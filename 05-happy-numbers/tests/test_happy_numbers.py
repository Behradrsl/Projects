"""Known results, exact paths, and real command-line usage."""

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from happy_numbers import happy_sequence, is_happy
from main import main


class HappyNumberTests(unittest.TestCase):
    def test_course_examples_and_known_unhappy_numbers(self):
        for number in (1, 7, 10, 19, 44, 86, 139):
            with self.subTest(number=number):
                self.assertTrue(is_happy(number))
        for number in (2, 3, 4, 5, 6, 8, 9, 20):
            with self.subTest(number=number):
                self.assertFalse(is_happy(number))

    def test_exact_happy_path(self):
        self.assertEqual(happy_sequence(19), [19, 82, 68, 100, 1])
        self.assertEqual(happy_sequence(1), [1])

    def test_unhappy_path_includes_first_repeat(self):
        self.assertEqual(happy_sequence(2), [2, 4, 16, 37, 58, 89, 145, 42, 20, 4])

    def test_invalid_values(self):
        for value in (0, -19, True, False, 1.5, "19", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                happy_sequence(value)

    def test_terminal_retries_then_shows_result(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["hello", "0", "19", "q"]):
            with redirect_stdout(output):
                self.assertEqual(main([]), 0)
        self.assertIn("19 is a happy number", output.getvalue())
        self.assertIn("Please enter a positive whole number", output.getvalue())

    def test_interrupt_exits_cleanly(self):
        for error in (EOFError, KeyboardInterrupt):
            with patch("builtins.input", side_effect=error), redirect_stdout(io.StringIO()):
                self.assertEqual(main([]), 0)

    def test_script_runs_from_another_directory_without_dependencies(self):
        script = Path(__file__).resolve().parents[1] / "main.py"
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-S", str(script), "19"],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=10,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1² + 9² = 82", result.stdout)
        self.assertIn("19 is a happy number", result.stdout)

    def test_invalid_command_line_number_exits_with_error(self):
        script = Path(__file__).resolve().parents[1] / "main.py"
        result = subprocess.run(
            [sys.executable, str(script), "0"], capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("positive whole number", result.stderr)


if __name__ == "__main__":
    unittest.main()
