import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tic_tac_toe import WINNING_LINES, TicTacToe

ROOT = Path(__file__).resolve().parents[1]


class GameTests(unittest.TestCase):
    def test_every_winning_line_for_both_players(self):
        for player in ("X", "O"):
            for line in WINNING_LINES:
                with self.subTest(player=player, line=line):
                    game = TicTacToe(player)
                    other = [i for i in range(9) if i not in line]
                    for cell in (line[0], other[0], line[1], other[1], line[2]):
                        game.play(cell + 1)
                    self.assertEqual(game.winner, player)
                    self.assertTrue(game.finished)
                    with self.assertRaises(ValueError):
                        game.play(other[2] + 1)

    def test_draw_ends_after_ninth_move(self):
        game = TicTacToe("X")
        for index, cell in enumerate([1, 2, 3, 5, 4, 6, 8, 7, 9]):
            game.play(cell)
            self.assertEqual(game.finished, index == 8)
        self.assertIsNone(game.winner)

    def test_invalid_move_keeps_turn_and_board(self):
        game = TicTacToe("X")
        for cell in (0, 10, True, 1.5, "1"):
            with self.assertRaises(ValueError):
                game.play(cell)
            self.assertEqual(game.current_player, "X")
            self.assertEqual(game.board, [""] * 9)
        game.play(1)
        with self.assertRaises(ValueError):
            game.play(1)
        self.assertEqual(game.current_player, "O")
        self.assertIn("X | 2 | 3", str(game))

    def test_random_first_player_is_a_mark(self):
        self.assertIn(TicTacToe().current_player, ("X", "O"))
        with self.assertRaises(ValueError):
            TicTacToe("Z")

    def test_terminal_win_invalid_input_and_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, str(ROOT / "main.py"), "--first", "X"],
                input="hello\n1\n1\n4\n2\n5\n3\ny\nq\n",
                text=True,
                capture_output=True,
                cwd=folder,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("That cell is taken", result.stdout)
        self.assertIn("Player X wins!", result.stdout)
        self.assertEqual(result.stdout.count("Player X starts."), 2)

    def test_terminal_draw_and_eof(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "main.py"), "--first", "X"],
            input="1\n2\n3\n5\n4\n6\n8\n7\n9\n",
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("It's a draw!", result.stdout)


if __name__ == "__main__":
    unittest.main()
