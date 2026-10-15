"""Regression evidence for language scope, seven loops and independent review."""

import csv
import dataclasses
import io
import json
import unittest
from unittest.mock import patch

from engine import (
    DEFAULT_PROMPT,
    Generation,
    GenerationError,
    RunSettings,
    compact_feedback,
    export_csv,
    export_json,
    rows_for_run,
    run_loop,
)
from review import criteria_rows, review_measurements, save_reviews
from validator import Diagnostic, ValidationResult

MODEL = "package Demo { part def System; part system : System; }"


class Generator:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        return output if isinstance(output, Generation) else Generation(output, 10, 5)


class Validator:
    def __init__(self, state=None):
        self.state = state or ValidationResult("valid", "valid")

    def validate(self, *args):
        return self.state


def temporary_failure():
    return GenerationError(
        "Provider sent no completion choices.",
        code="missing_choices",
        retryable=True,
        input_tokens=2,
        output_tokens=1,
    )


class GenerationRecoveryTests(unittest.TestCase):
    @patch("engine.time.sleep")
    def test_seven_loops_recover_at_fifth_without_resetting_context(self, sleep):
        generator = Generator([MODEL] * 4 + [temporary_failure()] + [MODEL] * 3)
        result = run_loop(RunSettings("Original description", iterations=7), generator, Validator())
        self.assertEqual([r.loop for r in result.iterations], list(range(1, 8)))
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.processed_loops, 7)
        self.assertEqual(len(result.attempts), 8)
        self.assertEqual(generator.calls[4], generator.calls[5])
        self.assertTrue(all(c["description"] == "Original description" for c in generator.calls))
        self.assertEqual(result.cumulative_tokens, 108)
        sleep.assert_called_once_with(1)

    @patch("engine.time.sleep")
    def test_two_failures_leave_a_gap_and_still_attempt_loop_seven(self, _):
        generator = Generator(
            [MODEL] * 4 + [temporary_failure(), temporary_failure()] + [MODEL] * 2
        )
        result = run_loop(RunSettings("A system", iterations=7), generator, Validator())
        self.assertEqual(result.status, "completed_with_failures")
        self.assertEqual(result.failed_loops, (5,))
        self.assertEqual([r.loop for r in result.iterations], [1, 2, 3, 4, 6, 7])
        rows = rows_for_run(result)
        self.assertEqual([r["loop"] for r in rows], list(range(1, 8)))
        for field in ("syntax_score", "semantic_score", "automated_score", "passed"):
            self.assertIsNone(rows[4][field])
        self.assertEqual(rows[4]["generation_state"], "failed")
        self.assertEqual(rows[4]["generation_attempts"], 2)
        self.assertEqual(result.best.loop, 1)
        self.assertEqual(result.pass_rate, 100)  # denominator is the six checked versions
        payload = json.loads(export_json(result))
        self.assertEqual(payload["measurements"], rows)
        self.assertEqual(payload["failed_generation_loops"], [5])
        self.assertEqual(len(payload["attempts"]), 8)
        csv_rows = list(csv.DictReader(io.StringIO(export_csv(result))))
        self.assertEqual(len(csv_rows), 7)
        self.assertEqual(csv_rows[4]["automated_score"], "")
        self.assertEqual(float(csv_rows[-1]["cumulative_tokens"]), result.cumulative_tokens)

    @patch("engine.time.sleep")
    def test_all_failed_slots_export_without_fabricated_models_or_scores(self, _):
        result = run_loop(
            RunSettings("A system", iterations=7),
            Generator([temporary_failure() for _ in range(14)]),
            Validator(),
        )
        self.assertEqual(result.processed_loops, 7)
        self.assertEqual(len(result.iterations), 0)
        self.assertEqual(len(result.attempts), 14)
        self.assertIsNone(result.best)
        self.assertIsNone(result.pass_rate)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(export_csv(result))))), 7)
        self.assertTrue(all(row["automated_score"] is None for row in rows_for_run(result)))

    def test_authentication_stops_without_seven_identical_failed_requests(self):
        generator = Generator([GenerationError("Authentication failed.", code="authentication")])
        result = run_loop(RunSettings("A system", iterations=7), generator, Validator())
        self.assertEqual(result.status, "generation_failed")
        self.assertEqual(len(generator.calls), 1)
        self.assertEqual(result.settings.iterations, 7)
        self.assertEqual(result.processed_loops, 1)

    def test_failed_output_budget_usage_is_retained(self):
        failure = GenerationError(
            "Increase output budget.",
            code="output_budget",
            input_tokens=20,
            output_tokens=8192,
            reasoning_tokens=8192,
        )
        result = run_loop(RunSettings("A system", iterations=7), Generator([failure]), Validator())
        self.assertEqual(result.cumulative_tokens, 8212)
        self.assertEqual(result.attempts[0].reasoning_tokens, 8192)
        self.assertEqual(result.status, "generation_failed")

    def test_candidate_specific_unsupported_checks_do_not_shorten_the_run(self):
        unsupported = ValidationResult(
            "valid",
            "unavailable",
            diagnostics=(
                Diagnostic("semantic", "error", "Analyzer cannot resolve this construct"),
            ),
            unavailable_scope="candidate",
        )
        generator = Generator([MODEL] * 7)
        result = run_loop(RunSettings("A system", iterations=7), generator, Validator(unsupported))
        self.assertEqual(len(result.iterations), 7)
        self.assertTrue(all(r.automated_score is None and not r.passed for r in result.iterations))
        self.assertIn("tool_limitation", generator.calls[1]["feedback"])

    def test_global_validator_unavailability_still_stops(self):
        unavailable = ValidationResult("unavailable", "unavailable", unavailable_scope="validator")
        result = run_loop(
            RunSettings("A system", iterations=7), Generator([MODEL] * 7), Validator(unavailable)
        )
        self.assertEqual(result.status, "validator_unavailable")
        self.assertEqual(len(result.iterations), 1)

    def test_invalid_models_continue_when_early_stop_is_off(self):
        invalid = ValidationResult(
            "invalid", "unavailable", diagnostics=(Diagnostic("parser", "error", "Expected brace"),)
        )
        result = run_loop(
            RunSettings("A system", iterations=7), Generator([MODEL] * 7), Validator(invalid)
        )
        self.assertEqual(len(result.iterations), 7)
        self.assertTrue(all(r.automated_score == 0 for r in result.iterations))


