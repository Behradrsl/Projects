"""Dashboard behavior without remote requests or a slow parser startup."""

from __future__ import annotations

import dataclasses
import io
import os
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app import (
    expected_names_from_text,
    format_number,
    measurement_chart,
    plot_records,
    prompt_from_upload,
    table_rows,
    upgrade_session_result,
)
from engine import Generation, GenerationError, export_json
from validator import Diagnostic, ValidationResult

ROOT = Path(__file__).resolve().parents[1]


class FakeValidator:
    def validate(self, code, expected_names):
        return ValidationResult("valid", "valid", name_score=100.0 if expected_names else None)

    def close(self):
        pass


class UnavailableValidator(FakeValidator):
    def validate(self, code, expected_names):
        return ValidationResult(
            "valid",
            "unavailable",
            diagnostics=(Diagnostic("validator", "error", "Analyzer not installed."),),
        )


class FakeGenerator:
    mode = "live"

    def __init__(self, model, api_key, base_url=None, max_output_tokens=8192):
        self.secret_values = (api_key,)
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        return Generation(f"package Model{self.calls} {{ part def Sensor; }}", 20, 10)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def find(elements, label):
    return next(element for element in elements if element.label == label)


class DashboardTests(unittest.TestCase):
    def environment(self, validator=FakeValidator):
        stack = ExitStack()
        stack.enter_context(patch.dict(os.environ, {}, clear=True))
        stack.enter_context(patch("dotenv.load_dotenv", return_value=False))
        stack.enter_context(patch("engine.SysMLValidator", validator))
        stack.enter_context(patch("engine.OpenAIChatGenerator", FakeGenerator))
        self.addCleanup(stack.close)
        return stack

    def app(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
        self.assertFalse(at.exception)
        return at

    def complete_run(self, at, loops=2, early_stop=False):
        at.text_area(key="cps_description").set_value("A system has a Sensor.")
        at.text_area(key="expected_names").set_value("Sensor")
        find(at.text_input, "API key").set_value("test-secret-never-exported")
        find(at.number_input, "Number of loops").set_value(loops)
        find(at.checkbox, "Stop after first passing version").set_value(early_stop)
        find(at.button, "Run validation").click().run()
        self.assertFalse(at.exception)
        return at.session_state["completed_run"]

    def test_initial_controls_and_missing_key_are_actionable(self):
        self.environment()
        at = self.app()
        self.assertEqual(find(at.number_input, "Number of loops").value, 4)
        self.assertFalse(find(at.checkbox, "Stop after first passing version").value)
        self.assertEqual(len(at.sidebar.number_input), 0)
        self.assertEqual(find(at.text_input, "API key").value, "")
        at.text_area(key="cps_description").set_value("A system has a Sensor.")
        find(at.button, "Run validation").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Add an API key" in item.value for item in at.error))
        self.assertEqual(len(at.get("code")), 0)

    def test_empty_input_and_duplicate_names_rejected(self):
        self.environment()
        at = self.app()
        find(at.button, "Run validation").click().run()
        self.assertTrue(any("Enter a CPS description" in item.value for item in at.error))
        at.text_area(key="cps_description").set_value("A system has a Sensor.")
        at.text_area(key="expected_names").set_value("Sensor\nsensor")
        find(at.button, "Run validation").click().run()
        self.assertTrue(any("unique" in item.value for item in at.error))
        self.assertFalse(at.exception)

    def test_completed_run_is_frozen_and_does_not_contain_credentials(self):
        self.environment()
        at = self.app()
        result = self.complete_run(at)
        self.assertEqual(result.settings.description, "A system has a Sensor.")
        self.assertEqual(len(result.iterations), 2)
        self.assertEqual(result.best.loop, 1)
        self.assertEqual(result.cumulative_tokens, 60)
        self.assertNotIn("test-secret-never-exported", export_json(result))
        self.assertEqual(
            [panel.value for panel in at.get("code")], [r.code for r in result.iterations]
        )
        self.assertTrue(
            any("versions passed all configured checks" in item.value for item in at.success)
        )
        self.assertTrue(
            any(item.label == "Syntax passes" and item.value == "2/2" for item in at.metric)
        )
        at.text_area(key="cps_description").set_value("A different new system.")
        find(at.text_input, "Model ID").set_value("different-model").run()
        stored = at.session_state["completed_run"]
        self.assertEqual(stored.settings.description, "A system has a Sensor.")
        self.assertEqual(stored.settings.model, "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertTrue(any(item.value == "A system has a Sensor." for item in at.text))
        self.assertFalse(at.exception)

    def test_provider_constructor_failure_cannot_expose_a_credential(self):
        self.environment()
        at = self.app()
        previous = self.complete_run(at)
        with patch(
            "engine.OpenAIChatGenerator",
            side_effect=ValueError("Provider constructor: test-secret-never-exported"),
        ):
            find(at.button, "Run validation").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("could not finish" in item.value for item in at.error))
        self.assertTrue(all("test-secret-never-exported" not in item.value for item in at.error))
        self.assertEqual(at.session_state["completed_run"].run_id, previous.run_id)

    def test_unavailable_analyzer_never_appears_as_zero_or_accepted(self):
        self.environment(UnavailableValidator)
        at = self.app()
        result = self.complete_run(at)
        self.assertEqual(result.status, "validator_unavailable")
        self.assertIsNone(result.best)
        self.assertTrue(any("Validator unavailable" in item.value for item in at.error))
        self.assertEqual(at.metric[0].value, "1/1")
        self.assertEqual(at.metric[2].value, "N/A")
        self.assertFalse(result.iterations[0].passed)
        self.assertEqual(at.dataframe[0].value.iloc[0]["Semantics"], "N/A")

    def test_generation_failure_without_a_completed_loop_has_no_pass_rate(self):
        self.environment()
        at = self.app()
        with patch.object(FakeGenerator, "generate", side_effect=ValueError("Bad response")):
            result = self.complete_run(at)
        self.assertEqual(result.status, "generation_failed")
        self.assertEqual(result.iterations, ())
        self.assertIsNone(result.pass_rate)
        self.assertEqual(at.metric[2].value, "N/A")
        self.assertTrue(any("Generation stopped" in item.value for item in at.error))

    def test_interface_has_no_examples_tutorials_or_legacy_scoring(self):
        self.environment()
        at = self.app()
        self.assertEqual(len(at.info), 0)
        self.assertEqual(len(at.caption), 0)
        self.assertEqual(len(at.get("code")), 0)
        self.assertEqual([button.label for button in at.button], ["Run validation"])
        self.assertEqual([panel.label for panel in at.expander], ["Advanced settings"])
        self.assertEqual(at.text_area(key="cps_description").value, "")
        self.assertTrue(all(not area.proto.placeholder for area in at.text_area))
        self.assertTrue(all(not field.proto.help for field in at.text_input))
        self.complete_run(at, loops=1)
        self.assertTrue(all("legacy" not in item.label.lower() for item in at.checkbox))
        self.assertTrue(all("Legacy" not in col for col in at.dataframe[0].value.columns))
        self.assertFalse(at.exception)

    def test_loop_count_is_honored_and_early_stop_is_optional(self):
        self.environment()
        at = self.app()
        result = self.complete_run(at, loops=5)
        self.assertEqual(result.settings.iterations, 5)
        self.assertFalse(result.settings.early_stop)
        self.assertEqual(len(result.iterations), 5)
        result = self.complete_run(at, loops=5, early_stop=True)
        self.assertEqual(result.settings.iterations, 5)
        self.assertTrue(result.settings.early_stop)
        self.assertEqual(len(result.iterations), 1)
        self.assertEqual(result.status, "early_stopped")

    def test_every_version_is_visible_and_rerender_keeps_the_completed_run(self):
        self.environment()
        at = self.app()
        result = self.complete_run(at, loops=3)
        self.assertEqual(
            [panel.value for panel in at.get("code")], [r.code for r in result.iterations]
        )
        self.assertEqual(len({r.code for r in result.iterations}), 3)
        labels = [button.label for button in at.get("download_button")]
        for record in result.iterations:
            self.assertIn(f"Download loop {record.loop}", labels)
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["completed_run"].run_id, result.run_id)
        self.assertEqual(
            [panel.value for panel in at.get("code")], [r.code for r in result.iterations]
        )

    def test_provider_neutral_connection_values_appear_in_controls(self):
        self.environment()
        os.environ.update(
            LLM_MODEL="provider/custom-model",
            LLM_BASE_URL="https://provider.example/v1",
            LLM_API_KEY="configured-test-secret",
        )
        at = self.app()
        self.assertEqual(find(at.text_input, "Model ID").value, "provider/custom-model")
        self.assertEqual(find(at.text_input, "API base URL").value, "https://provider.example/v1")
        self.assertEqual(find(at.text_input, "API key").value, "")
        self.assertEqual(len(at.caption), 0)
        at.text_area(key="cps_description").set_value("A system has a Sensor.")
        find(at.number_input, "Number of loops").set_value(1)
        find(at.button, "Run validation").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.session_state["completed_run"].iterations), 1)
        self.assertNotIn("configured-test-secret", export_json(at.session_state["completed_run"]))

    @patch("engine.time.sleep")
    def test_seven_loops_with_transient_fifth_failure_show_seven_versions(self, _):
        class RecoveringGenerator(FakeGenerator):
            def generate(self, **kwargs):
                self.calls += 1
                if self.calls == 5:
                    raise GenerationError(
                        "Missing completion choices.", code="missing_choices", retryable=True
                    )
                return Generation(f"package Model{self.calls} {{ part def Sensor; }}", 20, 10)

        self.environment()
        with patch("engine.OpenAIChatGenerator", RecoveringGenerator):
            at = self.app()
            result = self.complete_run(at, loops=7)
        self.assertEqual(result.settings.iterations, 7)
        self.assertEqual(len(result.iterations), 7)
        self.assertEqual(len(result.attempts), 8)
        self.assertEqual(len(at.get("code")), 7)
        self.assertTrue(any("Completed 7 of 7 loops" == item.value for item in at.header))
        self.assertTrue(any("Loop 5/7" in item.value for item in at.warning))
        self.assertEqual(
            [tab.label for tab in at.tabs],
            [
                "Validation dashboard",
                "Generated versions",
                "Engineering review",
                "Provider attempts",
            ],
        )
        self.assertTrue(all(item.label != "Best automated score" for item in at.metric))

    def test_review_requirements_and_budget_are_frozen_and_exported(self):
        self.environment()
        at = self.app()
        at.text_area(key="review_requirements").set_value(
            "The sensor sends temperature.\nThe controller reads temperature."
        )
        at.number_input(key="max_output_tokens").set_value(16384)
        result = self.complete_run(at, loops=1)
        self.assertEqual(result.settings.max_output_tokens, 16384)
        self.assertEqual(len(result.settings.requirements), 2)
        payload = __import__("json").loads(export_json(result))
        self.assertEqual(payload["language"], "OMG SysML v2 textual notation")
        self.assertIsNone(payload["measurements"][0]["manual_requirement_pass_percent"])

    def test_engineering_review_requires_evidence_and_preserves_automated_results(self):
        self.environment()
        at = self.app()
        original = self.complete_run(at, loops=2)
        find(at.selectbox, "Assessment").set_value("Fail")
        find(at.button, "Save engineering review").click().run()
        self.assertTrue(any("Add evidence" in item.value for item in at.error))
        find(at.text_area, "Model evidence or reason").set_value("No system assembly is defined.")
        find(at.button, "Save engineering review").click().run()
        self.assertFalse(at.exception)
        updated = at.session_state["completed_run"]
        self.assertEqual(updated.reviews[0].assessment, "Fail")
        self.assertEqual(updated.reviews[0].evidence, "No system assembly is defined.")
        self.assertEqual(updated.iterations, original.iterations)
        self.assertEqual(updated.best, original.best)
        self.assertTrue(updated.reviewed_at)
        find(at.selectbox, "Version to review").set_value(2).run()
        self.assertEqual(find(at.selectbox, "Assessment").value, "Not reviewed")
        find(at.selectbox, "Version to review").set_value(1).run()
        self.assertEqual(find(at.selectbox, "Assessment").value, "Fail")
        self.assertEqual(at.session_state["completed_run"].reviews, updated.reviews)


