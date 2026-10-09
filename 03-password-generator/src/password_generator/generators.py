"""Password generators based on the course's class-based solution."""

import secrets
import string
from abc import ABC, abstractmethod
from collections.abc import Sequence


class PasswordGenerator(ABC):
    """Each password generator provides its own generate method."""

    @abstractmethod
    def generate(self) -> str:
        pass


class RandomPasswordGenerator(PasswordGenerator):
    """Generate a password containing each selected character type."""

    def __init__(
        self, length: int = 16, include_numbers: bool = True, include_symbols: bool = True
    ):
        if type(length) is not int or not 8 <= length <= 128:
            raise ValueError("Password length must be between 8 and 128.")
        self.length = length
        self.groups = [string.ascii_lowercase, string.ascii_uppercase]
        if include_numbers:
            self.groups.append(string.digits)
        if include_symbols:
            self.groups.append(string.punctuation)
        self.characters = "".join(self.groups)

    def generate(self) -> str:
        while True:
            password = "".join(secrets.choice(self.characters) for _ in range(self.length))
            if all(any(character in group for character in password) for group in self.groups):
                return password


class MemorablePasswordGenerator(PasswordGenerator):
    """Combine randomly chosen words into a memorable password."""

    def __init__(
        self,
        no_of_words: int = 4,
        separator: str = "-",
        capitalization: bool = False,
        vocabulary: Sequence[str] | None = None,
    ):
        if type(no_of_words) is not int or not 3 <= no_of_words <= 12:
            raise ValueError("Word count must be between 3 and 12.")
        if not isinstance(separator, str) or len(separator) > 3:
            raise ValueError("Use a separator with up to 3 characters.")
        if any(not character.isprintable() for character in separator):
            raise ValueError("The separator must contain printable characters.")
        if vocabulary is None:
            from nltk.corpus import words

            try:
                vocabulary = words.words()
            except LookupError as exc:
                raise ValueError(
                    "Install the word list first: python -m nltk.downloader words"
                ) from exc
            vocabulary = sorted(
                {
                    word.lower()
                    for word in vocabulary
                    if word.isascii() and word.isalpha() and 4 <= len(word) <= 8
                }
            )
        if isinstance(vocabulary, str | bytes) or not vocabulary:
            raise ValueError("The vocabulary must be a nonempty sequence of words.")
        if any(not isinstance(word, str) or not word.isalpha() for word in vocabulary):
            raise ValueError("The vocabulary must contain alphabetic words.")
        self.vocabulary = tuple(vocabulary)
        self.no_of_words = no_of_words
        self.separator = separator
        self.capitalization = capitalization

    def generate(self) -> str:
        chosen = [secrets.choice(self.vocabulary) for _ in range(self.no_of_words)]
        if self.capitalization:
            chosen = [word.capitalize() for word in chosen]
        return self.separator.join(chosen)


class PinCodeGenerator(PasswordGenerator):
    """Generate a numeric PIN, keeping any leading zeroes."""

    def __init__(self, length: int = 6):
        if type(length) is not int or not 4 <= length <= 12:
            raise ValueError("PIN length must be between 4 and 12.")
        self.length = length

    def generate(self) -> str:
        return "".join(secrets.choice(string.digits) for _ in range(self.length))
