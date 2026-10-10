"""Sort a list and compare the time taken by three algorithms."""

import argparse
import random
from statistics import median
from time import perf_counter

from sorting import ALGORITHMS


def parse_numbers(text):
    try:
        numbers = [int(value) for value in text.replace(",", " ").split()]
    except ValueError as error:
        raise ValueError(
            "Enter whole numbers separated by spaces or commas."
        ) from error
    if not numbers:
        raise ValueError("Enter at least one number.")
    if len(numbers) > 2000:
        raise ValueError("Use at most 2,000 numbers for these quadratic algorithms.")
    return numbers


def compare(numbers, algorithm="all"):
    selected = ALGORITHMS if algorithm == "all" else {algorithm: ALGORITHMS[algorithm]}
    print(f"\nInput:  {numbers}")
    for name, function in selected.items():
        timings = []
        for _ in range(5):
            start = perf_counter()
            result = function(numbers)
            timings.append((perf_counter() - start) * 1000)
        print(f"{name.title():10} {median(timings):9.3f} ms   {result}")
    print("Times are medians of 5 runs; small differences are normal.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Sort numbers and compare three algorithms."
    )
    parser.add_argument(
        "numbers", nargs="*", help="Whole numbers, separated by spaces."
    )
    parser.add_argument("--algorithm", choices=["all", *ALGORITHMS], default="all")
    parser.add_argument(
        "--random", type=int, metavar="COUNT", help="Generate 1–2000 numbers."
    )
    parser.add_argument(
        "--seed", type=int, help="Repeat the same randomly generated input."
    )
    args = parser.parse_args(argv)
    if args.numbers and args.random is not None:
        parser.error("Use explicit numbers or --random, not both.")
    if args.seed is not None and args.random is None:
        parser.error("--seed needs --random.")
    try:
        if args.random is not None:
            if not 1 <= args.random <= 2000:
                parser.error("--random must be between 1 and 2000.")
            rng = random.Random(args.seed)
            numbers = [rng.randint(-999, 999) for _ in range(args.random)]
        else:
            text = " ".join(args.numbers)
            if not text:
                print("Sorting Algorithms\nEnter whole numbers, or q to quit.")
                text = input("Numbers (for example 8, 3, -1, 3): ").strip()
                if text.lower() == "q":
                    return 0
            numbers = parse_numbers(text)
        compare(numbers, args.algorithm)
        return 0
    except ValueError as error:
        print(error)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
