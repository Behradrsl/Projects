"""Prove the door rules exhaustively and check real terminal usage."""

import io
import random
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from main import main
from monty_hall import DOORS, Round, create_round, monty_hall_game, simulate_games


class MontyHallTests(unittest.TestCase):
    def test_all_nine_prize_and_choice_combinations(self):
        stay_wins = switch_wins = 0
        for car in DOORS:
            for initial in DOORS:
                reveal = next(door for door in DOORS if door != car and door != initial)
                rng = Mock()
                rng.choice.side_effect = [car, reveal]
                game = create_round(initial, rng)
                with self.subTest(car=car, initial=initial):
                    self.assertNotEqual(game.revealed, game.car)
                    self.assertNotEqual(game.revealed, game.initial)
                    self.assertEqual({game.initial, game.revealed, game.remaining}, set(DOORS))
                    self.assertNotEqual(game.won(False), game.won(True))
                stay_wins += game.won(False)
                switch_wins += game.won(True)
        self.assertEqual(stay_wins, 3)
        self.assertEqual(switch_wins, 6)

    def test_host_can_reveal_either_goat_if_initial_pick_is_car(self):
        for revealed in (2, 3):
            rng = Mock()
            rng.choice.side_effect = [1, revealed]
            game = create_round(1, rng)
            self.assertEqual(game.revealed, revealed)
            self.assertTrue(game.won(False))
            self.assertFalse(game.won(True))

    def test_single_game_and_seeded_simulation(self):
        self.assertIsInstance(monty_hall_game(True, random.Random(7)), bool)
        result = simulate_games(2000, seed=42)
        self.assertEqual(result, simulate_games(2000, seed=42))
        self.assertEqual(sum(result), 2000)
        self.assertTrue(all(0 <= count <= 2000 for count in result))
        self.assertEqual(sum(simulate_games(1, seed=1)), 1)

    def test_invalid_inputs(self):
        for door in (0, 4, True, 1.0, "1"):
            with self.subTest(door=door), self.assertRaises(ValueError):
                create_round(door)
        for count in (0, -1, 1_000_001, True, 1.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                simulate_games(count)
        with self.assertRaises(ValueError):
            simulate_games(10, seed="invalid")

    def test_terminal_play_and_invalid_choices(self):
        output = io.StringIO()
        with patch("main.create_round", return_value=Round(2, 1, 3, 2)):
            with patch("builtins.input", side_effect=["wrong", "1", "4", "1", "x", "s", "0"]):
                with redirect_stdout(output):
                    self.assertEqual(main([]), 0)
        self.assertIn("Monty opens door 3. It has a goat.", output.getvalue())
        self.assertIn("You won the car!", output.getvalue())

    def test_terminal_simulation(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["2", "100", "0"]):
            with redirect_stdout(output):
                self.assertEqual(main([]), 0)
        self.assertIn("Results for 100 games", output.getvalue())
        self.assertIn("Switch doors:", output.getvalue())

    def test_interrupt_exits_cleanly(self):
        for error in (EOFError, KeyboardInterrupt):
            with patch("builtins.input", side_effect=error), redirect_stdout(io.StringIO()):
                self.assertEqual(main([]), 0)

    def test_script_runs_from_another_directory_without_dependencies(self):
        script = Path(__file__).resolve().parents[1] / "main.py"
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-S", str(script), "--games", "1000", "--seed", "42"],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=10,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Results for 1,000 games", result.stdout)
        self.assertIn("Random seed: 42", result.stdout)

    def test_invalid_simulation_arguments(self):
        script = Path(__file__).resolve().parents[1] / "main.py"
        for args in (["--games", "0"], ["--seed", "42"]):
            result = subprocess.run(
                [sys.executable, str(script), *args],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
