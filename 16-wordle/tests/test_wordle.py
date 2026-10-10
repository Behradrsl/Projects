import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from wordle import Wordle, feedback, load_words

ROOT = Path(__file__).resolve().parents[1]


class WordleTests(unittest.TestCase):
    def test_repeated_letters_reserve_correct_positions_first(self):
        self.assertEqual(
            feedback("allee", "apple"),
            ("correct", "present", "absent", "absent", "correct"),
        )
        self.assertEqual(
            feedback("eerie", "serve"),
            ("absent", "correct", "correct", "absent", "correct"),
        )
        self.assertEqual(feedback("APPLE", "apple"), ("correct",) * 5)

    def test_invalid_guesses_do_not_consume_turns(self):
        words = ["apple", "ample", "angle", "alien", "arise", "beach", "blame", "bread"]
        game = Wordle("apple", words)
        with self.assertRaises(ValueError):
            game.guess("xxxxx")
        self.assertEqual(game.guesses, [])
        game.guess("ample")
        with self.assertRaises(ValueError):
            game.guess("ample")
        self.assertEqual(len(game.guesses), 1)
        self.assertIn("apple", game.candidates())
        self.assertTrue(
            all(
                feedback("ample", word) == game.guesses[0][1]
                for word in game.candidates()
            )
        )

    def test_win_and_six_guess_loss(self):
        words = ["apple", "ample", "angle", "alien", "arise", "beach", "blame", "bread"]
        game = Wordle("apple", words)
        game.guess("apple")
        self.assertTrue(game.won and game.finished)
        with self.assertRaises(ValueError):
            game.guess("ample")
        game = Wordle("apple", words)
        for word in words[1:7]:
            game.guess(word)
        self.assertTrue(game.finished)
        self.assertFalse(game.won)

    def test_vocabulary_and_cli_from_another_folder(self):
        self.assertGreater(len(load_words(ROOT / "words.txt")), 100)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "words.txt"
            path.write_text("apple\n")
            result = subprocess.run(
                [sys.executable, str(ROOT / "main.py"), "--words", str(path)],
                input="bad\n?\napple\nn\n",
                cwd=folder,
                text=True,
                capture_output=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 possible answers: apple", result.stdout)
        self.assertIn("You got it!", result.stdout)


if __name__ == "__main__":
    unittest.main()
