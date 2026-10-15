"""Strict SysML parsing and semantic checks in a bounded, isolated worker."""

from __future__ import annotations

import contextlib
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MAX_CODE_CHARS = 60_000
MAX_DIAGNOSTICS = 200
MAX_MESSAGE_CHARS = 1_000
_STATES = {"valid", "invalid", "unavailable"}
_TOKENS = re.compile(
    r"//[^\r\n]*|/\*[\s\S]*?(?:\*/|\Z)|'(?:\\.|[^'\\])*'|"
    r'"(?:\\.|[^"\\])*"|[^\W\d]\w*',
    re.UNICODE,
)


@dataclass(frozen=True)
class Diagnostic:
    stage: str
    severity: str
    message: str
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True)
class ValidationResult:
    parse_state: str
    semantic_state: str
    diagnostics: tuple[Diagnostic, ...] = ()
    warnings: tuple[Diagnostic, ...] = ()
    missing_names: tuple[str, ...] = ()
    name_score: float | None = None
    unavailable_scope: str | None = None


def lexical_names(code: str) -> frozenset[str]:
    """Find whole lexical identifiers, excluding comments and string values.

    Single quotes delimit SysML unrestricted identifiers. Double quotes delimit
    string values, which cannot satisfy an expected identifier. This is a name
    presence measurement, independent of grammar and semantic validation.
    """
    names = set()
    for match in _TOKENS.finditer(code):
        token = match.group()
        if token.startswith(("//", "/*", '"')):
            continue
        if token.startswith("'"):
            token = re.sub(r"\\(.)", r"\1", token[1:-1])
        names.add(token.casefold())
    return frozenset(names)


def expected_name_presence(
    code: str, expected_names: tuple[str, ...]
) -> tuple[tuple[str, ...], float | None]:
    """Return missing names and exact lexical presence percentage."""
    if not expected_names:
        return (), None
    found = lexical_names(code)
    missing = tuple(name for name in expected_names if name.casefold() not in found)
    return missing, 100.0 * (len(expected_names) - len(missing)) / len(expected_names)


def _unavailable(message: str, parse_state: str = "unavailable") -> ValidationResult:
    return ValidationResult(
        parse_state,
        "unavailable",
        (Diagnostic("validator", "error", message),),
        unavailable_scope="validator",
    )


def _syntax_diagnostic(message: str) -> Diagnostic:
    location = re.search(r"Syntax error at (\d+):(\d+):", message)
    return Diagnostic(
        "parser",
        "error",
        message[:MAX_MESSAGE_CHARS],
        int(location[1]) if location else None,
        int(location[2]) if location else None,
    )


def _named_nodes(node, kind):
    if isinstance(node, dict):
        if node.get("name") == kind:
            yield node
        for value in node.values():
            yield from _named_nodes(value, kind)
    elif isinstance(node, list):
        for value in node:
            yield from _named_nodes(value, kind)


def _declarations(grammar):
    """Collect scoped declarations from the parsed tree, excluding comments."""
    definitions, usages = {}, []

    def walk(node, scope=(), performed=False):
        if isinstance(node, dict):
            kind = node.get("name", "")
            performed = performed or kind == "PerformActionUsage"
            header = node.get("definition", node).get("declaration", {})
            if kind == "Package":
                header = node.get("declaration", {})
            if kind.endswith("Usage"):
                header = node.get("usage", node).get("declaration", {})
            identification = next(_named_nodes(header, "Identification"), {})
            name = identification.get("declaredName")
            if kind in {
                "PortUsage",
                "DefaultReferenceUsage",
                "ReferenceUsage",
                "PartUsage",
                "ActionUsage",
                "FlowConnectionUsage",
                "InterfaceUsage",
                "ConnectionUsage",
            } and not (kind == "ActionUsage" and performed):
                usages.append((scope, name, kind, header))
            if name and (
                (kind.endswith("Definition") and kind != "Definition") or kind == "Package"
            ):
                definitions[(*scope, name)] = kind
                scope = (*scope, name)
            elif name and kind in {"PartUsage", "ActionUsage"}:
                scope = (*scope, name)
            for value in node.values():
                walk(value, scope, performed)
        elif isinstance(node, list):
            for value in node:
                walk(value, scope, performed)

    walk(grammar)
    return definitions, usages


def _resolve_definition(definitions, scope, names):
    return next(
        (
            definitions[(*scope[:depth], *names)]
            for depth in range(len(scope), -1, -1)
            if (*scope[:depth], *names) in definitions
        ),
        None,
    )


