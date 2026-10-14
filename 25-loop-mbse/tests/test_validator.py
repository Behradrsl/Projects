"""Actual grammar/analyzer integration and fail-closed adapter checks."""

import dataclasses
import unittest
from pathlib import Path
from unittest.mock import patch

from validator import (
    Diagnostic,
    SysMLValidator,
    ValidationResult,
    _validate_source,
    expected_name_presence,
    lexical_names,
)

VALID_MODEL = "package Demo { part def Sensor; part sensor : Sensor; }"


class LexicalNameTests(unittest.TestCase):
    def test_analyzer_exception_is_candidate_limitation_not_language_failure(self):
        with (
            patch("sysmlpy.antlr_parser.parse"),
            patch("sysmlpy.loads"),
            patch("sysmlpy.analyze", side_effect=RuntimeError("Unsupported construct")),
        ):
            result = _validate_source(VALID_MODEL, ("Sensor",))
        self.assertEqual(result.parse_state, "valid")
        self.assertEqual(result.semantic_state, "unavailable")
        self.assertEqual(result.unavailable_scope, "candidate")
        self.assertEqual(result.name_score, 100)

    def test_whole_identifiers_case_insensitive_outside_comments(self):
        code = """package Demo {
            // Battery
            /* Controller */
            part sensors;
            part SENSOR;
            part 'Power Supply';
            attribute label = "Hidden Name";
        }"""
        missing, score = expected_name_presence(
            code,
            (
                "sensor",
                "sensors",
                "Power Supply",
                "Battery",
                "Controller",
                "Hidden Name",
            ),
        )
        self.assertEqual(missing, ("Battery", "Controller", "Hidden Name"))
        self.assertEqual(score, 50)
        self.assertEqual(expected_name_presence(code, ("sen",))[1], 0)

    def test_quotes_and_comment_markers_inside_identifiers(self):
        names = lexical_names(r"part 'Main\'s // Controller'; /* not_a_name */")
        self.assertIn("main's // controller", names)
        self.assertNotIn("not_a_name", names)
        self.assertEqual(expected_name_presence("// Sensor", ()), ((), None))
        self.assertNotIn("sensor", lexical_names("/* Sensor"))

    def test_result_records_are_immutable(self):
        record = ValidationResult("valid", "valid", (Diagnostic("parser", "error", "text"),))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            record.semantic_state = "invalid"


class RealSysMLIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = SysMLValidator()

    @classmethod
    def tearDownClass(cls):
        cls.validator.close()

    def test_01_actual_parser_and_analyzer_accept_known_model(self):
        result = self.validator.validate(VALID_MODEL, ("Sensor", "Demo"))
        self.assertEqual(result.parse_state, "valid", result.diagnostics)
        self.assertEqual(result.semantic_state, "valid", result.diagnostics)
        self.assertEqual(result.diagnostics, ())
        self.assertEqual(result.name_score, 100)

    def test_02_actual_semantic_undefined_type_error(self):
        result = self.validator.validate("package Demo { part sensor : MissingType; }")
        self.assertEqual(result.parse_state, "valid")
        self.assertEqual(result.semantic_state, "invalid")
        self.assertTrue(any("UNDEFINED_SYMBOL" in item.message for item in result.diagnostics))
        self.assertTrue(any("MissingType" in item.message for item in result.diagnostics))

    def test_03_actual_syntax_diagnostic_has_location(self):
        result = self.validator.validate("package Demo { part def Sensor }")
        self.assertEqual(result.parse_state, "invalid")
        self.assertEqual(result.semantic_state, "unavailable")
        self.assertEqual(result.diagnostics[0].stage, "parser")
        self.assertEqual(result.diagnostics[0].line, 1)
        self.assertIsNotNone(result.diagnostics[0].column)
        self.assertIsNone(result.name_score)

    def test_04_constraint_rescue_is_disabled(self):
        result = self.validator.validate("package Demo { constraint c { must be safe } }")
        self.assertEqual(result.parse_state, "invalid")
        self.assertEqual(result.semantic_state, "unavailable")

    def test_05_warnings_are_separate_and_do_not_invent_errors(self):
        result = self.validator.validate("package Demo { part def sensor; }")
        self.assertEqual(result.semantic_state, "valid", result.diagnostics)
        self.assertEqual(result.diagnostics, ())
        self.assertTrue(any("NAMING_CONVENTION" in item.message for item in result.warnings))
        self.assertTrue(all(item.severity == "warning" for item in result.warnings))

    def test_06_real_name_check_cannot_match_comments_or_substrings(self):
        result = self.validator.validate(
            "package Demo { /* Sensor */ part sensorArray; part 'Power Supply'; }",
            ("Sensor", "Power Supply"),
        )
        self.assertEqual(result.parse_state, "valid", result.diagnostics)
        self.assertEqual(result.missing_names, ("Sensor",))
        self.assertEqual(result.name_score, 50)

    def test_07_directed_transfer_assembly_and_reading_example(self):
        code = (
            Path(__file__).resolve().parents[1] / "examples/temperature_monitor.sysml"
        ).read_text()
        result = self.validator.validate(
            code, ("Sensor", "Controller", "MonitoringSystem", "ReadTemperature")
        )
        self.assertEqual(result.parse_state, "valid", result.diagnostics)
        self.assertEqual(result.semantic_state, "valid", result.diagnostics)
        self.assertEqual(result.name_score, 100)
        self.assertIn("flow source.temperature to target.temperature;", code)

    def test_08_definition_specialization_uses_v2_operator(self):
        good = self.validator.validate(
            "package Data { attribute def EnvironmentTemperature :> ScalarValues::Real; }"
        )
        bad = self.validator.validate(
            "package Data { attribute def EnvironmentTemperature : ScalarValues::Real; }"
        )
        self.assertEqual(good.parse_state, "valid", good.diagnostics)
        self.assertEqual(good.semantic_state, "valid", good.diagnostics)
        self.assertEqual(bad.parse_state, "invalid")

    def test_09_conjugation_tool_limit_is_not_a_false_semantic_failure(self):
        code = (
            Path(__file__).resolve().parents[1] / "examples/temperature_monitor_v2.sysml"
        ).read_text()
        result = self.validator.validate(code)
        self.assertEqual(result.parse_state, "valid", result.diagnostics)
        self.assertEqual(result.semantic_state, "unavailable", result.diagnostics)
        self.assertEqual(result.unavailable_scope, "candidate")
        self.assertIn("ANALYZER_LIMITATION", result.diagnostics[0].message)

    def test_10_port_typed_by_scalar_is_a_semantic_error_even_when_symbol_exists(self):
        for typing in ("ScalarValues::Real", "Real"):
            code = f"package Wrong {{ part def Sensor {{ port temperatureOut : {typing}; }} }}"
            result = self.validator.validate(code)
            self.assertEqual(result.parse_state, "valid", result.diagnostics)
            self.assertEqual(result.semantic_state, "invalid", result.diagnostics)
            self.assertTrue(any("PORT_TYPE_KIND" in d.message for d in result.diagnostics))

    def test_11_local_part_definition_cannot_type_a_port(self):
        code = "package Wrong { part def Data; part def Sensor { port output : Data; } }"
        result = self.validator.validate(code)
        self.assertEqual(result.semantic_state, "invalid", result.diagnostics)
        self.assertTrue(any("PORT_TYPE_KIND" in d.message for d in result.diagnostics))

    def test_12_scalar_word_in_comments_does_not_trigger_port_kind_check(self):
        code = (
            "package Correct { port def Real; part def Sensor { port output : Real; } "
            "/* port bad : ScalarValues::Real; */ }"
        )
        result = self.validator.validate(code)
        self.assertEqual(result.parse_state, "valid", result.diagnostics)
        self.assertFalse(any("PORT_TYPE_KIND" in d.message for d in result.diagnostics))

    def test_13_legal_bare_references_warn_without_claiming_composition_or_performance(self):
        code = """package References {
            port def Output { out attribute value : ScalarValues::Real; }
            action def Read { in attribute value : ScalarValues::Real; }
            part def Sensor { output : Output; }
            part def System { sensor : Sensor; reading : Read; }
        }"""
        result = self.validator.validate(code)
        self.assertEqual(result.parse_state, "valid", result.diagnostics)
        self.assertEqual(result.semantic_state, "valid", result.diagnostics)
        observations = [d for d in result.warnings if d.stage == "modeling"]
        self.assertEqual(len(observations), 3)
        self.assertTrue(all(d.message.startswith("REFERENCE_ONLY:") for d in observations))
        self.assertTrue(any("perform action" in d.message for d in observations))

    def test_14_explicit_reference_model_has_no_reference_only_warning(self):
        code = (
            Path(__file__).resolve().parents[1] / "examples/temperature_monitor.sysml"
        ).read_text()
        result = self.validator.validate(code)
        self.assertFalse(any(d.stage == "modeling" for d in result.warnings))

    def test_15_comment_and_scalar_parameters_are_not_modeling_findings(self):
        code = """package Correct {
            part def Sensor;
            action def Read { in value : ScalarValues::Real; }
            /* sensor : Sensor; */
        }"""
        result = self.validator.validate(code)
        self.assertFalse(any(d.stage == "modeling" for d in result.warnings))

    def test_16_unperformed_action_and_flow_only_assembly_prompt_independent_review(self):
        code = """package Model {
            port def Data { out attribute value : ScalarValues::Real; }
            action def Read { in attribute value : ScalarValues::Real; }
            part def Sensor { port output : Data; }
            part def Controller {
                port input : Data;
                action read : Read;
                bind read.value = input.value;
            }
            part def System {
                part sensor : Sensor;
                part controller : Controller;
                flow sensor.output.value to controller.input.value;
            }
        }"""
        result = self.validator.validate(code)
        self.assertEqual(result.parse_state, "valid", result.diagnostics)
        self.assertTrue(any("ACTION_PERFORMER:" in d.message for d in result.warnings))
        self.assertTrue(any("CONNECTION_REVIEW:" in d.message for d in result.warnings))


