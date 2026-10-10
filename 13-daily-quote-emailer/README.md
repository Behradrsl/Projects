# Daily Quote Emailer

Prepare personalized daily notes from a local quote list. Preview them without an account, send a batch through SMTP, or keep a daily schedule running.

## Run it

Requires **Python 3.10 or newer**.

```bash
cd 13-daily-quote-emailer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows, activate with `.venv\Scripts\activate` instead. The launcher uses this project’s `.venv` when it exists.

In VS Code, open **main.py** and choose **Run Python File in Terminal**. Use `Ctrl+C` to exit.

## Preview first

Running `python main.py` prints example messages in the terminal. **The default run sends no email.** The supplied addresses use the reserved `example.invalid` domain.

Create a recipients CSV with these columns:

```csv
name,email
Alex,alex@example.com
Sam,sam@example.com
```

Names personalize the greeting, and repeated email addresses are deduplicated. Use addresses belonging to your actual recipients before sending. The app never adds other recipients to a message’s headers.

## Configure sending

Copy `.env.example` to `.env`, then fill in your provider’s SMTP settings:

```text
SMTP_HOST=your-provider-host
SMTP_PORT=587
SMTP_USER=your-login
SMTP_PASSWORD=your-provider-credential
SMTP_FROM=your-sender-address
```

The app uses STARTTLS before authentication. Use a provider credential that supports SMTP; `.env` is excluded from Git.

```bash
python main.py --recipients recipients.csv --send
python main.py --recipients recipients.csv --send --daily 09:00
```

The daily option waits until the next occurrence of that **local system time**, then sends once each day while the process remains running. Closing the terminal, sleeping the computer, or stopping the process interrupts scheduling; there is no background service or catch-up delivery. After an SMTP error, the process stops and reports how many messages were sent, rather than silently retrying the whole batch.

## How it works

`emailer.py` reads and validates CSV records, chooses one note from `quotes.json`, creates individual `EmailMessage` objects, and sends them through an authenticated TLS connection. The included notes are original short messages; replace the JSON list to use your own text.

`main.py` provides preview, one-time sending, and scheduling. Tests verify personalization, CSV validation, TLS-before-login, partial-send failures, and scheduling. SMTP is mocked in tests; no real messages are sent.

## Checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

GitHub Actions runs the tests and style checks on Python 3.10 and 3.13.
