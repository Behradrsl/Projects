import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

import requests

from converter import ExchangeRate, convert_amount, get_exchange_rate, parse_amount


class ConverterTests(unittest.TestCase):
    def test_amount_validation(self):
        self.assertEqual(parse_amount(" 12.50 "), Decimal("12.50"))
        self.assertEqual(parse_amount("0"), Decimal("0"))
        for value in ("", "-1", "NaN", "Infinity", "1,000", "abc", "1e16", "1e-999999"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_amount(value)

    def test_rounding_and_zero_decimal_currencies(self):
        rate = ExchangeRate("EUR", "USD", Decimal("1.12345"), "2026-01-02")
        self.assertEqual(convert_amount(Decimal("100"), rate), Decimal("112.35"))
        rate = ExchangeRate("EUR", "JPY", Decimal("160.255"), "2026-01-02")
        self.assertEqual(convert_amount(Decimal("1"), rate), Decimal("160"))
        self.assertEqual(convert_amount(Decimal("0"), rate), Decimal("0"))

    def test_large_amount_and_rate_still_round(self):
        rate = ExchangeRate("EUR", "USD", Decimal("1e12"), "2026-01-02")
        self.assertEqual(convert_amount(Decimal("1e15"), rate), Decimal("1e27"))

    @patch("converter.requests.get")
    def test_same_currency_does_not_use_network(self, request):
        rate = get_exchange_rate("eur", "EUR")
        self.assertEqual(rate.value, Decimal("1"))
        self.assertIsNone(rate.date)
        request.assert_not_called()

    @patch("converter.requests.get")
    def test_fetch_validates_pair_date_and_rate(self, request):
        request.return_value = Mock()
        valid = {"base": "EUR", "quote": "USD", "date": "2026-01-02", "rate": 1.12}
        request.return_value.json.return_value = valid
        rate = get_exchange_rate("eur", "usd")
        self.assertEqual(rate.value, Decimal("1.12"))
        request.assert_called_with(
            "https://api.frankfurter.dev/v2/rate/EUR/USD", timeout=15
        )
        for data in [
            {},
            [],
            {**valid, "rate": "NaN"},
            {**valid, "rate": 0},
            {**valid, "base": "GBP"},
            {**valid, "date": "wrong"},
        ]:
            request.return_value.json.return_value = data
            with (
                self.subTest(data=data),
                self.assertRaisesRegex(RuntimeError, "unexpected"),
            ):
                get_exchange_rate("EUR", "USD")

    @patch("converter.requests.get", side_effect=requests.Timeout("Timeout"))
    def test_network_failure_is_readable(self, request):
        with self.assertRaisesRegex(RuntimeError, "Check your connection"):
            get_exchange_rate("EUR", "USD")
        with self.assertRaises(ValueError):
            get_exchange_rate("XXX", "USD")

    @patch("converter.requests.get")
    def test_bad_json_and_http_failure(self, request):
        request.return_value.json.side_effect = ValueError("Not JSON")
        with self.assertRaises(RuntimeError):
            get_exchange_rate("EUR", "USD")
        request.return_value.raise_for_status.side_effect = requests.HTTPError("503")
        with self.assertRaisesRegex(RuntimeError, "Could not reach"):
            get_exchange_rate("EUR", "USD")


if __name__ == "__main__":
    unittest.main()