class UnavailableValidatorTests(unittest.TestCase):
    def test_missing_dependency_is_unavailable(self):
        with patch.dict("sys.modules", {"sysmlpy": None}):
            result = _validate_source(VALID_MODEL, ())
        self.assertEqual(result.parse_state, "unavailable")
        self.assertEqual(result.semantic_state, "unavailable")

    def test_analyzer_absence_is_not_accepted(self):
        with patch("sysmlpy.analyze", None):
            result = _validate_source(VALID_MODEL, ())
        self.assertEqual(result.parse_state, "valid")
        self.assertEqual(result.semantic_state, "unavailable")

    def test_unexpected_parser_exception_is_safe_and_unavailable(self):
        with patch(
            "sysmlpy.antlr_parser.parse",
            side_effect=RuntimeError("secret-provider-key"),
        ):
            result = _validate_source(VALID_MODEL, ())
        self.assertEqual(result.parse_state, "unavailable")
        self.assertNotIn("secret-provider-key", repr(result))

    def test_worker_timeout_does_not_score_as_syntax_failure(self):
        with SysMLValidator(timeout_seconds=0.001) as validator:
            result = validator.validate(VALID_MODEL)
            self.assertEqual(result.parse_state, "unavailable")
            self.assertEqual(result.semantic_state, "unavailable")
            self.assertIn("time limit", result.diagnostics[0].message)
            self.assertIsNone(validator._process)

    def test_invalid_candidate_size_and_names_are_rejected(self):
        with SysMLValidator() as validator:
            for candidate in ("", "x" * 60_001, None):
                self.assertEqual(validator.validate(candidate).parse_state, "unavailable")
            for names in (
                ("Sensor", "sensor"),
                ("",),
                ("x" * 81,),
                tuple(map(str, range(31))),
            ):
                self.assertEqual(validator.validate(VALID_MODEL, names).parse_state, "unavailable")


if __name__ == "__main__":
    unittest.main()