class FeedbackAndComparisonTests(unittest.TestCase):
    def test_syntax_repair_receives_location_source_and_complete_previous_model(self):
        broken = "package Demo {\npart def System\n}"
        validation = ValidationResult(
            "invalid",
            "unavailable",
            (Diagnostic("parser", "error", "Expected semicolon", 2, 15),),
        )
        generator = Generator([broken, MODEL])

        class RepairValidator:
            def validate(self, code, names):
                return validation if code == broken else ValidationResult("valid", "valid")

        result = run_loop(RunSettings("A system", iterations=2), generator, RepairValidator())
        feedback = generator.calls[1]["feedback"]
        self.assertEqual(generator.calls[1]["previous_code"], broken)
        self.assertEqual(feedback["diagnostics"][0]["source_line"], "part def System")
        self.assertEqual(feedback["diagnostics"][0]["column"], 15)
        self.assertIn("earliest syntax error", feedback["revision_goal"])
        self.assertFalse(result.iterations[0].passed)
        self.assertTrue(result.iterations[1].passed)

    def test_prompt_is_short_and_does_not_teach_binding_as_communication(self):
        self.assertLess(len(DEFAULT_PROMPT), 1000)
        self.assertIn("OMG SysML v2", DEFAULT_PROMPT)
        self.assertIn(":>", DEFAULT_PROMPT)
        self.assertIn("not data transfer", DEFAULT_PROMPT)

    def test_feedback_deduplicates_and_bounds_without_discarding_evidence(self):
        diagnostics = tuple(
            Diagnostic("semantic", "error", "Error " + str(i) + ":" + "x" * 800) for i in range(30)
        )
        validation = ValidationResult(
            "valid",
            "invalid",
            diagnostics * 2,
            (Diagnostic("semantic", "warning", "NAMING_CONVENTION: lower case"),),
        )
        feedback = compact_feedback(validation)
        self.assertEqual(len(feedback["diagnostics"]), 12)
        self.assertNotIn("scores", feedback)
        self.assertNotIn("warnings", feedback)
        self.assertEqual(len(validation.diagnostics), 60)
        self.assertTrue(all(len(d["message"]) <= 240 for d in feedback["diagnostics"]))

    def test_expected_names_and_requirements_reach_first_request(self):
        generator = Generator([MODEL])
        settings = RunSettings(
            "Original description",
            iterations=1,
            expected_names=("System",),
            requirements=("The system reads temperature.",),
        )
        run_loop(settings, generator, Validator(ValidationResult("valid", "valid", name_score=100)))
        self.assertEqual(generator.calls[0]["feedback"]["expected_names"], ["System"])
        self.assertEqual(
            generator.calls[0]["feedback"]["review_requirements"], list(settings.requirements)
        )
        self.assertEqual(generator.calls[0]["description"], settings.description)

    def test_reference_only_observations_reach_revision_without_becoming_semantic_errors(self):
        observation = Diagnostic(
            "modeling", "warning", "REFERENCE_ONLY: Use `part name : Type;` for owned composition."
        )
        generator = Generator([MODEL, MODEL])
        result = run_loop(
            RunSettings("A system", iterations=2),
            generator,
            Validator(ValidationResult("valid", "valid", warnings=(observation,))),
        )
        self.assertTrue(all(r.passed for r in result.iterations))
        self.assertEqual(generator.calls[1]["feedback"]["warnings"][0]["stage"], "modeling")
        self.assertEqual(result.iterations[0].validation.warnings, (observation,))

    def test_renaming_alone_has_no_diagnostic_improvement(self):
        result = run_loop(
            RunSettings("A system", iterations=2),
            Generator([MODEL, MODEL.replace("system :", "assembly :")]),
            Validator(),
        )
        second = result.iterations[1]
        self.assertTrue(second.source_changed)
        self.assertEqual(second.resolved_diagnostics, 0)
        self.assertEqual(second.new_diagnostics, 0)
        self.assertEqual(second.delta, 0)