def _port_type_errors(grammar: dict) -> list[Diagnostic]:
    """Check explicit port typing, which sysmlpy's symbol checks alone miss.

    OMG SysML v2 section 7.12.2 restricts port usages to port definitions.
    Only reject resolved local non-port definitions and known scalar types;
    this does not claim to resolve every library, alias or inheritance form.
    """
    definitions, usages = _declarations(grammar)
    errors = []
    scalars = {"Real", "Integer", "Natural", "Rational", "Number", "String", "Boolean"}
    for scope, port_name, kind, header in usages:
        if kind != "PortUsage":
            continue
        for typing in _named_nodes(header, "OwnedFeatureTyping"):
            for qualified in _named_nodes(typing, "QualifiedName"):
                names = tuple(qualified.get("names", ()))
                if not names:
                    continue
                resolved = _resolve_definition(definitions, scope, names)
                scalar = names[0] == "ScalarValues" or (
                    len(names) == 1
                    and names[0] in scalars
                    and resolved is None
                    and not any(
                        key[-1] == names[0] and kind == "PortDefinition"
                        for key, kind in definitions.items()
                    )
                )
                if scalar or (resolved is not None and resolved != "PortDefinition"):
                    errors.append(
                        Diagnostic(
                            "semantic",
                            "error",
                            f"PORT_TYPE_KIND: Port '{port_name}' is typed by {'::'.join(names)}, "
                            "which is not a port definition. Define a port def containing an "
                            "in/out attribute or item of the data type, then type the port usage "
                            "by that port definition and flow between its directed features.",
                        )
                    )
    return errors


def _reference_usage_warnings(grammar: dict) -> list[Diagnostic]:
    """Flag reference-only declarations for review, without rejecting legal v2.

    A bare typed reference can be intentional (OMG section 7.6.4). It does not
    establish the composition, port or performed behavior its type suggests.
    These observations guide revision and never change language scores.
    """
    definitions, usages = _declarations(grammar)
    hints = {
        "PartDefinition": "Use `part name : Type;` if owned composition is intended.",
        "PortDefinition": "Use `port name : Type;` if a component port is intended.",
        "ActionDefinition": "Use `perform action name : Type;` if performed behavior is intended.",
    }
    found = {kind: [] for kind in hints}
    for scope, name, kind, header in usages:
        if kind not in {"DefaultReferenceUsage", "ReferenceUsage"}:
            continue
        for typing in _named_nodes(header, "OwnedFeatureTyping"):
            for qualified in _named_nodes(typing, "QualifiedName"):
                resolved = _resolve_definition(definitions, scope, qualified.get("names", ()))
                if resolved in hints and name not in found[resolved]:
                    found[resolved].append(name)
    warnings = [
        Diagnostic(
            "modeling",
            "warning",
            f"REFERENCE_ONLY: {hints[kind]} Reference declarations: {', '.join(names[:8])}.",
        )
        for kind, names in found.items()
        if names
    ]
    part_scopes = {scope for scope, kind in definitions.items() if kind == "PartDefinition"}
    part_scopes.update((*scope, name) for scope, name, kind, _ in usages if kind == "PartUsage")
    actions = [
        name for scope, name, kind, _ in usages if kind == "ActionUsage" and scope in part_scopes
    ]
    if actions:
        warnings.append(
            Diagnostic(
                "modeling",
                "warning",
                "ACTION_PERFORMER: Owned actions do not explicitly identify their part as "
                "performer. If that behavior is requested, use `perform action name : Type;` and "
                f"connect its inputs. Actions: {', '.join(actions[:8])}.",
            )
        )
    for scope in sorted(part_scopes):
        kinds = [kind for owner, _, kind, _ in usages if owner == scope]
        if (
            kinds.count("PartUsage") >= 2
            and "FlowConnectionUsage" in kinds
            and not {"InterfaceUsage", "ConnectionUsage"}.intersection(kinds)
        ):
            warnings.append(
                Diagnostic(
                    "modeling",
                    "warning",
                    f"CONNECTION_REVIEW: {'::'.join(scope)} contains parts and directed flow but "
                    "no explicit interface/connection usage. If an architectural link is needed, "
                    "declare it between the component ports and retain the flow.",
                )
            )
    return warnings


