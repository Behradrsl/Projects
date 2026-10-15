"""Exercise the full pipeline with real validation and optional live generation."""

import argparse
import json
from pathlib import Path

from config import load_connection
from engine import (
    DEMO_DESCRIPTION,
    DEMO_NAMES,
    DemoGenerator,
    OpenAIChatGenerator,
    RunSettings,
    best_model,
    export_csv,
    export_json,
    run_loop,
)

ROOT = Path(__file__).resolve().parent


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline", action="store_true", help="Fixed candidates, real validator")
    modes.add_argument("--live", action="store_true", help="Real API generation, real validator")
    parser.add_argument(
        "--loops",
        type=int,
        choices=range(1, 9),
        metavar="1-8",
        help="Live mode only: maximum iterations (default: 4; continue after a pass).",
    )
    parser.add_argument(
        "--early-stop",
        action="store_true",
        help="Live mode only: stop on the first accepted version (default: off).",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=8192,
        help="Completion budget per request, including provider reasoning (1024–32768).",
    )
    args = parser.parse_args(argv)
    if args.offline and (args.loops is not None or args.early_stop):
        parser.error(
            "--loops and --early-stop require --live; --offline replays exactly 3 examples."
        )
    if args.loops is None:
        args.loops = 4
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.live:
        connection = load_connection(ROOT)
        if not connection.api_key:
            print("T09 NOT VERIFIED: configure LLM_API_KEY in this project's .env first.")
            return 2
        try:
            settings = RunSettings(
                DEMO_DESCRIPTION,
                expected_names=DEMO_NAMES,
                iterations=args.loops,
                early_stop=args.early_stop,
                model=connection.model,
                base_url=connection.base_url,
                max_output_tokens=args.max_output_tokens,
            )
            with OpenAIChatGenerator(
                settings.model,
                connection.api_key,
                settings.base_url,
                max_output_tokens=settings.max_output_tokens,
            ) as generator:
                result = run_loop(settings, generator)
        except Exception:
            print("T09 NOT PASSED: could not start the provider connection. Check .env settings.")
            return 1
    else:
        settings = RunSettings(
            DEMO_DESCRIPTION,
            expected_names=DEMO_NAMES,
            iterations=3,
            model="Fixed demonstration examples",
        )
        result = run_loop(settings, DemoGenerator())

    output = args.output / f"{result.mode}-{result.run_id}"
    output.mkdir(parents=True, exist_ok=False)
    (output / "run_record.json").write_text(export_json(result), encoding="utf-8")
    (output / "loop_scores.csv").write_text(export_csv(result), encoding="utf-8", newline="")
    selected = best_model(result)
    if selected is not None:
        (output / "best.sysml").write_text(selected, encoding="utf-8")
    success = result.best is not None and result.best.passed
    complete = result.status in {"completed", "early_stopped"}
    gate_passed = success and complete and result.mode == "live"
    evidence = {
        "mode": result.mode,
        "run_id": result.run_id,
        "pipeline_passed": success and complete,
        "status": result.status,
        "requested_loops": result.settings.iterations,
        "processed_loops": result.processed_loops,
        "generated_versions": len(result.iterations),
        "failed_generation_loops": list(result.failed_loops),
        "T09_real_llm_and_validator": "passed" if gate_passed else "not verified",
        "boundary": "Offline replay does not verify live LLM generation.",
    }
    (output / "integration_evidence.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    for record in result.iterations:
        print(
            f"Loop {record.loop}: parser={record.validation.parse_state}, "
            f"semantics={record.validation.semantic_state}, "
            f"Q={record.automated_score}, pass={record.passed}"
        )
    for attempt in result.attempts:
        if attempt.state == "failed":
            print(
                f"Loop {attempt.loop}, attempt {attempt.attempt}: "
                f"{attempt.error_code}: {attempt.message}"
            )
    print("Status:", result.status)
    print("Artifacts:", output)
    if result.reason:
        print(result.reason)
    if not args.live:
        if success:
            print("Offline replay verified. T09 still requires a live LLM run.")
        else:
            print("Offline replay failed. Inspect diagnostics; T09 remains unverified.")
    elif gate_passed:
        print("T09 PASSED: real API generation and installed parser/analyzer.")
    else:
        print("T09 NOT PASSED: inspect diagnostics in the exported record.")
    return 0 if success and complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
