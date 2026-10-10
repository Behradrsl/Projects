"""Preview daily notes or send them once or on a daily schedule."""

import argparse
import csv
import smtplib
import time
from pathlib import Path


def main(argv=None):
    from dotenv import load_dotenv

    from emailer import (
        choose_quote,
        load_recipients,
        make_message,
        seconds_until,
        send_messages,
        smtp_settings,
    )

    project = Path(__file__).resolve().parent
    load_dotenv(project / ".env")
    parser = argparse.ArgumentParser(
        description="Preview personalized quote emails; --send enables sending."
    )
    parser.add_argument(
        "--recipients", type=Path, default=project / "recipients.example.csv"
    )
    parser.add_argument("--quotes", type=Path, default=project / "quotes.json")
    parser.add_argument("--send", action="store_true")
    parser.add_argument(
        "--daily", metavar="HH:MM", help="Send daily at this local time while running."
    )
    args = parser.parse_args(argv)
    if args.daily and not args.send:
        parser.error("--daily requires --send.")
    try:
        recipients = load_recipients(args.recipients)
        settings = smtp_settings() if args.send else None
        if args.daily:
            seconds_until(args.daily)
        while True:
            if args.daily:
                delay = seconds_until(args.daily)
                print(
                    f"Waiting until {args.daily} local time. "
                    "Ctrl+C stops the schedule.",
                    flush=True,
                )
                time.sleep(delay)
            quote = choose_quote(args.quotes)
            sender = settings["SMTP_FROM"] if settings else "notes@example.invalid"
            messages = [
                make_message(recipient, quote, sender) for recipient in recipients
            ]
            if settings:
                print(f"Sent {send_messages(messages, settings)} messages.")
            else:
                print("Preview only. No email has been sent.\n")
                for message in messages:
                    print(message.as_string())
            if not args.daily:
                return 0
    except (
        OSError,
        ValueError,
        RuntimeError,
        csv.Error,
        smtplib.SMTPException,
    ) as error:
        print(f"Could not prepare or send notes: {error}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    import os
    import sys

    project = Path(__file__).resolve().parent
    environment = project / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if python.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        os.execv(
            str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]]
        )
    raise SystemExit(main())
