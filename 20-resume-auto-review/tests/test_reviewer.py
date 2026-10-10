import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx2 as httpx
from openai import OpenAI
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from streamlit.testing.v1 import AppTest

from reviewer import ai_review, extract_pdf, local_review


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


def pdf_fixture(text=None):
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=400)
    if text:
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): writer._add_object(font)}
                )
            }
        )
        content = DecodedStreamObject()
        content.set_data(("BT /F1 12 Tf 20 350 Td (" + text + ") Tj ET").encode())
        page[NameObject("/Contents")] = writer._add_object(content)
    result = io.BytesIO()
    writer.write(result)
    return result.getvalue()


class ReviewerTests(unittest.TestCase):
    def test_local_structure_and_literal_job_terms(self):
        sample = (ROOT / "sample_resume.txt").read_text()
        result = local_review(sample, "Python SQL Docker developer")
        self.assertIn("Skills: heading found", result)
        self.assertIn("docker", result)
        self.assertIn("not an ATS score", result)
        with self.assertRaises(ValueError):
            local_review("short")

    def test_extracts_text_and_rejects_scanned_or_bad_pdf(self):
        text = (
            "Alex Morgan builds Python tools and writes automated tests "
            "for applications."
        )
        self.assertIn("Alex Morgan", extract_pdf(pdf_fixture(text)))
        for data in (pdf_fixture(), b"not a PDF"):
            with self.assertRaises(ValueError):
                extract_pdf(data)

    def test_sdk_grounded_prompt_and_storage_setting(self):
        client, captured = fake_client("## Suggestions\nClarify the project outcome.")
        with client:
            result = ai_review(
                (ROOT / "sample_resume.txt").read_text(), "Python developer", client
            )
        self.assertIn("Suggestions", result)
        self.assertIn("Do not invent", captured[0]["instructions"])
        self.assertFalse(captured[0]["store"])

    def test_key_and_api_errors_are_readable(self):
        sample = (ROOT / "sample_resume.txt").read_text()
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            ai_review(sample)
        client, _ = fake_client("", status=401)
        with client, self.assertRaises(RuntimeError):
            ai_review(sample, client=client)

    def test_local_form_and_invalid_resume(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(
            any("Local resume review" in item.value for item in app.markdown)
        )
        app.text_area[0].set_value("short").run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)


if __name__ == "__main__":
    unittest.main()
