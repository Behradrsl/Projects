"""Acceptance checks for scoring, controlled iteration, and exported evidence."""

import contextlib
import csv
import dataclasses
import io
import json
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from engine import (
    DEFAULT_PROMPT,
    Generation,
    RunSettings,
    best_model,
    export_csv,
    export_json,
    rows_for_run,
    run_loop,
    score_validation,
)
from validator import Diagnostic, ValidationResult

MODEL = "package Demo { part controller; }"
DESCRIPTION = "  A controller monitors a pump.\nKeep this original text unchanged.  "


def checked(
    parse="valid",
    semantic="valid",
    diagnostics=(),
    warnings=(),
    missing=(),
    names=None,
):
    return ValidationResult(
        parse_state=parse,
        semantic_state=semantic,
        diagnostics=tuple(diagnostics),
        warnings=tuple(warnings),
        missing_names=tuple(missing),
        name_score=names,
    )


class FixtureGenerator:
    def __init__(self, outputs, api_key=""):
        self.outputs = list(outputs)
        self.calls = []
        self.api_key = api_key

    def generate(self, description, system_prompt, previous_code=None, feedback=None):
        self.calls.append(
            {
                "description": description,
                "system_prompt": system_prompt,
                "previous_code": previous_code,
                "feedback": feedback,
            }
        )
        output = self.outputs[len(self.calls) - 1]
        if isinstance(output, Exception):
            raise output
        return output if isinstance(output, Generation) else Generation(output)


class FixtureValidator:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []
        self.closed = False

    def validate(self, code, expected_names=()):
        self.calls.append((code, tuple(expected_names)))
        return self.results[len(self.calls) - 1]

    def close(self):
        self.closed = True


def experiment(results, *, outputs=None, **settings):
    generator = FixtureGenerator(outputs or [MODEL] * len(results))
    validator = FixtureValidator(results)
    config = RunSettings(DESCRIPTION, iterations=len(results), **settings)
    result = run_loop(config, generator, validator)
    return result, generator, validator


class ScoreAcceptanceTests(unittest.TestCase):
    def test_t01_syntax_failure_forces_zero_without_inventing_semantics(self):
        scores = score_validation(checked("invalid", "unavailable"), False)
        self.assertEqual(scores, (0, None, None, 0, False))

    def test_t02_semantic_errors_fail_acceptance(self):
        scores = score_validation(checked(semantic="invalid"), False)
        self.assertEqual(scores, (100, 0, None, 40, False))

    def test_t03_exact_published_weights_with_expected_names(self):
        validation = checked(missing=("pump",), names=50)
        scores = score_validation(validation, True)
        self.assertEqual(scores, (100, 100, 50, 82.5, False))
        scores = score_validation(checked(names=100), True)
        self.assertEqual(scores, (100, 100, 100, 100, True))

    def test_no_name_list_is_na_and_uses_the_two_check_formula(self):
        self.assertEqual(score_validation(checked(), False), (100, 100, None, 100, True))

    def test_t04_missing_validator_or_analyzer_has_no_composite(self):
        self.assertEqual(
            score_validation(checked("unavailable", "unavailable"), False),
            (None, None, None, None, False),
        )
        self.assertEqual(
            score_validation(checked(semantic="unavailable"), False),
            (100, None, None, None, False),
        )

    def test_semantics_must_be_exactly_valid_for_acceptance(self):
        unchecked = SimpleNamespace(
            parse_state="valid",
            semantic_state="not_checked",
            diagnostics=(),
            warnings=(),
            missing_names=(),
            name_score=None,
        )
        try:
            scores = score_validation(unchecked, False)
        except ValueError:
            return
        self.assertFalse(scores[-1])
        self.assertIsNone(scores[3])


