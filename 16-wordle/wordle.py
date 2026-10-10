"""Wordle rules with exact duplicate-letter accounting."""

from collections import Counter
from pathlib import Path


def load_words(path: Path) -> list[str]:
    words = sorted(
        set(
            word.strip().lower()
            for word in path.read_text().splitlines()
            if word.strip()
        )
    )
    if not words or any(
        len(word) != 5 or not word.isascii() or not word.isalpha() for word in words
    ):
        raise ValueError(
            "The words file must contain five-letter English words, one per line."
        )
    return words


def feedback(guess: str, answer: str) -> tuple[str, ...]:
    if any(
        len(word) != 5 or not word.isascii() or not word.isalpha()
        for word in (guess, answer)
    ):
        raise ValueError("Use five English letters.")
    guess, answer = guess.lower(), answer.lower()
    result = ["absent"] * 5
    remaining = Counter()
    for index, (letter, correct) in enumerate(zip(guess, answer)):
        if letter == correct:
            result[index] = "correct"
        else:
            remaining[correct] += 1
    for index, letter in enumerate(guess):
        if result[index] != "correct" and remaining[letter]:
            result[index] = "present"
            remaining[letter] -= 1
    return tuple(result)


class Wordle:
    def __init__(self, answer: str, words: list[str]):
        if answer not in words:
            raise ValueError("The answer must be in the word list.")
        self.answer = answer
        self.words = set(words)
        self.guesses = []

    @property
    def won(self):
        return bool(self.guesses and self.guesses[-1][0] == self.answer)

    @property
    def finished(self):
        return self.won or len(self.guesses) >= 6

    def guess(self, word: str):
        word = word.strip().lower()
        if self.finished:
            raise ValueError("The round has finished.")
        if word not in self.words:
            raise ValueError(
                "Choose a five-letter word from the word list. Type ? for a hint."
            )
        if any(previous == word for previous, _ in self.guesses):
            raise ValueError("You already tried that word. Choose another.")
        result = feedback(word, self.answer)
        self.guesses.append((word, result))
        return result

    def candidates(self):
        return sorted(
            word
            for word in self.words
            if all(feedback(guess, word) == result for guess, result in self.guesses)
        )
