import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


class AppTests(unittest.TestCase):
    def test_interaction(self):
        at = AppTest.from_file(str(APP)).run()
        self.assertFalse(at.exception)
        at.slider[5].set_value(10.0).run()
        self.assertFalse(at.exception)
        self.assertTrue(at.warning)
