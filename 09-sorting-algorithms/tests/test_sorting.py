import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from main import parse_numbers
from sorting import ALGORITHMS

ROOT = Path(__file__).resolve().parents[1]


class SortingTests(unittest.TestCase):
    def test_algorithms_match_builtin_and_preserve_input(self):
        rng = random.Random(42)
        cases = [[], [1], [2, 2, 2], [1, 2, 3], [3, 2, 1], [0, -4, 3, -4]]
        cases += [[rng.randint(-50, 50) for _ in range(n)] for n in range(50)]
        for name, function in ALGORITHMS.items():
            for numbers in cases:
                with self.subTest(algorithm=name, numbers=numbers):
                    original = numbers.copy()
                    self.assertEqual(function(numbers), sorted(numbers))
                    self.assertEqual(numbers, original)
                    self.assertIsNot(function(numbers), numbers)

    def test_parser(self):
        self.assertEqual(parse_numbers("8, 3 -1,3"), [8, 3, -1, 3])
        for value in ("", "1.5 3", "a", "1 " * 2001):
            with self.subTest(value=value[:20]), self.assertRaises(ValueError):
                parse_numbers(value)

    def test_cli_compares_all_algorithms_from_another_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, str(ROOT / "main.py"), "8", "3", "-1", "3"],
                text=True,
                capture_output=True,
                cwd=folder,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("[-1, 3, 3, 8]"), 3)

    def test_random_input_is_repeatable(self):
        command = [
            sys.executable,
            str(ROOT / "main.py"),
            "--random",
            "8",
            "--seed",
            "42",
        ]
        results = [
            subprocess.run(command, text=True, capture_output=True) for _ in range(2)
        ]
        self.assertTrue(all(result.returncode == 0 for result in results))
        inputs = [
            next(
                line for line in result.stdout.splitlines() if line.startswith("Input:")
            )
            for result in results
        ]
        self.assertEqual(inputs[0], inputs[1])

    def test_single_algorithm_and_invalid_arguments(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "main.py"),
                "3",
                "1",
                "--algorithm",
                "insertion",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Insertion", result.stdout)
        self.assertNotIn("Bubble", result.stdout)
        for arguments in (
            ["--random", "0"],
            ["--seed", "1"],
            ["1", "--random", "4"],
            ["a"],
        ):
            result = subprocess.run(
                [sys.executable, str(ROOT / "main.py"), *arguments],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_interactive_prompt(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "main.py")],
            input="4,2,4\n",
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("[2, 4, 4]", result.stdout)


if __name__ == "__main__":
    unittest.main()
