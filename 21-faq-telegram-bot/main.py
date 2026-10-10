"""Try the FAQ locally, or connect it to a Telegram bot."""

import argparse
import os
from pathlib import Path


def main(argv=None):
    from dotenv import load_dotenv

    from faq import answer_question, load_faq

    root = Path(__file__).resolve().parent
    load_dotenv(root / ".env")
    parser = argparse.ArgumentParser(
        description="Answer FAQ questions locally or through Telegram."
    )
    parser.add_argument("--faq", type=Path, default=root / "faq.json")
    parser.add_argument(
        "--telegram", action="store_true", help="Connect using TELEGRAM_BOT_TOKEN."
    )
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Use OpenAI to phrase answers from matching FAQ records.",
    )
    args = parser.parse_args(argv)
    try:
        records = load_faq(args.faq)
        if args.ai and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("Set OPENAI_API_KEY in .env before using --ai.")
        if args.telegram:
            token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
            if not token:
                raise ValueError(
                    (
                        "Set TELEGRAM_BOT_TOKEN in .env, or run without --telegram "
                        "for local mode."
                    )
                )
            from telegram.error import TelegramError

            from telegram_bot import build_application

            try:
                app = build_application(token, records, args.ai)
                print("FAQ bot is running. Ctrl+C stops it.", flush=True)
                app.run_polling(allowed_updates=["message"])
            except TelegramError as error:
                raise RuntimeError(
                    "Telegram could not connect. Check the bot token and network."
                ) from error
            return 0
        print("FAQ Assistant (local mode)\nAsk a question, or q to quit.")
        while True:
            question = input("You: ").strip()
            if question.lower() == "q":
                return 0
            try:
                print("FAQ:", answer_question(question, records, args.ai))
            except (ValueError, RuntimeError) as error:
                print(error)
    except (OSError, ValueError, RuntimeError) as error:
        print(error)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
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
