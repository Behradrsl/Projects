"""Check a number interactively, or run: python main.py 19."""

import argparse

from happy_numbers import happy_sequence


def show_result(number: int) -> None:
    sequence = happy_sequence(number)
    print(f"\nChecking {number}")
    for current, following in zip(sequence, sequence[1:], strict=False):
        expression = " + ".join(f"{digit}²" for digit in str(current))
        print(f"{expression} = {following}")
    if sequence[-1] == 1:
        print(f"{number} is a happy number: the sequence reaches 1.")
    else:
        print(f"{number} is not a happy number: {sequence[-1]} repeats, so the sequence cycles.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check whether a positive integer is happy.")
    parser.add_argument("number", type=int, nargs="?", help="Number to check (for example, 19)")
    args = parser.parse_args(argv)
    if args.number is not None:
        try:
            show_result(args.number)
        except ValueError as exc:
            parser.error(str(exc))
        return 0

    print("\nHappy Numbers")
    print("A happy number reaches 1 by repeatedly adding the squares of its digits.")
    try:
        while True:
            answer = input("\nEnter a positive whole number, or q to quit: ").strip()
            if answer.lower() == "q":
                break
            try:
                show_result(int(answer))
            except ValueError:
                print("Please enter a positive whole number, such as 19.")
    except (KeyboardInterrupt, EOFError):
        print()
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
