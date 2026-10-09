"""Exercise the interactive menu using scripted input."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from password_generator.__main__ import ask_number, ask_yes_no, main


class MenuTests(unittest.TestCase):
    def run_menu(self, answers):
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            self.assertEqual(main(), 0)
        return output.getvalue()

    def test_random_password_with_defaults(self):
        output = self.run_menu(["1", "", "", "", "0"])
        self.assertIn("Generated password:", output)
        self.assertIn("Goodbye!", output)

    def test_pin_generation_and_invalid_menu_choice(self):
        output = self.run_menu(["invalid", "3", "4", "0"])
        self.assertIn("Please choose 1, 2, 3, or 0.", output)
        result = output.split("Generated password: ")[1].splitlines()[0]
        self.assertEqual(len(result), 4)
        self.assertTrue(result.isdigit())

    def test_memorable_menu_passes_options_to_generator(self):
        with patch("password_generator.__main__.MemorablePasswordGenerator") as generator:
            generator.return_value.generate.return_value = "River.Cloud.Stone"
            output = self.run_menu(["2", "3", ".", "yes", "0"])
            generator.assert_called_once_with(3, ".", True)
            self.assertIn("River.Cloud.Stone", output)

    def test_generator_error_returns_to_menu(self):
        with patch("password_generator.__main__.MemorablePasswordGenerator") as generator:
            generator.side_effect = ValueError("Install the word list first.")
            output = self.run_menu(["2", "", "", "", "0"])
            self.assertIn("Install the word list first.", output)
            self.assertIn("Goodbye!", output)

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
                output = self.run_menu(error)
                self.assertIn("Goodbye!", output)


if __name__ == "__main__":
    unittest.main()
