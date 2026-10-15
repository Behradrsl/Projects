"""Real SDK request/response contract tests with an in-memory HTTP transport.

These tests do not make network requests and do not satisfy the live T09 gate.
"""

import json
import unittest
from unittest.mock import patch

import httpx2 as httpx
from openai import OpenAI

from engine import GenerationError, OpenAIChatGenerator

MODEL = "package Demo { part pump; }"
KEY = "sk-fixture-only-not-a-real-api-key"


def completion(code=MODEL, usage=True, finish_reason="stop"):
    payload = {
        "id": "chatcmpl_fixture",
        "object": "chat.completion",
        "created": 1,
        "model": "fixture-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": code},
                "finish_reason": finish_reason,
            }
        ],
    }
    if usage:
        payload["usage"] = {
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "total_tokens": 18,
        }
    return payload


def fixture_client(payload=None, *, status=200, handler=None):
    captured = []

    def record(request):
        captured.append(request)
        if handler is not None:
            return handler(request, len(captured))
        return httpx.Response(status, json=payload if payload is not None else completion())

    client = OpenAI(
        api_key=KEY,
        base_url="https://provider.example/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(record)),
        max_retries=0,
    )
    return client, captured


class ChatAPIContractTests(unittest.TestCase):
    def test_actual_sdk_chat_completions_request_and_reported_token_counts(self):
        client, requests = fixture_client()
        with client:
            with OpenAIChatGenerator("fixture-model", KEY, client=client) as generator:
                output = generator.generate("  A pump.\n", "Exact custom system prompt")
            self.assertFalse(client.is_closed())
        self.assertEqual(output.code, MODEL)
        self.assertEqual(output.input_tokens, 11)
        self.assertEqual(output.output_tokens, 7)
        self.assertEqual(len(requests), 1)
        self.assertEqual(str(requests[0].url), "https://provider.example/v1/chat/completions")
        payload = json.loads(requests[0].content)
        self.assertEqual(payload["model"], "fixture-model")
        self.assertEqual(payload["max_tokens"], 8192)
        self.assertEqual(
            payload["messages"][0],
            {"role": "system", "content": "Exact custom system prompt"},
        )
        user_payload = json.loads(payload["messages"][1]["content"])
        self.assertEqual(user_payload["description"], "  A pump.\n")
        timeout = requests[0].extensions["timeout"]
        self.assertTrue(all(value == 60 for value in timeout.values()))

    def test_revision_contains_frozen_description_previous_complete_code_and_feedback(
        self,
    ):
        client, requests = fixture_client()
        feedback = {
            "parse_state": "invalid",
            "diagnostics": [{"message": "Expected brace"}],
        }
        with (
            client,
            OpenAIChatGenerator("fixture-model", KEY, client=client) as generator,
        ):
            generator.generate(
                "Original description", "System prompt", "package Broken {", feedback
            )
        payload = json.loads(requests[0].content)
        user_payload = json.loads(payload["messages"][1]["content"])
        self.assertEqual(user_payload["description"], "Original description")
        self.assertEqual(user_payload["previous_code"], "package Broken {")
        self.assertEqual(user_payload["diagnostics"], feedback)
        self.assertEqual(len(payload["messages"]), 2)

    def test_missing_provider_usage_stays_unknown(self):
        client, _ = fixture_client(completion(usage=False))
        with (
            client,
            OpenAIChatGenerator("fixture-model", KEY, client=client) as generator,
        ):
            output = generator.generate("A pump", "Generate SysML")
        self.assertIsNone(output.input_tokens)
        self.assertIsNone(output.output_tokens)

    def test_provider_missing_one_usage_count_does_not_invent_it(self):
        payload = completion()
        payload["usage"].pop("completion_tokens")
        client, _ = fixture_client(payload)
        with (
            client,
            OpenAIChatGenerator("fixture-model", KEY, client=client) as generator,
        ):
            output = generator.generate("A pump", "Generate SysML")
        self.assertEqual(output.input_tokens, 11)
        self.assertIsNone(output.output_tokens)

    def test_one_sdk_retry_recovers_after_rate_limit(self):
        def handler(request, attempt):
            if attempt == 1:
                return httpx.Response(
                    429,
                    headers={"retry-after": "0"},
                    json={"error": {"message": "Rate limited", "type": "rate_limit_error"}},
                )
            return httpx.Response(200, json=completion())

        client, requests = fixture_client(handler=handler)
        with (
            client,
            OpenAIChatGenerator("fixture-model", KEY, client=client) as generator,
        ):
            output = generator.generate("A pump", "Generate SysML")
        self.assertEqual(output.code, MODEL)
        self.assertEqual(len(requests), 2)

    def test_api_failure_is_generic_and_never_exposes_provider_body_or_credential(self):
        provider_body = f"Sensitive upstream body includes {KEY}"
        client, requests = fixture_client(
            {"error": {"message": provider_body, "type": "authentication_error"}},
            status=401,
        )
        with (
            client,
            OpenAIChatGenerator("fixture-model", KEY, client=client) as generator,
        ):
            with self.assertRaises(GenerationError) as caught:
                generator.generate("A pump", "Generate SysML")
        self.assertEqual(len(requests), 1)
        self.assertNotIn(KEY, str(caught.exception))
        self.assertNotIn(provider_body, str(caught.exception))

    def test_timeout_is_retried_once_and_reported_without_exception_details(self):
        def handler(request, attempt):
            raise httpx.ReadTimeout(f"Unsafe transport text {KEY}", request=request)

        client, requests = fixture_client(handler=handler)
        with (
            client,
            OpenAIChatGenerator("fixture-model", KEY, client=client) as generator,
        ):
            with self.assertRaises(GenerationError) as caught:
                generator.generate("A pump", "Generate SysML")
        self.assertEqual(len(requests), 2)
        self.assertNotIn(KEY, str(caught.exception))
        self.assertNotIn("Unsafe transport", str(caught.exception))

    def test_empty_refused_and_malformed_completion_are_rejected(self):
        refused = completion(None)
        refused["choices"][0]["message"]["refusal"] = "I cannot complete this request."
        candidates = (
            completion(""),
            completion("   "),
            refused,
            {"id": "chatcmpl_empty", "object": "chat.completion", "choices": []},
        )
        for payload in candidates:
            with self.subTest(payload=payload):
                client, _ = fixture_client(payload)
                with (
                    client,
                    OpenAIChatGenerator("fixture-model", KEY, client=client) as generator,
                ):
                    with self.assertRaises(GenerationError):
                        generator.generate("A pump", "Generate SysML")

    def test_nonstandard_finish_reason_is_retained_as_a_provider_warning(self):
        client, _ = fixture_client(completion(finish_reason="length"))
        with (
            client,
            OpenAIChatGenerator("fixture-model", KEY, client=client) as generator,
        ):
            output = generator.generate("A pump", "Generate SysML")
        self.assertEqual(output.code, MODEL)
        self.assertTrue(output.warnings)
        self.assertIn("completeness", output.warnings[0])

    def test_caller_owned_client_remains_open_after_success_and_failure(self):
        for status in (200, 401):
            with self.subTest(status=status):
                payload = completion() if status == 200 else {"error": {"message": "No access"}}
                client, _ = fixture_client(payload, status=status)
                try:
                    with OpenAIChatGenerator("fixture-model", KEY, client=client) as generator:
                        if status == 200:
                            generator.generate("A pump", "Generate SysML")
                        else:
                            with self.assertRaises(GenerationError):
                                generator.generate("A pump", "Generate SysML")
                    self.assertFalse(client.is_closed())
                finally:
                    client.close()

    def test_owned_sdk_client_uses_required_settings_and_closes_on_exit(self):
        client, _ = fixture_client()
        with patch("openai.OpenAI", return_value=client) as create_client:
            with OpenAIChatGenerator(
                "fixture-model", KEY, "https://provider.example/v1"
            ) as generator:
                generator.generate("A pump", "Generate SysML")
                self.assertFalse(client.is_closed())
        self.assertTrue(client.is_closed())
        self.assertEqual(create_client.call_args.kwargs["timeout"], 60.0)
        self.assertEqual(create_client.call_args.kwargs["max_retries"], 1)
        self.assertEqual(create_client.call_args.kwargs["base_url"], "https://provider.example/v1")

    def test_empty_api_key_is_rejected_before_creating_a_connection(self):
        for key in ("", "   "):
            with self.subTest(key=key), self.assertRaises(ValueError):
                OpenAIChatGenerator("fixture-model", key)

    def test_http_200_provider_error_has_safe_specific_code_and_retryability(self):
        client, _ = fixture_client(
            {"error": {"code": 503, "message": f"Unsafe upstream body {KEY}"}}
        )
        with client, OpenAIChatGenerator("fixture-model", KEY, client=client) as generator:
            with self.assertRaises(GenerationError) as caught:
                generator.generate("A system", "SysML v2 only")
        self.assertEqual(caught.exception.code, "provider_503")
        self.assertTrue(caught.exception.retryable)
        self.assertNotIn(KEY, str(caught.exception))
        self.assertNotIn("Unsafe upstream", str(caught.exception))

    def test_http_200_access_error_is_not_retried_as_a_transient_failure(self):
        client, _ = fixture_client({"error": {"code": 402, "message": "Out of credits"}})
        with client, OpenAIChatGenerator("fixture-model", KEY, client=client) as generator:
            with self.assertRaises(GenerationError) as caught:
                generator.generate("A system", "SysML v2 only")
        self.assertEqual(caught.exception.code, "provider_402")
        self.assertFalse(caught.exception.retryable)

    def test_reasoning_only_budget_exhaustion_is_actionable_and_keeps_usage(self):
        payload = completion(None, finish_reason="length")
        payload["usage"]["completion_tokens"] = 8192
        payload["usage"]["completion_tokens_details"] = {"reasoning_tokens": 8192}
        client, _ = fixture_client(payload)
        with client, OpenAIChatGenerator("fixture-model", KEY, client=client) as generator:
            with self.assertRaises(GenerationError) as caught:
                generator.generate("A system", "SysML v2 only")
        self.assertEqual(caught.exception.code, "output_budget")
        self.assertFalse(caught.exception.retryable)
        self.assertEqual(caught.exception.output_tokens, 8192)
        self.assertEqual(caught.exception.reasoning_tokens, 8192)
        self.assertIn("Increase", str(caught.exception))

    def test_missing_choices_is_identifiable_and_retryable(self):
        client, _ = fixture_client({"choices": []})
        with client, OpenAIChatGenerator("fixture-model", KEY, client=client) as generator:
            with self.assertRaises(GenerationError) as caught:
                generator.generate("A system", "SysML v2 only")
        self.assertEqual(caught.exception.code, "missing_choices")
        self.assertTrue(caught.exception.retryable)

    def test_short_requests_omit_empty_history_and_preserve_real_usage(self):
        payload = completion()
        payload["usage"]["completion_tokens_details"] = {"reasoning_tokens": 3}
        client, requests = fixture_client(payload)
        with (
            client,
            OpenAIChatGenerator(
                "fixture-model", KEY, client=client, max_output_tokens=16384
            ) as generator,
        ):
            result = generator.generate("Original description", "SysML v2 only")
        body = json.loads(requests[0].content)
        self.assertEqual(body["max_tokens"], 16384)
        self.assertEqual(
            json.loads(body["messages"][1]["content"]), {"description": "Original description"}
        )
        self.assertEqual(result.reasoning_tokens, 3)
        self.assertEqual(result.output_tokens, 7)  # Reasoning is a subset, not added twice.


if __name__ == "__main__":
    unittest.main()
