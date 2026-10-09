import unittest

from number_guesser.game import DIFFICULTIES, Game, Status


class GameTests(unittest.TestCase):
    def test_first_guess_wins_with_full_score(self):
        game = Game(DIFFICULTIES["normal"], secret=42)
        result = game.guess(42)
        self.assertEqual(result.status, Status.WON)
        self.assertEqual(result.score, 100)
        self.assertEqual(result.attempts_left, 6)
        self.assertEqual(game.answer, 42)

    def test_hints_narrow_range_and_score_decreases(self):
        game = Game(DIFFICULTIES["normal"], secret=42)
        self.assertEqual(game.guess(20).direction, "higher")
        self.assertEqual(game.guess(60).direction, "lower")
        self.assertEqual((game.lower_bound, game.upper_bound), (21, 59))
        self.assertEqual(game.guess(42).score, 70)

    def test_invalid_and_duplicate_guesses_do_not_change_state(self):
        game = Game(DIFFICULTIES["normal"], secret=42)
        game.guess(20)
        for value in (20, 0, 101, True, 1.5, "42"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                game.guess(value)
        self.assertEqual(game.guesses, [20])
        self.assertEqual(game.attempts_left, 6)
        self.assertEqual(game.score, 85)

    def test_loss_after_last_attempt(self):
        game = Game(DIFFICULTIES["easy"], secret=50)
        for number in range(1, 9):
            game.guess(number)
        self.assertEqual(game.status, Status.LOST)
        self.assertEqual(game.score, 0)
        self.assertEqual(game.attempts_left, 0)
        with self.assertRaises(RuntimeError):
            game.guess(50)

    def test_win_on_last_attempt_is_allowed(self):
        game = Game(DIFFICULTIES["normal"], secret=42)
        for number in range(1, 7):
            game.guess(number)
        self.assertEqual(game.guess(42).status, Status.WON)
        self.assertEqual(game.score, 10)

    def test_quit_and_hidden_answer(self):
        game = Game(DIFFICULTIES["hard"], secret=1000)
        with self.assertRaises(RuntimeError):
            _ = game.answer
        game.quit()
        self.assertEqual(game.status, Status.QUIT)
        self.assertEqual(game.score, 0)
        self.assertEqual(game.answer, 1000)
        with self.assertRaises(RuntimeError):
            game.quit()

    def test_range_boundaries_are_inclusive(self):
        for mode in DIFFICULTIES.values():
            for secret in (1, mode.upper):
                with self.subTest(mode=mode.name, secret=secret):
                    self.assertEqual(Game(mode, secret=secret).guess(secret).status, Status.WON)

    def test_random_secret_is_within_range(self):
        for mode in DIFFICULTIES.values():
            game = Game(mode)
            game.quit()
            self.assertTrue(1 <= game.answer <= mode.upper)
