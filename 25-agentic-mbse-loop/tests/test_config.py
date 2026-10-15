"""Connection precedence and explicit CLI loop controls without remote calls."""

import contextlib
import dataclasses
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from config import DEFAULT_BASE_URL, DEFAULT_MODEL, Connection, load_connection
from engine import Generation
from engine import run_loop as execute_loop
from validator import ValidationResult
from verify_integration import main, parse_args


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_no_settings_default_to_selected_model_and_openrouter_without_key(self):
        connection = load_connection(self.root)
        self.assertEqual(connection.api_key, "")
        self.assertEqual(connection.model, DEFAULT_MODEL)
        self.assertEqual(connection.base_url, DEFAULT_BASE_URL)

    def test_canonical_values_win_over_legacy_values_per_field(self):
        os.environ.update(
            LLM_API_KEY="fixture-new-key",
            LLM_MODEL="new/model",
            LLM_BASE_URL="https://new.example/api/v1",
            OPENAI_API_KEY="fixture-old-key",
            OPENAI_MODEL="old-model",
            OPENAI_BASE_URL="https://old.example/v1",
        )
        self.assertEqual(
            load_connection(self.root),
            Connection("fixture-new-key", "new/model", "https://new.example/api/v1"),
        )

    def test_missing_canonical_fields_fall_back_independently(self):
        os.environ.update(
            LLM_MODEL="new/model",
            OPENAI_API_KEY="fixture-legacy-key",
            OPENAI_MODEL="old-model",
            OPENAI_BASE_URL="https://legacy.example/v1",
        )
        self.assertEqual(
            load_connection(self.root),
            Connection("fixture-legacy-key", "new/model", "https://legacy.example/v1"),
        )

    def test_blank_canonical_key_model_and_url_never_reuse_legacy_values(self):
        os.environ.update(
            LLM_API_KEY="  ",
            LLM_MODEL="",
            LLM_BASE_URL="",
            OPENAI_API_KEY="fixture-old-key",
            OPENAI_MODEL="old-model",
            OPENAI_BASE_URL="https://old.example/v1",
        )
        self.assertEqual(load_connection(self.root), Connection("", "", None))

    def test_legacy_key_only_preserves_direct_openai_defaults(self):
        os.environ["OPENAI_API_KEY"] = "fixture-legacy-key"
        self.assertEqual(
            load_connection(self.root), Connection("fixture-legacy-key", "gpt-4.1-mini", None)
        )

    def test_legacy_model_with_missing_or_blank_url_does_not_use_openrouter(self):
        os.environ.update(OPENAI_API_KEY="fixture-legacy-key", OPENAI_MODEL="legacy-model")
        self.assertEqual(load_connection(self.root).model, "legacy-model")
        self.assertIsNone(load_connection(self.root).base_url)
        os.environ["OPENAI_BASE_URL"] = "  "
        self.assertIsNone(load_connection(self.root).base_url)

    def test_blank_legacy_model_keeps_historical_default_but_canonical_blank_does_not(self):
        os.environ.update(OPENAI_API_KEY="", OPENAI_MODEL="  ", OPENAI_BASE_URL="")
        self.assertEqual(load_connection(self.root), Connection("", "gpt-4.1-mini", None))
        os.environ["LLM_MODEL"] = ""
        self.assertEqual(load_connection(self.root), Connection("", "", None))

    def test_new_key_only_uses_provider_neutral_defaults(self):
        os.environ["LLM_API_KEY"] = "fixture-router-key"
        connection = load_connection(self.root)
        self.assertEqual(connection.model, DEFAULT_MODEL)
        self.assertEqual(connection.base_url, DEFAULT_BASE_URL)

    def test_local_dotenv_loads_without_overriding_process_settings(self):
        (self.root / ".env").write_text(
            "LLM_API_KEY=fixture-file-key\n"
            "LLM_MODEL=file-model\n"
            "LLM_BASE_URL=https://file.example/v1\n",
            encoding="utf-8",
        )
        os.environ["LLM_MODEL"] = "process-model"
        os.environ["LLM_API_KEY"] = ""
        connection = load_connection(self.root)
        self.assertEqual(connection.api_key, "")
        self.assertEqual(connection.model, "process-model")
        self.assertEqual(connection.base_url, "https://file.example/v1")

    def test_connection_does_not_expose_key_in_repr_and_is_frozen(self):
        connection = Connection("fixture-key-not-for-logs", DEFAULT_MODEL, DEFAULT_BASE_URL)
        self.assertNotIn(connection.api_key, repr(connection))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            connection.api_key = "changed"


