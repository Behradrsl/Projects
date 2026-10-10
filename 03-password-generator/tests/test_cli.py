"""Exercise the menu and run real entry points without installed packages."""

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from password_generator.__main__ import ask_number, ask_separator, ask_yes_no, main


class MenuTests(unittest.TestCase):
    def run_menu(self, answers):
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            self.assertEqual(main(), 0)
        return output.getvalue()

    def test_random_password_and_regenerate_without_reentering_settings(self):
        output = self.run_menu(["1", "", "", "", "", "q"])
        self.assertEqual(output.count("Your password:"), 2)
        self.assertIn("Goodbye!", output)

    def test_pin_generation_and_invalid_menu_choice(self):
        output = self.run_menu(["invalid", "3", "4", "q"])
        self.assertIn("Please choose 1, 2, 3, or 0.", output)
        result = output.split("Your PIN: ")[1].splitlines()[0]
        self.assertEqual(len(result), 4)
        self.assertTrue(result.isdigit())

    def test_memorable_menu_passes_options_to_generator(self):
        with patch("password_generator.__main__.MemorablePasswordGenerator") as generator:
            generator.return_value.generate.return_value = "River.Cloud.Stone"
            output = self.run_menu(["2", "3", ".", "yes", "m", "0"])
            generator.assert_called_once_with(3, ".", True)
            self.assertIn("River.Cloud.Stone", output)

    def test_invalid_result_action_does_not_generate_again(self):
        output = self.run_menu(["3", "", "invalid", "m", "0"])
        self.assertEqual(output.count("Your PIN:"), 1)
        self.assertIn("Press Enter, m, or q.", output)

    def test_separator_retries_and_supports_none(self):
        with patch("builtins.input", side_effect=["toolong", "none"]):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(ask_separator(), "")
        with patch("builtins.input", return_value=""):
            self.assertEqual(ask_separator(), "-")
        with patch("builtins.input", return_value=" "):
            self.assertEqual(ask_separator(), " ")

    def test_number_prompt_retries_invalid_input(self):
        with patch("builtins.input", side_effect=["oops", "-1", "3.5", "8"]):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(ask_number("Length", 16, 8, 128), 8)

    def test_yes_no_prompt_retries_and_supports_default(self):
        with patch("builtins.input", side_effect=["maybe", "n"]):
            with redirect_stdout(io.StringIO()):
                self.assertFalse(ask_yes_no("Numbers?"))
        with patch("builtins.input", return_value=""):
            self.assertFalse(ask_yes_no("Capitalize?", default=False))

    def test_interrupt_and_end_of_input_exit_cleanly(self):
        for error in (KeyboardInterrupt, EOFError):
            with self.subTest(error=error):
                self.assertIn("Goodbye!", self.run_menu(error))

    def test_entry_points_work_without_dependencies_from_another_directory(self):
        root = Path(__file__).resolve().parents[1]
        for entry in (root / "main.py", root / "src/password_generator/__main__.py"):
            with self.subTest(entry=entry), tempfile.TemporaryDirectory() as directory:
                # -S removes site-packages, including NLTK and editable installations.
                result = subprocess.run(
                    [sys.executable, "-S", str(entry)],
                    input="1\n\n\n\nm\n2\n\n\n\nm\n3\n\nq\n",
                    cwd=directory,
                    text=True,
                    capture_output=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Your password:", result.stdout)
                self.assertIn("Your memorable password:", result.stdout)
                self.assertIn("Your PIN:", result.stdout)
                self.assertIn("Goodbye!", result.stdout)


if __name__ == "__main__":
    unittest.main()
