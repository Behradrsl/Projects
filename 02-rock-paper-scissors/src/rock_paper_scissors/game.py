"""Match rules, independent of the browser, database, and random generator."""

from dataclasses import dataclass
from enum import Enum


class Move(str, Enum):
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"


class Outcome(str, Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    ABANDONED = "abandoned"


BEATS = {Move.ROCK: Move.SCISSORS, Move.PAPER: Move.ROCK, Move.SCISSORS: Move.PAPER}


def determine_outcome(player: Move, computer: Move) -> Outcome:
    if not isinstance(player, Move) or not isinstance(computer, Move):
        raise TypeError("Both choices must be Move values.")
    if player == computer:
        return Outcome.DRAW
    return Outcome.WIN if BEATS[player] == computer else Outcome.LOSS


@dataclass(frozen=True)
class Round:
    number: int
    player: Move
    computer: Move
    outcome: Outcome

    @property
    def explanation(self) -> str:
        if self.outcome == Outcome.DRAW:
            return "Same move. Great minds think alike."
        winner, loser = (
            (self.player, self.computer)
            if self.outcome == Outcome.WIN
            else (self.computer, self.player)
        )
        verb = {Move.ROCK: "crushes", Move.PAPER: "covers", Move.SCISSORS: "cuts"}[winner]
        return f"{winner.value.title()} {verb} {loser.value}."


class Match:
    """A first-to-majority match, or an open-ended free-play session.

    Draws count as played rounds but never advance the win target. Both moves
    are supplied by the caller, making the engine straightforward to test.
    """

    def __init__(self, best_of: int | None = 3):
        if best_of is not None and (type(best_of) is not int or best_of not in (3, 5, 7)):
            raise ValueError("Choose best of 3, 5, 7, or free play.")
        self.best_of = best_of
        self._rounds: list[Round] = []
        self._finished = False
        self._abandoned = False

    @property
    def rounds(self) -> tuple[Round, ...]:
        return tuple(self._rounds)

    @property
    def wins(self) -> int:
        return sum(r.outcome == Outcome.WIN for r in self._rounds)

    @property
    def losses(self) -> int:
        return sum(r.outcome == Outcome.LOSS for r in self._rounds)

    @property
    def draws(self) -> int:
        return len(self._rounds) - self.wins - self.losses

    @property
    def target(self) -> int | None:
        return self.best_of // 2 + 1 if self.best_of is not None else None

    @property
    def finished(self) -> bool:
        return self._finished

    @property
    def outcome(self) -> Outcome | None:
        if not self.finished:
            return None
        if self._abandoned:
            return Outcome.ABANDONED
        if self.wins == self.losses:
            return Outcome.DRAW
        return Outcome.WIN if self.wins > self.losses else Outcome.LOSS

    def play(self, player: Move, computer: Move) -> Round:
        if self.finished:
            raise ValueError("This match has ended. Start a new match to play again.")
        result = Round(len(self._rounds) + 1, player, computer, determine_outcome(player, computer))
        self._rounds.append(result)
        if self.target is not None and max(self.wins, self.losses) >= self.target:
            self._finished = True
        return result

    def finish(self) -> None:
        if self.finished:
            raise ValueError("This match has already ended.")
        self._finished = True
        self._abandoned = self.best_of is not None
