"""Follow the sum-of-squared-digits sequence until it ends or repeats."""


def happy_sequence(number: int) -> list[int]:
    """Return the path, including the final 1 or the first repeated number."""
    if type(number) is not int or number <= 0:
        raise ValueError("Enter a positive whole number.")
    sequence = [number]
    seen = set()
    while number != 1 and number not in seen:
        seen.add(number)
        number = sum(int(digit) ** 2 for digit in str(number))
        sequence.append(number)
    return sequence


def is_happy(number: int) -> bool:
    """A number is happy when its sequence reaches 1."""
    return happy_sequence(number)[-1] == 1
