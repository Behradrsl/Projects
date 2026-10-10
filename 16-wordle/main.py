"""Play six-guess rounds with optional candidate hints."""

import argparse
import random
from pathlib import Path

from wordle import Wordle, load_words


def show_row(word, result):
    return " ".join(
        f"[{letter.upper()}]"
        if mark == "correct"
        else f"({letter.upper()})"
        if mark == "present"
        else f" {letter.upper()} "
        for letter, mark in zip(word, result)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Guess a five-letter word in six attempts."
    )
    parser.add_argument(
        "--words", type=Path, default=Path(__file__).resolve().parent / "words.txt"
    )
    parser.add_argument("--seed", type=int)
    args = parser.parse_args(argv)
    try:
        words = load_words(args.words)
        rng = random.Random(args.seed)
        print("Wordle\n[Letter] = correct spot; (Letter) = wrong spot; plain = absent.")
        print("Type ? for possible answers, or q to quit.")
        while True:
            game = Wordle(rng.choice(words), words)
            while not game.finished:
                guess = input(f"Guess {len(game.guesses) + 1}/6: ").strip().lower()
                if guess == "q":
                    return 0
                if guess == "?":
                    candidates = game.candidates()
                    print(
                        f"{len(candidates)} possible answers: "
                        + ", ".join(candidates[:12])
                    )
                    continue
                try:
                    result = game.guess(guess)
                    print(show_row(guess, result))
                except ValueError as error:
                    print(error)
            print("You got it!" if game.won else f"The word was {game.answer.upper()}.")
            if input("Play again? [y/N]: ").strip().lower() != "y":
                return 0
    except (OSError, ValueError) as error:
        print(error)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