class IntegrationCLITests(unittest.TestCase):
    def test_live_defaults_to_four_loops_and_continues_after_a_pass(self):
        args = parse_args(["--live"])
        self.assertEqual(args.loops, 4)
        self.assertFalse(args.early_stop)

    def test_explicit_loop_count_and_early_stopping_are_accepted(self):
        for loops in (1, 8):
            with self.subTest(loops=loops):
                args = parse_args(["--live", "--loops", str(loops), "--early-stop"])
                self.assertEqual(args.loops, loops)
                self.assertTrue(args.early_stop)

    def test_invalid_loop_bounds_and_offline_loop_options_are_rejected(self):
        invalid = (
            ["--live", "--loops", "0"],
            ["--live", "--loops", "9"],
            ["--live", "--loops", "1.5"],
            ["--offline", "--loops", "4"],
            ["--offline", "--early-stop"],
        )
        for arguments in invalid:
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    parse_args(arguments)
            self.assertEqual(caught.exception.code, 2)

    def test_help_explains_default_and_live_only_controls(self):
        text = io.StringIO()
        with contextlib.redirect_stdout(text), self.assertRaises(SystemExit) as caught:
            parse_args(["--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("default: 4", text.getvalue())
        self.assertIn("default: off", text.getvalue())
        self.assertIn("Live mode only", text.getvalue())

    def test_missing_canonical_key_does_not_construct_a_provider(self):
        connection = Connection("", DEFAULT_MODEL, DEFAULT_BASE_URL)
        output = io.StringIO()
        with (
            patch("verify_integration.load_connection", return_value=connection),
            patch("verify_integration.OpenAIChatGenerator") as generator,
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(main(["--live"]), 2)
        generator.assert_not_called()
        self.assertIn("LLM_API_KEY", output.getvalue())

    def run_live_fixture(self, arguments):
        connection = Connection("fixture-router-key", DEFAULT_MODEL, DEFAULT_BASE_URL)
        generator = Mock(mode="live", secret_values=(connection.api_key,))
        generator.generate.return_value = Generation("package Example { part def Sensor; }", 2, 3)
        validator = Mock()
        validator.validate.return_value = ValidationResult("valid", "valid", name_score=100)
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch("verify_integration.load_connection", return_value=connection),
                patch("verify_integration.OpenAIChatGenerator") as create_generator,
                patch(
                    "verify_integration.run_loop",
                    side_effect=lambda settings, active: execute_loop(settings, active, validator),
                ),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                create_generator.return_value.__enter__.return_value = generator
                code = main(["--live", "--output", directory, *arguments])
            self.assertEqual(code, 0)
            create_generator.assert_called_once_with(
                DEFAULT_MODEL, connection.api_key, DEFAULT_BASE_URL, max_output_tokens=8192
            )
            records = list(Path(directory).glob("live-*/run_record.json"))
            self.assertEqual(len(records), 1)
            return json.loads(records[0].read_text(encoding="utf-8")), generator

    def test_live_default_controls_reach_engine_and_record_without_hidden_early_stop(self):
        record, generator = self.run_live_fixture([])
        self.assertEqual(record["settings"]["iterations"], 4)
        self.assertFalse(record["settings"]["early_stop"])
        self.assertEqual(len(record["iterations"]), 4)
        self.assertEqual(generator.generate.call_count, 4)

    def test_live_explicit_early_stop_reaches_engine_and_retains_requested_loop_limit(self):
        record, generator = self.run_live_fixture(["--loops", "3", "--early-stop"])
        self.assertEqual(record["settings"]["iterations"], 3)
        self.assertTrue(record["settings"]["early_stop"])
        self.assertEqual(record["status"], "early_stopped")
        self.assertEqual(len(record["iterations"]), 1)
        self.assertEqual(generator.generate.call_count, 1)


if __name__ == "__main__":
    unittest.main()
