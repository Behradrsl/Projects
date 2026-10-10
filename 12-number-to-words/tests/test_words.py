import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from number_words import number_to_words

ROOT = Path(__file__).resolve().parents[1]


class WordsTests(unittest.TestCase):
    def test_examples_and_boundaries(self):
        examples = {
            0: "zero",
            19: "nineteen",
            21: "twenty-one",
            100: "one hundred",
            101: "one hundred one",
            257: "two hundred fifty-seven",
            1001: "one thousand one",
            3890: "three thousand eight hundred ninety",
            600000: "six hundred thousand",
            1000000: "one million",
            1000000001: "one billion one",
            -42: "minus forty-two",
            999999999999: (
                "nine hundred ninety-nine billion nine hundred ninety-nine "
                "million nine hundred ninety-nine thousand nine hundred "
                "ninety-nine"
            ),
        }
        for number, expected in examples.items():
            with self.subTest(number=number):
                self.assertEqual(number_to_words(number), expected)

    def test_invalid_values(self):
        for value in (True, 1.5, "12", 10**12, -(10**12)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                number_to_words(value)

    def test_cli_and_interactive_retry_from_another_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, str(ROOT / "main.py"), "12345"],
                cwd=folder,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                result.stdout.strip(), "twelve thousand three hundred forty-five"
            )
            result = subprocess.run(
                [sys.executable, str(ROOT / "main.py")],
                cwd=folder,
                input="bad\n42\nq\n",
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("forty-two", result.stdout)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