class HumanReviewTests(unittest.TestCase):
    def result(self):
        return run_loop(
            RunSettings(
                "A system",
                iterations=1,
                requirements=("The sensor sends temperature.", "The controller reads temperature."),
            ),
            Generator([MODEL]),
            Validator(),
        )

    def test_unreviewed_quality_and_coverage_remain_unknown_even_when_valid(self):
        result = self.result()
        self.assertTrue(result.best.passed)
        self.assertIsNone(review_measurements(result, 1)["manual_requirement_pass_percent"])
        self.assertIsNone(review_measurements(result, 1)["manual_structural_pass_percent"])

    def test_evidence_required_and_criteria_cannot_be_replaced(self):
        result = self.result()
        rows = criteria_rows(result)
        rows[0]["Assessment"] = "Pass"
        with self.assertRaises(ValueError):
            save_reviews(result, rows)
        rows[0]["Evidence"] = "Line 1"
        rows[0]["Criterion"] = "Invented easier criterion"
        with self.assertRaises(ValueError):
            save_reviews(result, rows)

    def test_partial_review_never_becomes_a_complete_coverage_score(self):
        result = self.result()
        rows = criteria_rows(result)
        rows[-1].update(Assessment="Pass", Evidence="Controller action at line 20")
        amended = dataclasses.replace(result, reviews=save_reviews(result, rows))
        self.assertIsNone(review_measurements(amended, 1)["manual_requirement_pass_percent"])

    def test_manual_review_is_independent_consistent_and_redacts_credentials(self):
        result = self.result()
        rows = criteria_rows(result)
        for row in rows:
            row.update(
                Assessment="Pass", Evidence="Model evidence at line 5; credential sk-review-fixture"
            )
        rows[-1]["Assessment"] = "Partial"
        rows[0]["Assessment"] = "Not applicable"
        amended = dataclasses.replace(
            result, reviews=save_reviews(result, rows, ("sk-review-fixture",))
        )
        self.assertEqual(review_measurements(amended, 1)["manual_requirement_pass_percent"], 50)
        self.assertEqual(review_measurements(amended, 1)["manual_structural_pass_percent"], 100)
        self.assertEqual(result.best, amended.best)
        self.assertNotIn("sk-review-fixture", export_json(amended))
        json_row = json.loads(export_json(amended))["measurements"][0]
        csv_row = list(csv.DictReader(io.StringIO(export_csv(amended))))[0]
        self.assertEqual(
            json_row["manual_requirement_pass_percent"],
            float(csv_row["manual_requirement_pass_percent"]),
        )
        self.assertFalse(json.loads(export_json(amended))["engineering_review"]["assessed_by_llm"])


if __name__ == "__main__":
    unittest.main()
