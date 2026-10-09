"""A small terminal menu for the three password generators."""

from .generators import MemorablePasswordGenerator, PinCodeGenerator, RandomPasswordGenerator


def ask_number(prompt: str, default: int, minimum: int, maximum: int) -> int:
    while True:
        answer = input(f"{prompt} [{default}]: ").strip()
        if not answer:
            return default
        try:
            value = int(answer)
            if minimum <= value <= maximum:
                return value
        except ValueError:
            pass
        print(f"Please enter a whole number between {minimum} and {maximum}.")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{prompt} [{hint}]: ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter yes or no.")


def main() -> int:
    print("\nPassword Generator")
    print("Choose a type. Press Enter at a prompt to use its default.")
    try:
        while True:
            print("\n1. Random password\n2. Memorable password\n3. PIN code\n0. Exit")
            choice = input("Your choice: ").strip()
            if choice == "0":
                break
            try:
                if choice == "1":
                    length = ask_number("Password length", 16, 8, 128)
                    numbers = ask_yes_no("Include numbers?")
                    symbols = ask_yes_no("Include symbols?")
                    generator = RandomPasswordGenerator(length, numbers, symbols)
                elif choice == "2":
                    count = ask_number("Number of words", 4, 3, 12)
                    separator = input("Separator [hyphen]: ") or "-"
                    capitalize = ask_yes_no("Capitalize each word?", default=False)
                    generator = MemorablePasswordGenerator(count, separator, capitalize)
                elif choice == "3":
                    generator = PinCodeGenerator(ask_number("PIN length", 6, 4, 12))
                else:
                    print("Please choose 1, 2, 3, or 0.")
                    continue
                print(f"\nGenerated password: {generator.generate()}")
            except ValueError as exc:
                print(f"\n{exc}")
    except (KeyboardInterrupt, EOFError):
        print()
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
