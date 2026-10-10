import asyncio
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx2 as httpx
from openai import OpenAI

from faq import FALLBACK, answer_question, load_faq
from telegram_bot import build_application


def fake_client(text, annotations=None, status=200):
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        if status != 200:
            return httpx.Response(
                status,
                json={
                    "error": {"message": "Test failure", "type": "authentication_error"}
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "gpt-4.1-mini",
                "output": [
                    {
                        "type": "message",
                        "id": "msg_test",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": text,
                                "annotations": annotations or [],
                            }
                        ],
                    }
                ],
            },
        )

    client = OpenAI(
        api_key="test-placeholder",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=0,
    )
    return client, captured


ROOT = Path(__file__).resolve().parents[1]


class FAQTests(unittest.TestCase):
    def test_local_answers_and_unknown_questions(self):
        records = load_faq(ROOT / "faq.json")
        self.assertIn(
            "30 days", answer_question("What is your return policy?", records)
        )
        self.assertIn("9:00", answer_question("When are you open?", records))
        self.assertEqual(
            answer_question("Explain quantum mechanics", records), FALLBACK
        )
        with self.assertRaises(ValueError):
            answer_question("", records)

    def test_sdk_receives_relevant_faq_records_only(self):
        records = load_faq(ROOT / "faq.json")
        client, captured = fake_client(
            ("Unused items may be returned within 30 days with a receipt.")
        )
        with client:
            result = answer_question("return policy", records, True, client)
        self.assertIn("30 days", result)
        context = json.loads(captured[0]["input"])
        self.assertEqual(context["faq"][0]["question"], "What is the return policy?")
        self.assertFalse(captured[0]["store"])

    def test_telegram_handler_replies_without_network(self):
        records = load_faq(ROOT / "faq.json")
        application = build_application("123456:TestPlaceholderToken", records)
        self.assertEqual(len(application.handlers[0]), 3)
        message = SimpleNamespace(text="return policy", reply_text=AsyncMock())
        update = SimpleNamespace(effective_message=message)
        asyncio.run(application.handlers[0][2].callback(update, None))
        message.reply_text.assert_awaited_once()
        self.assertIn("30 days", message.reply_text.call_args.args[0])

    def test_bad_faq_and_local_cli_from_another_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            invalid = Path(folder) / "faq.json"
            invalid.write_text('[{"question":"Only a question"}]')
            with self.assertRaises(ValueError):
                load_faq(invalid)
            result = subprocess.run(
                [sys.executable, str(ROOT / "main.py")],
                cwd=folder,
                input="return policy\nq\n",
                text=True,
                capture_output=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("30 days", result.stdout)


if __name__ == "__main__":
    unittest.main()
