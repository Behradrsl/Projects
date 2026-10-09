"""Game rules. This module performs no terminal or filesystem operations."""

import random
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Difficulty:
    name: str
    upper: int
    attempts: int
    penalty: int


DIFFICULTIES = {
    "easy": Difficulty("easy", 50, 8, 10),
    "normal": Difficulty("normal", 100, 7, 15),
    "hard": Difficulty("hard", 1000, 10, 10),
}


class Status(str, Enum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"
    QUIT = "quit"


@dataclass(frozen=True)
class GuessResult:
    number: int
    direction: str
    status: Status
    attempts_left: int
    score: int


class Game:
    """One round; only distinct, valid guesses consume attempts.

    A supplied secret makes tests deterministic. Production rounds use randint,
    which includes both ends of the interval.
    """

    def __init__(self, difficulty: Difficulty, *, secret: int | None = None):
        if difficulty.upper < 2 or difficulty.attempts < 1 or difficulty.penalty < 0:
            raise ValueError("Invalid difficulty configuration.")
        self.difficulty = difficulty
        self._secret = random.randint(1, difficulty.upper) if secret is None else secret
        if type(self._secret) is not int or not 1 <= self._secret <= difficulty.upper:
            raise ValueError("Secret must be an integer within the game's range.")
        self.status = Status.PLAYING
        self.guesses: list[int] = []
        self.lower_bound = 1
        self.upper_bound = difficulty.upper
        self._mistakes = 0

    @property
    def attempts_left(self) -> int:
        return self.difficulty.attempts - len(self.guesses)

    @property
    def score(self) -> int:
        if self.status in (Status.LOST, Status.QUIT):
            return 0
        return max(0, 100 - self._mistakes * self.difficulty.penalty)

    @property
    def answer(self) -> int:
        if self.status == Status.PLAYING:
            raise RuntimeError("The answer is hidden until the round ends.")
        return self._secret

    def guess(self, number: int) -> GuessResult:
        if self.status != Status.PLAYING:
            raise RuntimeError("This round has already ended.")
        if type(number) is not int or not 1 <= number <= self.difficulty.upper:
            raise ValueError(f"Enter a whole number from 1 to {self.difficulty.upper}.")
        if number in self.guesses:
            raise ValueError("You already tried that number. Choose a different one.")
        self.guesses.append(number)
        if number == self._secret:
            self.status = Status.WON
            direction = "correct"
        else:
            self._mistakes += 1
            direction = "higher" if number < self._secret else "lower"
            if direction == "higher":
                self.lower_bound = max(self.lower_bound, number + 1)
            else:
                self.upper_bound = min(self.upper_bound, number - 1)
            if self.attempts_left == 0:
                self.status = Status.LOST
        return GuessResult(number, direction, self.status, self.attempts_left, self.score)

    def quit(self) -> None:
        if self.status != Status.PLAYING:
            raise RuntimeError("This round has already ended.")
        self.status = Status.QUIT
