import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from number_guesser.cli import main, show_stats
from number_guesser.storage import Record, ScoreStore


class CliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "scores.json"
        self.args = ["--name", "Ada", "--difficulty", "normal", "--scores-file", str(self.path)]

    def run_cli(self, inputs, extra=()):
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch("builtins.input", side_effect=inputs),
            patch("number_guesser.game.random.randint", return_value=42),
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            code = main(self.args + list(extra))
        return code, output.getvalue(), errors.getvalue()

    def test_full_round_validation_commands_and_persistence(self):
        code, output, errors = self.run_cli(
            ["abc", "101", "help", "20", "20", "history", "42", "n"]
        )
        self.assertEqual(code, 0)
        self.assertIn("Go higher!", output)
        self.assertIn("already tried", output)
        self.assertIn("Your guesses: 20", output)
        self.assertIn("Final score: 85/100", output)
        self.assertEqual(errors, "")
        record = ScoreStore(self.path).load()[0]
        self.assertEqual((record.player, record.attempts, record.score), ("Ada", 2, 85))

    def test_practice_mode_does_not_create_history(self):
        self.run_cli(["42", "n"], ["--no-save"])
        self.assertFalse(self.path.exists())

    def test_quit_eof_and_interrupt_save_abandoned_round(self):
        for signal, expected in (("quit", 0), (EOFError(), 0), (KeyboardInterrupt(), 130)):
            with self.subTest(signal=signal):
                code, _, _ = self.run_cli([signal])
                self.assertEqual(code, expected)
                record = ScoreStore(self.path).load()[-1]
                self.assertEqual((record.outcome, record.score), ("quit", 0))

    def test_replay_creates_independent_rounds(self):
        self.run_cli(["42", "y", "42", "n"])
        self.assertEqual(len(ScoreStore(self.path).load()), 2)

    def test_loss_then_difficulty_change(self):
        code, output, _ = self.run_cli(["1", "2", "3", "4", "5", "6", "7", "m", "hard", "42", "n"])
        self.assertEqual(code, 0)
        self.assertIn("Out of attempts", output)
        records = ScoreStore(self.path).load()
        self.assertEqual(records[0].outcome, "lost")
        self.assertEqual((records[1].difficulty, records[1].score), ("hard", 100))

    def test_leaderboard_orders_scores_and_filters_player(self):
        store = ScoreStore(self.path)
        for name, attempts, score in (("Grace", 3, 70), ("Ada", 1, 100), ("Linus", 2, 85)):
            store.append(
                Record(name, "normal", "won", attempts, score, "2026-01-01T12:00:00+00:00")
            )
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertTrue(show_stats(store))
        text = output.getvalue()
        self.assertLess(text.index("Ada"), text.index("Linus"))
        self.assertLess(text.index("Linus"), text.index("Grace"))
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertTrue(show_stats(store, "Ada"))
        self.assertIn("Rounds: 1", output.getvalue())
        self.assertNotIn("Grace", output.getvalue())

    def test_invalid_cli_options_exit_with_usage_error(self):
        for extra in (["--name", "\x1b[31m"], ["--difficulty", "unknown"]):
            with self.subTest(extra=extra), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(self.args + extra)
                self.assertEqual(error.exception.code, 2)

    def test_storage_failure_does_not_prevent_play(self):
        self.path.write_text("broken history")
        code, output, errors = self.run_cli(["42", "n"])
        self.assertEqual(code, 0)
        self.assertIn("Correct!", output)
        self.assertIn("This round was not saved", errors)
        self.assertEqual(self.path.read_text(), "broken history")

    def test_stats_on_corrupt_history_exits_with_error(self):
        self.path.write_text("broken history")
        _, _, errors = self.run_cli([], ["--stats"])
        self.assertIn("Cannot read history", errors)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--stats", "--scores-file", str(self.path)]), 1)

    def test_menu_stats_and_difficulty_selection(self):
        output = io.StringIO()
        with (
            patch("builtins.input", side_effect=["", "stats", "bad", "1", "quit"]),
            patch("number_guesser.game.random.randint", return_value=42),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["--no-save", "--scores-file", str(self.path)]), 0)
        self.assertIn("No saved rounds yet", output.getvalue())
        self.assertIn("Easy", output.getvalue())
