import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from converter import ExchangeRate

APP = Path(__file__).resolve().parents[1] / "app.py"


class AppTests(unittest.TestCase):
    def test_initial_page_needs_no_network(self):
        with patch("converter.get_exchange_rate") as fetch:
            app = AppTest.from_file(str(APP)).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.title[0].value, "Currency Converter")
            self.assertEqual(app.selectbox[0].value, "EUR")
            self.assertEqual(app.selectbox[1].value, "USD")
            fetch.assert_not_called()

    def test_convert_and_clear_old_result_on_invalid_amount(self):
        with patch(
            "converter.get_exchange_rate",
            return_value=ExchangeRate("EUR", "USD", Decimal("1.12"), "2026-01-02"),
        ):
            app = AppTest.from_file(str(APP)).run()
            app.text_input[0].set_value("25")
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.subheader[0].value, "28.00 USD")
            app.text_input[0].set_value("NaN")
            app.button[0].click().run()
            self.assertTrue(app.error)
            self.assertFalse(app.subheader)
            self.assertFalse(app.exception)

    def test_same_currency(self):
        app = AppTest.from_file(str(APP)).run()
        app.selectbox[1].set_value("EUR")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.subheader[0].value, "100.00 EUR")
        self.assertTrue(any("No rate lookup" in item.value for item in app.caption))

    def test_service_error_is_shown_without_traceback(self):
        # Use a different pair so the success test's cached value cannot be reused.
        with patch(
            "converter.get_exchange_rate",
            side_effect=RuntimeError("Service unavailable"),
        ):
            app = AppTest.from_file(str(APP)).run()
            app.selectbox[0].set_value("GBP")
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.error[0].value, "Service unavailable")
            self.assertFalse(app.subheader)


if __name__ == "__main__":
    unittest.main()
