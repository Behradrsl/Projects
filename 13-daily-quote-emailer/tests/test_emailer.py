import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from emailer import (
    choose_quote,
    load_recipients,
    make_message,
    seconds_until,
    send_messages,
    smtp_settings,
)

ROOT = Path(__file__).resolve().parents[1]


class EmailTests(unittest.TestCase):
    def test_csv_validation_and_deduplication(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "people.csv"
            path.write_text(
                ("name,email\nAlex,alex@example.com\nAlex,alex@example.com\n")
            )
            self.assertEqual(len(load_recipients(path)), 1)
            for text in [
                "name,address\nAlex,x\n",
                "name,email\nAlex,not-email\n",
                "name,email\n",
            ]:
                path.write_text(text)
                with self.assertRaises(ValueError):
                    load_recipients(path)

    def test_message_personalization_and_no_header_injection(self):
        message = make_message(
            {"name": "Alex", "email": "alex@example.com"},
            "One small step.",
            "notes@example.com",
        )
        self.assertIn("Hi Alex", message.get_content())
        self.assertEqual(message["To"], "alex@example.com")
        with self.assertRaises(ValueError):
            make_message(
                {"name": "Alex", "email": "a@b\nBcc: c@d"}, "Quote", "notes@example.com"
            )

    @patch("emailer.smtplib.SMTP")
    def test_smtp_encrypts_before_login_and_sends_separately(self, smtp):
        server = smtp.return_value.__enter__.return_value
        server.send_message.return_value = {}
        settings = {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": 587,
            "SMTP_USER": "u",
            "SMTP_PASSWORD": "p",
        }
        messages = [
            make_message(
                {"name": name, "email": name + "@example.com"},
                "Note",
                "sender@example.com",
            )
            for name in ["alex", "sam"]
        ]
        self.assertEqual(send_messages(messages, settings), 2)
        names = [call[0] for call in server.method_calls]
        self.assertLess(names.index("starttls"), names.index("login"))
        self.assertEqual(server.send_message.call_count, 2)
        server.send_message.side_effect = [{}, {"sam@example.com": (550, b"no")}]
        with self.assertRaisesRegex(RuntimeError, "after 1 sent"):
            send_messages(messages, settings)

    def test_schedule_rolls_over_to_next_day(self):
        self.assertEqual(seconds_until("09:00", datetime(2026, 1, 1, 8)), 3600)
        self.assertEqual(seconds_until("09:00", datetime(2026, 1, 1, 9)), 86400)
        for value in ("25:00", "12:60", "noon", "1:2:3"):
            with self.assertRaises(ValueError):
                seconds_until(value)

    @unittest.skipUnless(
        hasattr(time, "tzset"), "System timezone switching unavailable"
    )
    def test_schedule_accounts_for_daylight_saving(self):
        original = os.environ.get("TZ")
        try:
            os.environ["TZ"] = "Europe/Berlin"
            time.tzset()
            self.assertEqual(seconds_until("09:00", datetime(2026, 10, 24, 9)), 90000)
            self.assertEqual(seconds_until("09:00", datetime(2026, 3, 28, 9)), 82800)
        finally:
            if original is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = original
            time.tzset()

    def test_missing_settings_and_invalid_quotes(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            smtp_settings()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "quotes.json"
            path.write_text("[]")
            with self.assertRaises(ValueError):
                choose_quote(path)
            path.write_text('["Take a step."]')
            self.assertEqual(choose_quote(path), "Take a step.")

    def test_default_launch_only_previews(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, str(ROOT / "main.py")],
                cwd=folder,
                text=True,
                capture_output=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No email has been sent", result.stdout)
        self.assertIn("Hi Alex", result.stdout)


if __name__ == "__main__":
    unittest.main()