def _validate_source(
    code: str, expected_names: tuple[str, ...], notify_parsed: Any = None
) -> ValidationResult:
    """Worker implementation. Missing or failed checks never become valid."""
    try:
        import sysmlpy
        from sysmlpy.antlr_parser import SysMLSyntaxError, parse
        from sysmlpy.dfa_cache import set_dfa_cache

        set_dfa_cache(enabled=False)
    except Exception:
        return _unavailable("SysML parser is unavailable. Install the pinned dependencies.")

    try:
        # Disable sysmlpy's default natural-language constraint-body rescue.
        # First check grammar separately from semantic model construction.
        parse(code, rescue_language=None)
    except SysMLSyntaxError as error:
        messages = str(error).splitlines() or ["SysML syntax validation failed."]
        return ValidationResult(
            "invalid",
            "unavailable",
            tuple(_syntax_diagnostic(item) for item in messages[:MAX_DIAGNOSTICS]),
        )
    except Exception:
        return _unavailable("SysML parser failed before completing the syntax check.")

    if notify_parsed is not None:
        notify_parsed()
    missing, name_score = expected_name_presence(code, expected_names)
    analyzer = getattr(sysmlpy, "analyze", None)
    if not callable(analyzer):
        return _unavailable("The semantic analyzer API is unavailable.", "valid")
    try:
        # Model construction uses the exact original code, without repairs.
        try:
            model = sysmlpy.loads(code, rescue_language=None)
        except Exception:
            return ValidationResult(
                "valid",
                "unavailable",
                (
                    Diagnostic(
                        "semantic",
                        "error",
                        "The v2 grammar accepted this model, but the installed analyzer could not "
                        "construct it. Semantic validity is unknown; inspect tool support.",
                    ),
                ),
                missing_names=missing,
                name_score=name_score,
                unavailable_scope="candidate",
            )
        issues = analyzer(model, strict=False, style_checks=True)
        # Explicitly require the analyzer's documented result, not truthiness.
        if not isinstance(issues, sysmlpy.AnalysisResult):
            raise RuntimeError("Analyzer returned an unsupported result")
        # Inspect the source parse, not a re-serialized Model: the installed
        # model layer can omit legal reference usages while constructing it.
        grammar = sysmlpy.load_grammar_antlr(code, rescue_language=None)
        errors: list[Diagnostic] = _port_type_errors(grammar)
        warnings: list[Diagnostic] = _reference_usage_warnings(grammar)
        unsupported = False
        for issue in issues:
            if issue.severity not in {"error", "warning"}:
                raise RuntimeError("Analyzer returned an unsupported severity")
            reference = getattr(issue, "reference", None)
            # sysmlpy 0.96.4 treats a conjugated port type as a literal name.
            # Never turn that known false positive into an invalid-language verdict.
            if (
                issue.code == "UNDEFINED_SYMBOL"
                and isinstance(reference, str)
                and reference.startswith("~")
                and any(
                    getattr(element, "name", None) == reference[1:]
                    and getattr(element, "is_definition", False)
                    for element in model.find_all(type="port")
                )
            ):
                unsupported = True
                errors.append(
                    Diagnostic(
                        "semantic",
                        "error",
                        "ANALYZER_LIMITATION: The installed analyzer cannot resolve this SysML v2 "
                        "conjugated port type. Semantic validity is unknown; "
                        "do not treat it as an undefined definition.",
                    )
                )
                continue
            diagnostic = Diagnostic(
                "semantic",
                issue.severity,
                f"{issue.code}: {issue.message}"[:MAX_MESSAGE_CHARS],
            )
            (errors if issue.severity == "error" else warnings).append(diagnostic)
        if len(errors) + len(warnings) > MAX_DIAGNOSTICS:
            # Complete counts cannot be reported faithfully after truncation.
            raise RuntimeError("Analyzer diagnostic limit exceeded")
    except Exception:
        return ValidationResult(
            "valid",
            "unavailable",
            (
                Diagnostic(
                    "semantic",
                    "error",
                    "Semantic analysis did not complete. The model may use an unsupported "
                    "construct; return a package-wrapped model and inspect the validator setup.",
                ),
            ),
            missing_names=missing,
            name_score=name_score,
            unavailable_scope="candidate",
        )
    return ValidationResult(
        "valid",
        "unavailable" if unsupported else "invalid" if errors else "valid",
        tuple(errors),
        tuple(warnings),
        missing,
        name_score,
        "candidate" if unsupported else None,
    )


def _read_worker(process: subprocess.Popen[str], output: queue.Queue[Any]) -> None:
    try:
        if process.stdout is None:
            return
        for _ in range(32):
            line = process.stdout.readline(1_000_001)
            if not line or len(line) > 1_000_000:
                break
            output.put(json.loads(line))
    except (OSError, ValueError):
        pass
    finally:
        output.put(None)


