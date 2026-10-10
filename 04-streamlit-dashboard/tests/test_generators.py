"""Check generator rules without relying on particular random results."""

import string
import unittest
from unittest.mock import Mock, patch

from password_generators import (
    MemorablePasswordGenerator,
    PasswordGenerator,
    PinCodeGenerator,
    RandomPasswordGenerator,
)


class GeneratorTests(unittest.TestCase):
    def test_base_class_cannot_be_used_directly(self):
        with self.assertRaises(TypeError):
            PasswordGenerator()

    def test_all_generators_implement_the_base_class(self):
        generators = [
            RandomPasswordGenerator(),
            MemorablePasswordGenerator(vocabulary=["river"]),
            PinCodeGenerator(),
        ]
        for generator in generators:
            self.assertIsInstance(generator, PasswordGenerator)
            self.assertIsInstance(generator.generate(), str)

    def test_random_password_character_options(self):
        for numbers in (True, False):
            for symbols in (True, False):
                with self.subTest(numbers=numbers, symbols=symbols):
                    generator = RandomPasswordGenerator(24, numbers, symbols)
                    password = generator.generate()
                    self.assertEqual(len(password), 24)
                    self.assertTrue(set(password) <= set(generator.characters))
                    self.assertTrue(any(character.islower() for character in password))
                    self.assertTrue(any(character.isupper() for character in password))
                    self.assertEqual(any(character.isdigit() for character in password), numbers)
                    self.assertEqual(
                        any(character in string.punctuation for character in password), symbols
                    )

    def test_random_password_retries_if_a_required_group_is_missing(self):
        with patch(
            "password_generators.secrets.choice",
            side_effect=list("aaaaaaaa" + "aA1!bcde"),
        ):
            self.assertEqual(RandomPasswordGenerator(8).generate(), "aA1!bcde")

    def test_password_length_boundaries(self):
        for length in (8, 128):
            self.assertEqual(len(RandomPasswordGenerator(length).generate()), length)
        for length in (7, 129, True, 12.5, "16"):
            with self.subTest(length=length), self.assertRaises(ValueError):
                RandomPasswordGenerator(length)

    def test_memorable_words_separator_and_capitalization(self):
        vocabulary = ["river", "cloud", "forest"]
        password = MemorablePasswordGenerator(5, ".", True, vocabulary).generate()
        chosen = password.split(".")
        self.assertEqual(len(chosen), 5)
        self.assertTrue(all(word in ["River", "Cloud", "Forest"] for word in chosen))

    def test_memorable_allows_repeated_words_and_empty_separator(self):
        generator = MemorablePasswordGenerator(3, "", vocabulary=["stone"])
        self.assertEqual(generator.generate(), "stonestonestone")

    def test_memorable_invalid_options(self):
        for count in (2, 13, True):
            with self.subTest(count=count), self.assertRaises(ValueError):
                MemorablePasswordGenerator(count, vocabulary=["river"])
        for separator in ("long", "\n", 3):
            with self.subTest(separator=separator), self.assertRaises(ValueError):
                MemorablePasswordGenerator(separator=separator, vocabulary=["river"])
        for vocabulary in ([], "river", ["river", 4], ["bad word"]):
            with self.subTest(vocabulary=vocabulary), self.assertRaises(ValueError):
                MemorablePasswordGenerator(vocabulary=vocabulary)

    def test_missing_nltk_uses_bundled_words(self):
        with patch.dict("sys.modules", {"nltk.corpus": None}):
            generator = MemorablePasswordGenerator()
            self.assertIn("river", generator.vocabulary)
            self.assertEqual(len(generator.generate().split("-")), 4)

    def test_missing_corpus_uses_bundled_words(self):
        corpus = Mock()
        corpus.words.side_effect = LookupError("Corpus unavailable")
        with patch.dict("sys.modules", {"nltk.corpus": Mock(words=corpus)}):
            generator = MemorablePasswordGenerator()
            self.assertIn("river", generator.vocabulary)
            self.assertEqual(len(generator.generate().split("-")), 4)

    def test_nltk_basic_vocabulary_is_filtered_and_deduplicated(self):
        corpus = Mock()
        corpus.words.return_value = ["River", "river", "forest", "a", "café", "two words"]
        with patch.dict("sys.modules", {"nltk.corpus": Mock(words=corpus)}):
            generator = MemorablePasswordGenerator()
            corpus.words.assert_called_once_with("en-basic")
            self.assertEqual(generator.vocabulary, ("forest", "river"))

    def test_pin_is_numeric_and_keeps_leading_zeroes(self):
        with patch("password_generators.secrets.choice", side_effect=list("001234")):
            self.assertEqual(PinCodeGenerator().generate(), "001234")
        for length in (4, 12):
            pin = PinCodeGenerator(length).generate()
            self.assertEqual(len(pin), length)
            self.assertTrue(pin.isascii() and pin.isdigit())

    def test_invalid_pin_lengths(self):
        for length in (3, 13, True, 4.5, "6"):
            with self.subTest(length=length), self.assertRaises(ValueError):
                PinCodeGenerator(length)


if __name__ == "__main__":
    unittest.main()
