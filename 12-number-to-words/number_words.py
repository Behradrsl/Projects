"""Convert integers of up to twelve digits into English words."""

ONES = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
)
TENS = (
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
)


def number_to_words(number: int) -> str:
    if isinstance(number, bool) or not isinstance(number, int):
        raise ValueError("Enter a whole number.")
    if not -999_999_999_999 <= number <= 999_999_999_999:
        raise ValueError("Use at most 12 digits, excluding the minus sign.")
    if number < 0:
        return "minus " + number_to_words(-number)
    if number < 20:
        return ONES[number]
    if number < 100:
        tens, ones = divmod(number, 10)
        return TENS[tens] + ("-" + ONES[ones] if ones else "")
    for value, label in (
        (10**9, "billion"),
        (10**6, "million"),
        (1000, "thousand"),
        (100, "hundred"),
    ):
        if number >= value:
            leading, rest = divmod(number, value)
            words = number_to_words(leading) + " " + label
            return words + (" " + number_to_words(rest) if rest else "")
    raise AssertionError("Unreachable number.")
