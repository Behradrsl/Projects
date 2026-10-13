import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


class AppTests(unittest.TestCase):
    def test_interaction(self):
        at = AppTest.from_file(str(APP)).run()
        self.assertFalse(at.exception)
        at.selectbox[0].set_value("C-NAV").run()
        self.assertFalse(at.exception)
        self.assertIn("C-CAM", at.dataframe[1].value.iloc[0, 1])
        at.text_area[0].set_value("{}").run()
        self.assertFalse(at.exception)
        self.assertTrue(at.error)
