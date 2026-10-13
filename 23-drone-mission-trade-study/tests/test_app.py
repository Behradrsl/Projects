import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


class AppTests(unittest.TestCase):
    def test_interaction(self):
        at = AppTest.from_file(str(APP)).run()
        self.assertFalse(at.exception)
        self.assertIn("Surveyor", at.success[0].value)
        at.slider[0].set_value(45.0).run()
        self.assertFalse(at.exception)
        self.assertTrue(at.warning)
