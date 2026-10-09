import unittest

from rock_paper_scissors.game import Match, Move, Outcome, determine_outcome


class RulesTests(unittest.TestCase):
    def test_all_nine_pairings(self):
        expected = (
            (Move.ROCK, Move.ROCK, Outcome.DRAW),
            (Move.ROCK, Move.PAPER, Outcome.LOSS),
            (Move.ROCK, Move.SCISSORS, Outcome.WIN),
            (Move.PAPER, Move.ROCK, Outcome.WIN),
            (Move.PAPER, Move.PAPER, Outcome.DRAW),
            (Move.PAPER, Move.SCISSORS, Outcome.LOSS),
            (Move.SCISSORS, Move.ROCK, Outcome.LOSS),
            (Move.SCISSORS, Move.PAPER, Outcome.WIN),
            (Move.SCISSORS, Move.SCISSORS, Outcome.DRAW),
        )
        for player, computer, outcome in expected:
            with self.subTest(player=player, computer=computer):
                self.assertEqual(determine_outcome(player, computer), outcome)

    def test_untyped_moves_are_rejected(self):
        with self.assertRaises(TypeError):
            determine_outcome("rock", Move.SCISSORS)


class MatchTests(unittest.TestCase):
    def test_each_match_format_ends_at_its_win_target(self):
        for best_of, target in ((3, 2), (5, 3), (7, 4)):
            with self.subTest(best_of=best_of):
                match = Match(best_of)
                for _ in range(target - 1):
                    match.play(Move.ROCK, Move.SCISSORS)
                    self.assertFalse(match.finished)
                match.play(Move.ROCK, Move.SCISSORS)
                self.assertTrue(match.finished)
                self.assertEqual(match.outcome, Outcome.WIN)
                self.assertEqual(match.wins, target)

    def test_draws_do_not_advance_target_and_explanations_are_correct(self):
        match = Match()
        for _ in range(5):
            match.play(Move.PAPER, Move.PAPER)
        result = match.play(Move.PAPER, Move.ROCK)
        self.assertEqual(result.explanation, "Paper covers rock.")
        self.assertEqual((match.wins, match.losses, match.draws), (1, 0, 5))
        self.assertFalse(match.finished)
        self.assertEqual(match.rounds[-1].number, 6)

    def test_computer_can_win_and_finished_matches_reject_play(self):
        match = Match()
        match.play(Move.SCISSORS, Move.ROCK)
        match.play(Move.SCISSORS, Move.ROCK)
        self.assertEqual(match.outcome, Outcome.LOSS)
        with self.assertRaises(ValueError):
            match.play(Move.ROCK, Move.SCISSORS)
        with self.assertRaises(ValueError):
            match.finish()

    def test_ending_incomplete_match_marks_it_abandoned(self):
        match = Match()
        match.play(Move.ROCK, Move.SCISSORS)
        match.finish()
        self.assertEqual(match.outcome, Outcome.ABANDONED)

    def test_free_play_ends_only_on_request(self):
        match = Match(None)
        for _ in range(10):
            match.play(Move.ROCK, Move.SCISSORS)
        self.assertFalse(match.finished)
        match.finish()
        self.assertEqual(match.outcome, Outcome.WIN)

    def test_free_play_can_finish_in_draw(self):
        match = Match(None)
        match.play(Move.PAPER, Move.PAPER)
        match.finish()
        self.assertEqual(match.outcome, Outcome.DRAW)

    def test_invalid_formats_do_not_create_matches(self):
        for value in (True, 0, 2, 4, 9, "3", 3.0, []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Match(value)

    def test_invalid_move_does_not_change_match(self):
        match = Match()
        with self.assertRaises(TypeError):
            match.play("rock", Move.ROCK)
        self.assertEqual(match.rounds, ())
        self.assertIsNone(match.outcome)
