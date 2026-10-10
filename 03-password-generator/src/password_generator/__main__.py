"""Run the terminal menu directly, or with python -m password_generator."""

if __package__:
    from .generators import MemorablePasswordGenerator, PinCodeGenerator, RandomPasswordGenerator
else:
    from generators import MemorablePasswordGenerator, PinCodeGenerator, RandomPasswordGenerator


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


def ask_separator() -> str:
    while True:
        answer = input("Separator [-], or type none for no separator: ")
        if answer.lower() == "none":
            return ""
        if len(answer) <= 3 and all(character.isprintable() for character in answer):
            return answer or "-"
        print("Use up to 3 printable characters, such as - or a space.")


def show_passwords(generator, label: str) -> bool:
    """Return True to go back to the menu, or False to quit."""
    while True:
        print(f"\n{label}: {generator.generate()}\n")
        while True:
            action = input("Enter = generate another | m = menu | q = quit: ").strip().lower()
            if action == "":
                break
            if action == "m":
                return True
            if action in ("q", "0"):
                return False
            print("Press Enter, m, or q.")


def main() -> int:
    print("\nPassword Generator")
    print("Choose a type. Press Enter at a prompt to use its default.")
    try:
        while True:
            print("\n1. Random password\n2. Memorable password\n3. PIN code\n0. Exit")
            choice = input("Your choice: ").strip()
            if choice in ("0", "q"):
                break
            if choice == "1":
                length = ask_number("Password length (8–128)", 16, 8, 128)
                numbers = ask_yes_no("Include numbers?")
                symbols = ask_yes_no("Include symbols?")
                generator = RandomPasswordGenerator(length, numbers, symbols)
                label = "Your password"
            elif choice == "2":
                count = ask_number("Number of words (3–12)", 4, 3, 12)
                separator = ask_separator()
                capitalize = ask_yes_no("Capitalize each word?", default=False)
                generator = MemorablePasswordGenerator(count, separator, capitalize)
                label = "Your memorable password"
            elif choice == "3":
                generator = PinCodeGenerator(ask_number("PIN length (4–12)", 6, 4, 12))
                label = "Your PIN"
            else:
                print("Please choose 1, 2, 3, or 0.")
                continue
            if not show_passwords(generator, label):
                break
    except (KeyboardInterrupt, EOFError):
        print()
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