class SysMLValidator:
    """Reuse one worker's in-memory library index for up to eight candidates.

    The worker receives model text and expected names only. It has no API-key
    environment, cannot execute generated source, and is killed on timeout.
    First semantic analysis can take approximately 30 seconds while sysmlpy
    indexes its bundled standard library; subsequent checks reuse that index.
    """

    def __init__(self, timeout_seconds: float = 60.0):
        if not 0 < timeout_seconds <= 120:
            raise ValueError("Validator timeout must be between 0 and 120 seconds.")
        self.timeout_seconds = timeout_seconds
        self._process: subprocess.Popen[str] | None = None
        self._output: queue.Queue[Any] = queue.Queue()
        self._checks = 0
        self._lock = threading.Lock()

    def _start(self) -> None:
        self.close()
        self._output = queue.Queue()
        environment = {
            key: value
            for key, value in os.environ.items()
            if key in {"PATH", "SYSTEMROOT", "WINDIR", "TMPDIR", "TEMP", "TMP", "LANG"}
        }
        environment.update(
            SYSSMLPY_DFA_CACHE="off",
            OPENBLAS_NUM_THREADS="1",
            MKL_NUM_THREADS="1",
            OMP_NUM_THREADS="1",
        )
        self._process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-B",
                "-u",
                str(Path(__file__).resolve()),
                "--worker",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        self._checks = 0
        threading.Thread(
            target=_read_worker, args=(self._process, self._output), daemon=True
        ).start()

    def validate(self, code: str, expected_names: tuple[str, ...] = ()) -> ValidationResult:
        if not isinstance(code, str) or not 1 <= len(code) <= MAX_CODE_CHARS:
            return _unavailable("Candidate must contain between 1 and 60,000 characters.")
        if (
            not isinstance(expected_names, tuple)
            or len(expected_names) > 30
            or any(not isinstance(name, str) or not 1 <= len(name) <= 80 for name in expected_names)
            or len({name.casefold() for name in expected_names}) != len(expected_names)
        ):
            return _unavailable("Expected names must be at most 30 unique nonempty identifiers.")
        with self._lock:
            parse_state = "unavailable"
            try:
                if self._process is None or self._process.poll() is not None or self._checks >= 8:
                    self._start()
                assert self._process is not None and self._process.stdin is not None
                payload = json.dumps(
                    {"code": code, "expected_names": expected_names}, ensure_ascii=False
                )
                self._process.stdin.write(payload + "\n")
                self._process.stdin.flush()
                self._checks += 1
                deadline = time.monotonic() + self.timeout_seconds
                while True:
                    message = self._output.get(timeout=max(0, deadline - time.monotonic()))
                    if message is None:
                        raise OSError("Validator worker exited")
                    if message == {"event": "parsed"}:
                        parse_state = "valid"
                        continue
                    if not isinstance(message, dict):
                        raise ValueError("Unsupported validator response")
                    result = ValidationResult(
                        parse_state=message["parse_state"],
                        semantic_state=message["semantic_state"],
                        diagnostics=tuple(Diagnostic(**item) for item in message["diagnostics"]),
                        warnings=tuple(Diagnostic(**item) for item in message["warnings"]),
                        missing_names=tuple(message["missing_names"]),
                        name_score=message["name_score"],
                        unavailable_scope=message.get("unavailable_scope"),
                    )
                    if result.parse_state not in _STATES or result.semantic_state not in _STATES:
                        raise ValueError("Unsupported validator state")
                    return result
            except queue.Empty:
                self.close()
                return _unavailable("SysML validation exceeded its time limit.", parse_state)
            except (OSError, ValueError, KeyError, TypeError, AssertionError):
                self.close()
                return _unavailable("SysML validator did not complete successfully.", parse_state)

    def close(self) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        if process.poll() is None:
            process.kill()
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            process.wait(timeout=2)
        for stream in (process.stdin, process.stdout):
            if stream is not None:
                with contextlib.suppress(OSError):
                    stream.close()

    def __enter__(self) -> SysMLValidator:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def _worker_limits() -> None:
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU, (240, 241))
        # Linux enforces virtual-address limits reliably; macOS does not.
        if sys.platform.startswith("linux"):
            resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    except (ImportError, OSError, ValueError):
        # All platforms still enforce the parent process's wall-clock timeout.
        pass


def _worker_main() -> None:
    _worker_limits()
    reply = sys.stdout

    def parsed() -> None:
        reply.write('{"event":"parsed"}\n')
        reply.flush()

    # Never forward third-party stdout/stderr, tracebacks, or incidental logs.
    with open(os.devnull, "w", encoding="utf-8") as sink:
        for _ in range(8):
            line = sys.stdin.readline(512_001)
            if not line or len(line) > 512_000:
                break
            try:
                payload = json.loads(line)
                with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                    result = _validate_source(
                        payload["code"], tuple(payload["expected_names"]), parsed
                    )
                reply.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
                reply.flush()
            except Exception:
                reply.write(
                    json.dumps(asdict(_unavailable("SysML validator failed safely."))) + "\n"
                )
                reply.flush()


if __name__ == "__main__" and sys.argv[1:] == ["--worker"]:
    _worker_main()
