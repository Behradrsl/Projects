"""Fetch a dated exchange rate and convert amounts with Decimal arithmetic."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

import requests

CURRENCIES = {
    "AUD": "Australian dollar",
    "BRL": "Brazilian real",
    "CAD": "Canadian dollar",
    "CHF": "Swiss franc",
    "CNY": "Chinese yuan",
    "DKK": "Danish krone",
    "EUR": "Euro",
    "GBP": "British pound",
    "HKD": "Hong Kong dollar",
    "INR": "Indian rupee",
    "JPY": "Japanese yen",
    "KRW": "South Korean won",
    "MXN": "Mexican peso",
    "NOK": "Norwegian krone",
    "NZD": "New Zealand dollar",
    "PLN": "Polish zloty",
    "SEK": "Swedish krona",
    "SGD": "Singapore dollar",
    "USD": "US dollar",
    "ZAR": "South African rand",
}


@dataclass(frozen=True)
class ExchangeRate:
    base: str
    target: str
    value: Decimal
    date: str | None


def parse_amount(text: str) -> Decimal:
    try:
        amount = Decimal(text.strip())
    except (InvalidOperation, ValueError) as error:
        raise ValueError(
            "Enter an amount such as 100 or 12.50, without commas."
        ) from error
    if not amount.is_finite() or amount < 0 or amount > Decimal("1e15"):
        raise ValueError("Enter an amount from 0 to 1,000,000,000,000,000.")
    # Avoid extreme exponents while allowing zero and ordinary decimal input.
    if amount and amount.adjusted() < -12:
        raise ValueError("Use no more than 12 decimal places for very small amounts.")
    return amount


def get_exchange_rate(base: str, target: str) -> ExchangeRate:
    base, target = base.upper(), target.upper()
    if base not in CURRENCIES or target not in CURRENCIES:
        raise ValueError("Choose currencies from the supported list.")
    if base == target:
        return ExchangeRate(base, target, Decimal("1"), None)
    try:
        response = requests.get(
            f"https://api.frankfurter.dev/v2/rate/{base}/{target}", timeout=15
        )
        response.raise_for_status()
        data = response.json()
        value = Decimal(str(data["rate"]))
        rate_date = data["date"]
        date.fromisoformat(rate_date)
        if data["base"] != base or data["quote"] != target:
            raise ValueError("The service returned a different currency pair.")
        if not value.is_finite() or value <= 0 or value > Decimal("1e12"):
            raise ValueError("Invalid rate.")
        return ExchangeRate(base, target, value, rate_date)
    except requests.RequestException as error:
        raise RuntimeError(
            "Could not reach the rate service. Check your connection and try again."
        ) from error
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        raise RuntimeError(
            "The rate service returned an unexpected response. Try again later."
        ) from error


def convert_amount(amount: Decimal, rate: ExchangeRate) -> Decimal:
    amount = parse_amount(str(amount))
    places = Decimal("1") if rate.target in ("JPY", "KRW") else Decimal("0.01")
    with localcontext() as context:
        context.prec = 40
        return (amount * rate.value).quantize(places, rounding=ROUND_HALF_UP)