class LoopAcceptanceTests(unittest.TestCase):
    def test_t01_feedback_contains_real_parser_diagnostic_and_previous_code(self):
        diagnostic = Diagnostic("syntax", "error", "Expected closing brace", 1, 20)
        result, generator, validator = experiment(
            [checked("invalid", "unavailable", (diagnostic,)), checked()],
            outputs=["package Broken {", MODEL],
        )
        self.assertEqual(len(result.iterations), 2)
        self.assertEqual(result.iterations[0].automated_score, 0)
        self.assertEqual(generator.calls[1]["previous_code"], "package Broken {")
        self.assertIn("Expected closing brace", json.dumps(generator.calls[1]["feedback"]))
        for call in generator.calls:
            self.assertEqual(call["description"], DESCRIPTION)
            self.assertEqual(call["system_prompt"], DEFAULT_PROMPT)
        self.assertEqual(validator.calls[1][0], MODEL)

    def test_t02_semantic_diagnostics_and_warnings_are_recorded_separately(self):
        diagnostic = Diagnostic("semantic", "error", "Unresolved type Motor", 2, 5)
        warning = Diagnostic("semantic", "warning", "Unused private member")
        result, _, _ = experiment(
            [checked(semantic="invalid", diagnostics=(diagnostic,), warnings=(warning,))]
        )
        record = result.iterations[0]
        self.assertFalse(record.passed)
        self.assertEqual(record.semantic_score, 0)
        row = rows_for_run(result)[0]
        self.assertEqual(row["semantic_error_count"], 1)
        self.assertEqual(row["semantic_warning_count"], 1)
        self.assertEqual(row["error_count"], 1)
        self.assertEqual(row["warning_count"], 1)

    def test_t03_missing_names_enter_next_iteration_feedback(self):
        result, generator, _ = experiment(
            [checked(missing=("pump",), names=50), checked(names=100)],
            expected_names=("controller", "pump"),
        )
        self.assertEqual(result.iterations[0].automated_score, 82.5)
        self.assertFalse(result.iterations[0].passed)
        self.assertIn("pump", json.dumps(generator.calls[1]["feedback"]))
        self.assertEqual(result.best.loop, 2)

    def test_t04_unavailable_check_stops_instead_of_retrying_or_passing(self):
        for validation in (
            checked("unavailable", "unavailable"),
            checked(semantic="unavailable"),
        ):
            with self.subTest(validation=validation):
                result, generator, _ = experiment([validation, checked()])
                self.assertEqual(result.status, "validator_unavailable")
                self.assertEqual(len(generator.calls), 1)
                self.assertEqual(len(result.iterations), 1)
                self.assertIsNone(result.iterations[0].automated_score)
                self.assertFalse(result.iterations[0].passed)
                self.assertIsNone(result.best)
                self.assertIsNone(best_model(result))

    def test_t05_early_stop_defaults_off_and_can_stop_on_first_pass(self):
        result, generator, _ = experiment([checked()] * 4)
        self.assertEqual(len(generator.calls), 4)
        self.assertEqual(result.pass_rate, 100)
        self.assertEqual(len(result.iterations), 4)
        result, generator, _ = experiment([checked()] * 4, early_stop=True)
        self.assertEqual(len(generator.calls), 1)
        self.assertEqual(len(result.iterations), 1)
        self.assertTrue(result.best.passed)

    def test_t06_regression_preserves_previous_best_passing_version(self):
        result, _, _ = experiment(
            [checked(), checked("invalid", "unavailable"), checked(semantic="invalid")],
            outputs=[
                MODEL,
                "package Broken {",
                "package Later { part unresolved : X; }",
            ],
        )
        self.assertEqual(result.best.loop, 1)
        self.assertEqual(best_model(result), MODEL)
        self.assertAlmostEqual(result.pass_rate, 100 / 3)
        self.assertEqual(result.iterations[1].delta, -100)
        self.assertEqual(result.iterations[2].delta, 40)

    def test_best_nonpassing_score_and_earliest_tie_are_deterministic(self):
        result, _, _ = experiment(
            [
                checked("invalid", "unavailable"),
                checked(semantic="invalid"),
                checked(semantic="invalid"),
            ],
            outputs=["bad", "package Second {}", "package Third {}"],
        )
        self.assertEqual(result.best.loop, 2)
        self.assertEqual(best_model(result), "package Second {}")
        result, _, _ = experiment([checked("invalid", "unavailable")] * 2)
        self.assertEqual(result.best.loop, 1)

    def test_unknown_usage_is_never_coerced_to_zero_or_partial_total(self):
        result, _, _ = experiment(
            [checked()] * 3,
            outputs=[
                Generation(MODEL, 10, 5),
                Generation(MODEL, None, 7),
                Generation(MODEL, 1, 1),
            ],
        )
        first, second, third = result.iterations
        self.assertEqual(first.total_tokens, 15)
        self.assertEqual(first.cumulative_tokens, 15)
        self.assertIsNone(second.total_tokens)
        self.assertIsNone(second.cumulative_tokens)
        self.assertEqual(third.total_tokens, 2)
        self.assertIsNone(third.cumulative_tokens)
        self.assertIsNone(result.cumulative_tokens)

    def test_zero_provider_tokens_are_known_counts(self):
        result, _, _ = experiment([checked()], outputs=[Generation(MODEL, 0, 0)])
        self.assertEqual(result.iterations[0].total_tokens, 0)
        self.assertEqual(result.cumulative_tokens, 0)

    def test_provider_warning_does_not_become_a_semantic_error(self):
        result, _, _ = experiment(
            [checked()], outputs=[Generation(MODEL, warnings=("Truncation warning",))]
        )
        self.assertTrue(result.iterations[0].passed)
        self.assertEqual(result.iterations[0].automated_score, 100)
        row = rows_for_run(result)[0]
        self.assertEqual(row["warning_count"], 1)
        self.assertEqual(row["semantic_warning_count"], 0)
        self.assertEqual(row["semantic_error_count"], 0)

    def test_progress_callbacks_receive_frozen_records_in_order(self):
        seen = []
        validator = FixtureValidator([checked()] * 2)
        result = run_loop(
            RunSettings(DESCRIPTION, iterations=2),
            FixtureGenerator([MODEL] * 2),
            validator,
            on_iteration=seen.append,
        )
        self.assertEqual([record.loop for record in seen], [1, 2])
        self.assertEqual(tuple(seen), result.iterations)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            seen[0].code = "changed"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.settings.description = "changed"
        self.assertFalse(validator.closed)

    def test_generated_code_fence_is_removed_before_validation_and_export(self):
        result, _, validator = experiment([checked()], outputs=[f"```sysml\n{MODEL}\n```"])
        self.assertEqual(validator.calls[0][0], MODEL)
        self.assertEqual(best_model(result), MODEL)

    def test_bad_generation_outputs_stop_safely_before_validation(self):
        for output in ("", "   ", "x" * 60_001, RuntimeError("unsafe-provider-body")):
            with self.subTest(output_type=type(output).__name__):
                result, generator, validator = experiment([checked()], outputs=[output])
                self.assertEqual(result.status, "generation_failed")
                self.assertEqual(len(result.iterations), 0)
                self.assertEqual(len(generator.calls), 1)
                self.assertEqual(validator.calls, [])
                self.assertNotIn("unsafe-provider-body", result.reason)

    def test_generation_failure_after_a_pass_retains_the_previous_evidence(self):
        result, _, validator = experiment(
            [checked()] * 2,
            outputs=[Generation(MODEL, 10, 5), RuntimeError("Unsafe provider detail")],
        )
        self.assertEqual(result.status, "generation_failed")
        self.assertEqual(len(result.iterations), 1)
        self.assertEqual(len(validator.calls), 1)
        self.assertEqual(result.best.loop, 1)
        self.assertEqual(best_model(result), MODEL)
        self.assertIsNone(result.cumulative_tokens)  # The failed request did not report usage.
        self.assertEqual(result.iterations[0].cumulative_tokens, 15)
        self.assertNotIn("Unsafe provider detail", export_json(result))

    def test_validator_failure_becomes_unavailable_with_safe_diagnostic(self):
        validator = FixtureValidator([checked()])
        with patch.object(validator, "validate", side_effect=RuntimeError("Unsafe validator path")):
            result = run_loop(
                RunSettings(DESCRIPTION, iterations=2),
                FixtureGenerator([MODEL] * 2),
                validator,
            )
        self.assertEqual(result.status, "validator_unavailable")
        self.assertEqual(len(result.iterations), 1)
        self.assertIsNone(result.iterations[0].automated_score)
        self.assertFalse(result.iterations[0].passed)
        self.assertNotIn("Unsafe validator path", export_json(result))

    def test_engine_owned_validator_closes_even_when_generation_fails(self):
        validator = FixtureValidator([checked()])
        with patch("engine.SysMLValidator", return_value=validator):
            result = run_loop(
                RunSettings(DESCRIPTION, iterations=1),
                FixtureGenerator([RuntimeError("Generation failure")]),
            )
        self.assertEqual(result.status, "generation_failed")
        self.assertTrue(validator.closed)