class PresentationTests(unittest.TestCase):
    def test_hot_reload_preserves_existing_versions_and_scores(self):
        from engine import RunSettings, run_loop

        current = run_loop(
            RunSettings("A system", iterations=1), FakeGenerator("m", "key"), FakeValidator()
        )
        legacy_type = dataclasses.make_dataclass(
            "OldRun",
            [
                (name, object)
                for name in (
                    "settings",
                    "iterations",
                    "status",
                    "reason",
                    "run_id",
                    "started_at",
                    "ended_at",
                    "mode",
                )
            ],
        )
        old = legacy_type(
            **{
                field.name: getattr(current, field.name)
                for field in dataclasses.fields(legacy_type)
            }
        )
        upgraded = upgrade_session_result(old)
        self.assertEqual(upgraded.run_id, current.run_id)
        self.assertEqual(upgraded.iterations[0].code, current.iterations[0].code)
        self.assertEqual(
            upgraded.iterations[0].automated_score, current.iterations[0].automated_score
        )
        self.assertEqual(upgraded.attempts, ())

    def test_missing_values_stay_missing_and_break_lines(self):
        rows = [
            {"loop": 1, "automated_score": 100},
            {"loop": 2, "automated_score": None},
            {"loop": 3, "automated_score": 90},
        ]
        data = plot_records(rows, {"automated_score": "Automated score"})
        self.assertIsNone(data[1]["Value"])
        self.assertNotEqual(data[0]["Segment"], data[2]["Segment"])
        chart = measurement_chart(
            rows,
            {"automated_score": "Automated score"},
            colors=["#173A5E"],
            height=320,
            y_title="Automated check score",
            percentage=True,
        ).to_dict()
        self.assertEqual(chart["encoding"]["y"]["scale"]["domain"], [0, 100])
        self.assertEqual(chart["transform"][0]["filter"], "isValid(datum.Value)")
        self.assertEqual(format_number(None), "N/A")
        self.assertEqual(format_number(0), "0")
        self.assertEqual(format_number(82.5), "82.5")

    def test_prompt_and_expected_name_input_bounds(self):
        self.assertEqual(expected_names_from_text("Sensor\n\nController"), ("Sensor", "Controller"))
        for names in (
            "Sensor\nsensor",
            "x" * 81,
            "\n".join(f"n{i}" for i in range(31)),
        ):
            with self.assertRaises(ValueError):
                expected_names_from_text(names)
        for content in (b"\xff", b"", b"x" * 8001):
            with self.assertRaises(ValueError):
                prompt_from_upload(io.BytesIO(content))
        self.assertEqual(prompt_from_upload(io.BytesIO(b"\xef\xbb\xbfA prompt")), "A prompt")

    def test_table_uses_canonical_measurements_without_code(self):
        source = {
            "loop": 1,
            "automated_score": 82.5,
            "delta": None,
            "passed": False,
            "error_count": 0,
            "warning_count": 2,
            "input_tokens": None,
            "output_tokens": 10,
            "total_tokens": None,
            "cumulative_tokens": None,
            "cumulative_pass_rate": 0,
        }
        row = table_rows([source])[0]
        self.assertNotIn("Legacy points", row)
        self.assertEqual(row["Input tokens"], "N/A")
        self.assertNotIn("code", row)
        self.assertIsNone(source["input_tokens"])


if __name__ == "__main__":
    unittest.main()
