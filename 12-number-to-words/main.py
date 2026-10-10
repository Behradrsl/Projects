"""Convert a number directly or keep converting in the terminal."""

import argparse

from number_words import number_to_words


def convert(text):
    try:
        number = int(text)
    except ValueError as error:
        raise ValueError(
            "Enter a whole number, without decimal points or commas."
        ) from error
    return number_to_words(number)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert up to 12 digits into English words."
    )
    parser.add_argument("number", nargs="?")
    args = parser.parse_args(argv)
    if args.number is not None:
        try:
            print(convert(args.number))
            return 0
        except ValueError as error:
            print(error)
            return 1
    print("Number to Words\nEnter a whole number, or q to quit.")
    try:
        while True:
            text = input("Number: ").strip()
            if text.lower() == "q":
                return 0
            try:
                print(convert(text))
            except ValueError as error:
                print(error)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