class InputAcceptanceTests(unittest.TestCase):
    def test_t07_description_bounds_and_iteration_count(self):
        for description in ("", " \n\t ", "x" * 20_001):
            with (
                self.subTest(description_length=len(description)),
                self.assertRaises(ValueError),
            ):
                RunSettings(description)
        for iterations in (0, 9, -1, True, 1.5):
            with self.subTest(iterations=iterations), self.assertRaises(ValueError):
                RunSettings(DESCRIPTION, iterations=iterations)
        self.assertEqual(RunSettings("x").description, "x")
        self.assertEqual(len(RunSettings("x" * 20_000).description), 20_000)
        self.assertEqual(RunSettings(DESCRIPTION, iterations=8).iterations, 8)

    def test_t07_expected_name_limits_duplicates_and_invalid_terms(self):
        cases = (
            ("motor", "MOTOR"),
            tuple(f"part{i}" for i in range(31)),
            ("x" * 81,),
            ("",),
            ("   ",),
        )
        for names in cases:
            with self.subTest(names=names), self.assertRaises(ValueError):
                RunSettings(DESCRIPTION, expected_names=names)
        valid = tuple(f"part{i}" for i in range(30))
        self.assertEqual(len(RunSettings(DESCRIPTION, expected_names=valid).expected_names), 30)

    def test_t07_prompt_and_provider_url_bounds(self):
        with self.assertRaises(ValueError):
            RunSettings(DESCRIPTION, system_prompt="x" * 8_001)
        self.assertEqual(
            len(RunSettings(DESCRIPTION, system_prompt="x" * 8_000).system_prompt),
            8_000,
        )
        for base_url in (
            "file:///tmp/provider",
            "https://user:secret@example.com/v1",
            "https://example.com/v1?api_key=secret",
            "https://example.com/v1#secret",
        ):
            with self.subTest(base_url=base_url), self.assertRaises(ValueError):
                RunSettings(DESCRIPTION, base_url=base_url)


