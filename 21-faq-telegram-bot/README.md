# FAQ Telegram Bot

Answer questions from a configurable FAQ. Try it in the terminal, connect it to Telegram, and optionally use an LLM to phrase answers from retrieved facts.

## Run it

Requires **Python 3.10 or newer**.

```bash
cd 21-faq-telegram-bot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows, activate with `.venv\Scripts\activate` instead. The launcher uses this project’s `.venv` when it exists.

In VS Code, open **main.py** and choose **Run Python File in Terminal**. Use `Ctrl+C` to exit.

## Try it locally

`python main.py` opens a terminal conversation without a bot token or API key. Ask `What is your return policy?` to receive the example shop’s 30-day return answer. Enter `q` to exit.

Edit `faq.json` before using the bot for a real service. Each record has a `question`, an `answer`, and optional `keywords`. The included business, hours, policies, and support address are examples.

## Connect Telegram

Create your own bot through Telegram’s BotFather, copy `.env.example` to `.env`, and set `TELEGRAM_BOT_TOKEN`. Then run:

```bash
python main.py --telegram
```

The bot responds to `/start`, `/help`, and text questions while this process is running. It polls Telegram for messages and replies to incoming questions. Anyone able to contact the bot can ask it questions. It does not initiate broadcasts, store conversation history, or create a hosted service. Stop with `Ctrl+C`.

## Optional LLM answers

Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in `.env`:

```bash
python main.py --ai
python main.py --telegram --ai
```

Without `--ai`, the best matching FAQ answer is returned directly. With `--ai`, matching records and the question are sent to OpenAI for a grounded plain-text answer. API calls may incur charges. Unknown questions fall back to a support message without an API call. `.env` is excluded from Git.

## How it works

`faq.py` validates FAQ records, ranks matches by shared words and keywords, and optionally calls the Responses API with only matching records. `telegram_bot.py` registers command and message handlers using python-telegram-bot. `main.py` selects local or Telegram mode and checks configuration before connecting.

Questions are limited to 500 characters and the FAQ to 200 entries. Matching is deliberately simple: improve the supplied keywords for your service. An LLM can still make mistakes, so keep the facts clear and test important questions.

Tests exercise local matching, the real OpenAI SDK with a mocked transport, and the actual Telegram reply callback with a mocked message. They do not connect to Telegram or send real messages.

References: [Telegram bot example](https://docs.python-telegram-bot.org/en/stable/examples.echobot.html), [OpenAI text generation](https://developers.openai.com/api/docs/guides/text).

## Checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

GitHub Actions runs the tests and style checks on Python 3.10 and 3.13.
