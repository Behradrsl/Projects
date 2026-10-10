"""Monty knows the prize door and always reveals an unchosen goat door."""

import random
from dataclasses import dataclass

DOORS = (1, 2, 3)


@dataclass(frozen=True)
class Round:
    car: int
    initial: int
    revealed: int
    remaining: int

    def won(self, switch: bool) -> bool:
        return (self.remaining if switch else self.initial) == self.car


def create_round(initial_choice: int, rng: random.Random | None = None) -> Round:
    if type(initial_choice) is not int or initial_choice not in DOORS:
        raise ValueError("Choose door 1, 2, or 3.")
    rng = rng if rng is not None else random.Random()
    car = rng.choice(DOORS)
    revealed = rng.choice([door for door in DOORS if door != initial_choice and door != car])
    remaining = next(door for door in DOORS if door != initial_choice and door != revealed)
    return Round(car, initial_choice, revealed, remaining)


def monty_hall_game(switch_doors: bool, rng: random.Random | None = None) -> bool:
    """Simulate one contestant using the selected strategy."""
    rng = rng if rng is not None else random.Random()
    game = create_round(rng.choice(DOORS), rng)
    return game.won(switch_doors)


def simulate_games(num_games: int = 10000, seed: int | None = None) -> tuple[int, int]:
    """Compare both strategies on the same games; return (stay wins, switch wins)."""
    if type(num_games) is not int or not 1 <= num_games <= 1_000_000:
        raise ValueError("Number of games must be between 1 and 1,000,000.")
    if seed is not None and type(seed) is not int:
        raise ValueError("The seed must be a whole number.")
    rng = random.Random(seed)
    stay_wins = 0
    for _ in range(num_games):
        game = create_round(rng.choice(DOORS), rng)
        stay_wins += game.won(switch=False)
    # For the same game, exactly one of the two strategies wins.
    return stay_wins, num_games - stay_wins