class ReportingAcceptanceTests(unittest.TestCase):
    def test_no_completed_iterations_have_no_cumulative_pass_rate(self):
        result, _, _ = experiment([checked()], outputs=[RuntimeError("Provider unavailable")])
        self.assertEqual(result.iterations, ())
        self.assertIsNone(result.pass_rate)
        self.assertIsNone(json.loads(export_json(result))["cumulative_check_pass_rate"])

    def test_unchecked_semantic_counts_are_unknown_across_measurement_exports(self):
        for validation in (
            checked("invalid", "unavailable"),
            checked("unavailable", "unavailable"),
            checked(
                semantic="unavailable",
                diagnostics=(Diagnostic("semantic", "error", "Analyzer unavailable"),),
            ),
        ):
            with self.subTest(validation=validation):
                result, _, _ = experiment([validation])
                row = rows_for_run(result)[0]
                exported_row = json.loads(export_json(result))["measurements"][0]
                csv_row = list(csv.DictReader(io.StringIO(export_csv(result))))[0]
                for field in ("semantic_error_count", "semantic_warning_count"):
                    self.assertIsNone(row[field])
                    self.assertIsNone(exported_row[field])
                    self.assertEqual(csv_row[field], "")

    def test_t08_one_measurement_source_feeds_csv_json_and_best_download(self):
        result, _, _ = experiment(
            [checked(semantic="invalid"), checked(), checked()],
            outputs=[
                Generation("package First {}", 10, 3),
                Generation(MODEL, 12, 5),
                Generation("package Tie {}", 11, 4),
            ],
        )
        rows = rows_for_run(result)
        exported = json.loads(export_json(result))
        self.assertEqual(exported["measurements"], rows)
        csv_rows = list(csv.DictReader(io.StringIO(export_csv(result))))
        self.assertEqual(len(csv_rows), len(rows))
        for original, csv_row, candidate in zip(
            rows, csv_rows, exported["iterations"], strict=True
        ):
            for key, value in original.items():
                self.assertIn(key, csv_row)
                if value is None:
                    self.assertEqual(csv_row[key], "")
                elif isinstance(value, bool):
                    self.assertEqual(csv_row[key].casefold(), str(value).casefold())
                elif isinstance(value, (float, int)):
                    self.assertAlmostEqual(float(csv_row[key]), value)
                else:
                    self.assertEqual(csv_row[key], str(value))
            self.assertEqual(candidate["code"], result.iterations[original["loop"] - 1].code)
        self.assertEqual(len(exported["iterations"]), 3)
        self.assertEqual(best_model(result), result.iterations[result.best.loop - 1].code)
        self.assertEqual(result.best.loop, 2)

    def test_t08_unknown_values_stay_null_in_json_and_empty_in_csv(self):
        result, _, _ = experiment([checked(semantic="unavailable")])
        row = json.loads(export_json(result))["measurements"][0]
        self.assertIsNone(row["automated_score"])
        self.assertIsNone(row["semantic_score"])
        self.assertIsNone(row["input_tokens"])
        csv_row = list(csv.DictReader(io.StringIO(export_csv(result))))[0]
        self.assertEqual(csv_row["automated_score"], "")
        self.assertEqual(csv_row["semantic_score"], "")
        self.assertEqual(csv_row["input_tokens"], "")

    def test_t10_keys_echoed_into_model_are_rejected_without_records(self):
        secret = "sk-test-only-secret-do-not-export-123456"
        generator = FixtureGenerator([f"{MODEL}\n// {secret}"], api_key=secret)
        validator = FixtureValidator([checked()])
        result = run_loop(RunSettings(DESCRIPTION, iterations=1), generator, validator)
        self.assertEqual(result.status, "generation_failed")
        self.assertEqual(validator.calls, [])
        self.assertEqual(result.iterations, ())
        for artifact in (export_json(result), export_csv(result), result.reason):
            self.assertNotIn(secret, artifact)

    def test_t10_secrets_are_absent_from_metadata_diagnostics_and_logs(self):
        secret = "sk-test-only-credential-123456789"
        generator = FixtureGenerator([MODEL], api_key=secret)
        diagnostic = Diagnostic("semantic", "warning", f"Provider echoed {secret}")
        validator = FixtureValidator([checked(warnings=(diagnostic,))])
        settings = RunSettings(
            f"A controller. Internal key: {secret}",
            system_prompt=f"Generate a model. Private credential {secret}",
            iterations=1,
        )
        captured = io.StringIO()
        log_handler = logging.StreamHandler(captured)
        logging.getLogger().addHandler(log_handler)
        try:
            with (
                contextlib.redirect_stdout(captured),
                contextlib.redirect_stderr(captured),
            ):
                result = run_loop(settings, generator, validator)
        finally:
            logging.getLogger().removeHandler(log_handler)
        for artifact in (
            export_json(result),
            export_csv(result),
            best_model(result),
            repr(result),
            captured.getvalue(),
        ):
            self.assertNotIn(secret, artifact)
        self.assertEqual(generator.calls[0]["description"], settings.description)


if __name__ == "__main__":
    unittest.main()
