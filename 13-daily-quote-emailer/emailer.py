"""Read recipients, prepare personalized messages, and send with STARTTLS."""

import csv
import json
import os
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path


def valid_email(value):
    return (
        "\n" not in value
        and "\r" not in value
        and parseaddr(value)[1] == value
        and value.count("@") == 1
        and all(value.split("@"))
        and not any(c.isspace() for c in value)
    )


def load_recipients(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"name", "email"}.issubset(reader.fieldnames or []):
            raise ValueError("The recipients CSV needs name and email columns.")
        result, seen = [], set()
        for row in reader:
            name, email = (
                (row.get("name") or "").strip(),
                (row.get("email") or "").strip(),
            )
            if not name or not valid_email(email):
                raise ValueError(f"Invalid recipient on CSV line {reader.line_num}.")
            if email.casefold() not in seen:
                result.append({"name": name, "email": email})
                seen.add(email.casefold())
        if not result:
            raise ValueError("Add at least one recipient to the CSV.")
        return result


def choose_quote(path: Path) -> str:
    quotes = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(quotes, list)
        or not quotes
        or any(not isinstance(q, str) or not q.strip() for q in quotes)
    ):
        raise ValueError("The quotes file must be a nonempty JSON list of text.")
    return secrets.choice(quotes)


def make_message(recipient: dict, quote: str, sender: str) -> EmailMessage:
    if not valid_email(sender) or not valid_email(recipient["email"]):
        raise ValueError("Use a plain email address for sender and recipient.")
    message = EmailMessage()
    message["Subject"] = "Your daily note"
    message["From"] = sender
    message["To"] = recipient["email"]
    message.set_content(f"Hi {recipient['name']},\n\n{quote}\n\nHave a good day!\n")
    return message


def smtp_settings() -> dict:
    settings = {
        name: os.getenv(name, "").strip()
        for name in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM")
    }
    settings["SMTP_PASSWORD"] = os.getenv("SMTP_PASSWORD", "")
    settings["SMTP_FROM"] = settings["SMTP_FROM"] or settings["SMTP_USER"]
    if not all(settings.values()):
        raise ValueError(
            "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM in .env."
        )
    try:
        settings["SMTP_PORT"] = int(os.getenv("SMTP_PORT", "587"))
    except ValueError as error:
        raise ValueError(
            "SMTP_PORT must be a number, usually 587 for STARTTLS."
        ) from error
    if not 1 <= settings["SMTP_PORT"] <= 65535:
        raise ValueError("SMTP_PORT must be between 1 and 65535.")
    if not valid_email(settings["SMTP_FROM"]):
        raise ValueError("SMTP_FROM must be a plain email address.")
    return settings


def send_messages(messages: list[EmailMessage], settings: dict) -> int:
    sent = 0
    with smtplib.SMTP(
        settings["SMTP_HOST"], settings["SMTP_PORT"], timeout=20
    ) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(settings["SMTP_USER"], settings["SMTP_PASSWORD"])
        for message in messages:
            try:
                refused = server.send_message(message)
                if refused:
                    raise smtplib.SMTPException("The server refused a recipient.")
                sent += 1
            except smtplib.SMTPException as error:
                raise RuntimeError(
                    f"Stopped after {sent} sent messages. "
                    "Check recipients before retrying."
                ) from error
    return sent


def seconds_until(time_text: str, now: datetime | None = None) -> float:
    try:
        hour, minute = (int(value) for value in time_text.split(":"))
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError
    except ValueError as error:
        raise ValueError("Use a local time in HH:MM format, such as 09:00.") from error
    now = now or datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target.timestamp() - now.timestamp()
