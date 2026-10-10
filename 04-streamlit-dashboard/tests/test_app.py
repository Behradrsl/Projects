"""Run the actual Streamlit app and interact with its widgets."""

import string
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(APP), default_timeout=15).run()
        self.assertFalse(self.app.exception)

    def test_result_requires_generate_button(self):
        self.assertFalse(self.app.code)
        self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.code[0].value), 16)

    def test_random_options_are_respected(self):
        self.app.slider[0].set_value(20)
        self.app.checkbox[0].uncheck()
        self.app.checkbox[1].uncheck()
        self.app.button[0].click().run()
        value = self.app.code[0].value
        self.assertEqual(len(value), 20)
        self.assertTrue(set(value) <= set(string.ascii_letters))
        self.assertFalse(self.app.exception)

    def test_memorable_custom_words_and_separator(self):
        self.app.radio[0].set_value("Memorable password").run()
        self.app.slider[0].set_value(3)
        self.app.text_input[0].set_value(".")
        self.app.checkbox[0].check()
        self.app.text_area[0].set_value("river, cloud\nforest stone")
        self.app.button[0].click().run()
        words = self.app.code[0].value.split(".")
        self.assertEqual(len(words), 3)
        self.assertTrue(set(words) <= {"River", "Cloud", "Forest", "Stone"})
        self.assertFalse(self.app.exception)

    def test_memorable_default_vocabulary_and_empty_separator(self):
        self.app.radio[0].set_value("Memorable password").run()
        self.app.text_input[0].set_value("")
        self.app.button[0].click().run()
        self.assertTrue(self.app.code[0].value.isalpha())
        self.assertFalse(self.app.exception)

    def test_invalid_vocabulary_shows_error_instead_of_traceback(self):
        self.app.radio[0].set_value("Memorable password").run()
        self.app.text_area[0].set_value("river, 123")
        self.app.button[0].click().run()
        self.assertTrue(self.app.error)
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.code)

    def test_pin_and_changing_type(self):
        self.app.radio[0].set_value("PIN code").run()
        self.app.slider[0].set_value(4)
        self.app.button[0].click().run()
        self.assertEqual(len(self.app.code[0].value), 4)
        self.assertTrue(self.app.code[0].value.isdigit())
        self.app.radio[0].set_value("Random password").run()
        self.assertFalse(self.app.code)
        self.assertFalse(self.app.exception)


if __name__ == "__main__":
    unittest.main()
