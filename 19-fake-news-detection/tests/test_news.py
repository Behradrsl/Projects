import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx2 as httpx
from openai import OpenAI
from streamlit.testing.v1 import AppTest

from news_review import evidence_checklist, review_claim


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


class NewsTests(unittest.TestCase):
    def test_manual_report_has_no_truth_classification(self):
        report = evidence_checklist(
            "A specific claim to check.",
            {"Check dates": False, "Read the source": True},
        )
        self.assertIn("Check dates", report)
        self.assertIn("does not classify", report)
        with self.assertRaises(ValueError):
            evidence_checklist("short", {})

    def test_sdk_web_search_and_source_deduplication(self):
        annotation = {
            "type": "url_citation",
            "title": "Primary source",
            "url": "https://example.com/record",
            "start_index": 0,
            "end_index": 8,
        }
        client, captured = fake_client(
            "A sourced assessment.", [annotation, annotation]
        )
        with client:
            review = review_claim("A specific claim to check.", client)
        self.assertEqual(len(review.sources), 1)
        self.assertEqual(captured[0]["tools"][0]["type"], "web_search")
        self.assertEqual(captured[0]["tool_choice"], "required")
        self.assertFalse(captured[0]["store"])

    def test_missing_key_empty_evidence_and_api_error(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            review_claim("A specific claim to check.")
        client, _ = fake_client("An answer without a source.")
        with client, self.assertRaisesRegex(RuntimeError, "no sourced"):
            review_claim("A specific claim to check.", client)
        client, _ = fake_client("", status=401)
        with client, self.assertRaisesRegex(RuntimeError, "API key"):
            review_claim("A specific claim to check.", client)

    def test_form_manual_mode_and_bad_input(self):
        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=15
        ).run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        app.text_area[0].set_value("A specific claim to check.")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(
            any("Manual evidence checklist" in item.value for item in app.markdown)
        )


if __name__ == "__main__":
    unittest.main()
