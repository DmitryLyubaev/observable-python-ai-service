import json
import threading
import time
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from p19.provider import InvalidProviderOutput, ProviderFailure, validate_reply


def response_body():
    return {
        "id": "msg_demo",
        "model": "claude-haiku-5-5",
        "type": "message",
        "role": "assistant",
        "stop_reason": "end_turn",
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "schema_version": 1,
                        "summary": "The receipt confirms delivery.",
                        "receiver_outcome": "received",
                        "evidence_ids": ["ev_receipt"],
                        "uncertainty": "Only supplied evidence was inspected.",
                        "next_diagnostic_step": "Inspect the receipt before considering any resend.",
                    }
                ),
            }
        ],
        "usage": {
            "input_tokens": 1000,
            "output_tokens": 100,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0},
            "output_tokens_details": {"thinking_tokens": 25},
            "server_tool_use": {"web_fetch_requests": 0, "web_search_requests": 0},
            "service_tier": "standard",
            "speed": "standard",
            "inference_geo": "global",
        },
    }


def inputs():
    cases = json.loads(open("fixtures/cases.json").read())
    return cases[1], {
        "receiver_outcome": "received",
        "records": [
            {"id": "ev_receipt", "fact": {"kind": "receipt", "receiver_reference": "receipt_101"}}
        ],
    }


def invoke(tmp_path, body=None, status=200, handler=None):
    from p19.claude import ClaudeProvider, build_request

    record, evidence = inputs()
    key = tmp_path / "key"
    key.write_text("fake-test-key")
    requests = []

    def respond(request):
        requests.append(request)
        return (
            handler(request)
            if handler
            else httpx.Response(
                status,
                json=body if body is not None else response_body(),
                headers={"request-id": "req_demo"},
            )
        )

    provider = ClaudeProvider(
        build_request(record, evidence),
        key,
        receipt_path=tmp_path / "receipt.json",
        transport=httpx.MockTransport(respond),
    )
    return provider, requests, record, evidence


def test_request_excludes_reference_answers():
    from p19.claude import build_request

    record, evidence = inputs()
    evidence["receiver_outcome"] = "REFERENCE_CANARY"
    payload = build_request(record, evidence)
    request = json.loads(payload)
    assert b"REFERENCE_CANARY" not in payload
    supplied = json.loads(request["messages"][0]["content"])
    assert set(supplied) == {"failure", "records"}
    assert supplied["records"][0]["id"] == "ev_receipt"
    assert request["model"] == "claude-haiku-5-5"
    assert request["max_tokens"] == 1024 and request["stream"] is False
    assert request["service_tier"] == "standard_only"


def test_reply_usage_and_result(tmp_path):
    body = response_body()
    body["usage"]["harmless_metadata"] = "additive"
    provider, requests, record, evidence = invoke(tmp_path, body)
    reply = provider.invoke(record, evidence, 1, 2)
    assert validate_reply(reply, evidence)["receiver_outcome"] == "received"
    assert Decimal(reply["usage"]["cost_usd"]) == Decimal("0.00015")
    assert reply["usage"]["provenance"] == "provider"
    assert reply["usage"]["output_tokens"] == 100
    assert len(requests) == 1
    assert requests[0].headers["anthropic-version"] == "2026-10-21"
    assert json.loads((tmp_path / "receipt.json").read_text())["body"] == body


@pytest.mark.parametrize(
    "field,value",
    [
        ("input_tokens", -1),
        ("output_tokens", True),
        ("output_tokens", "100"),
        ("cache_creation_input_tokens", 2),
        ("speed", "fast"),
        ("service_tier", "priority"),
        ("inference_geo", "us"),
        ("server_tool_use", {"web_search_requests": 1}),
    ],
)
def test_unpriced_usage_remains_unknown(tmp_path, field, value):
    body = response_body()
    body["usage"][field] = value
    provider, requests, record, evidence = invoke(tmp_path, body)
    reply = provider.invoke(record, evidence, 1, 2)
    assert reply["usage"] is None
    assert reply["error"] == "invalid_provider_usage"
    assert len(requests) == 1


@pytest.mark.parametrize(
    "change", ["missing_usage", "wrong_model", "refusal", "truncated", "malformed"]
)
def test_content_errors_preserve_known_accounting(tmp_path, change):
    body = response_body()
    if change == "missing_usage":
        body.pop("usage")
    if change == "wrong_model":
        body["model"] = "unexpected_model"
    if change == "refusal":
        body["stop_details"] = {"type": "refusal"}
    if change == "truncated":
        body["stop_reason"] = "max_tokens"
    if change == "malformed":
        body["content"][0]["text"] = "not json"
    provider, requests, record, evidence = invoke(tmp_path, body)
    reply = provider.invoke(record, evidence, 1, 2)
    assert reply["error"]
    if change in {"missing_usage", "wrong_model"}:
        assert reply["usage"] is None
    else:
        assert Decimal(reply["usage"]["cost_usd"]) == Decimal("0.00015")
    assert len(requests) == 1


def test_foreign_citation_is_validated_after_usage(tmp_path):
    body = response_body()
    result = json.loads(body["content"][0]["text"])
    result["evidence_ids"] = ["foreign"]
    body["content"][0]["text"] = json.dumps(result)
    provider, _, record, evidence = invoke(tmp_path, body)
    reply = provider.invoke(record, evidence, 1, 2)
    with pytest.raises(InvalidProviderOutput):
        validate_reply(reply, evidence)
    assert reply["usage"]["input_tokens"] == 1000


@pytest.mark.parametrize("status", [429, 500, 529])
def test_ambiguous_http_failure_has_one_request(tmp_path, status):
    provider, requests, record, evidence = invoke(tmp_path, {"error": "RAW_CANARY"}, status)
    with pytest.raises(ProviderFailure) as caught:
        provider.invoke(record, evidence, 1, 2)
    assert not caught.value.definitely_not_processed
    assert "RAW_CANARY" not in str(caught.value)
    assert len(requests) == 1


def test_receipt_write_failure_preserves_usage(tmp_path):
    provider, _, record, evidence = invoke(tmp_path)
    (tmp_path / "receipt.json").write_text("original")
    reply = provider.invoke(record, evidence, 1, 2)
    assert reply["error"] == "provider_receipt_failed"
    assert reply["usage"]["cost_usd"] == "0.00015"
    assert (tmp_path / "receipt.json").read_text() == "original"


def test_slow_body_respects_total_deadline(tmp_path):
    from p19.claude import ClaudeProvider, build_request

    arrived = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            arrived.append(True)
            self.send_response(200)
            self.send_header("Content-Length", "1000")
            self.end_headers()
            try:
                for _ in range(100):
                    self.wfile.write(b" ")
                    self.wfile.flush()
                    time.sleep(0.02)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class LocalTransport(httpx.AsyncHTTPTransport):
        async def handle_async_request(self, request):
            request.url = request.url.copy_with(
                scheme="http", host="127.0.0.1", port=server.server_port
            )
            return await super().handle_async_request(request)

    key = tmp_path / "key"
    key.write_text("fake-test-key")
    record, evidence = inputs()
    provider = ClaudeProvider(
        build_request(record, evidence),
        key,
        receipt_path=tmp_path / "receipt.json",
        transport=LocalTransport(),
    )
    started = time.monotonic()
    try:
        with pytest.raises(ProviderFailure) as caught:
            provider.invoke(record, evidence, 1, 0.12)
        assert time.monotonic() - started < 0.8
        assert not caught.value.definitely_not_processed
        assert len(arrived) == 1
    finally:
        server.shutdown()
        server.server_close()


def test_transport_exception_hides_canary(tmp_path):
    def broken(request):
        raise httpx.ConnectError("SECRET_CANARY", request=request)

    provider, _, record, evidence = invoke(tmp_path, handler=broken)
    with pytest.raises(ProviderFailure) as caught:
        provider.invoke(record, evidence, 1, 2)
    assert "SECRET_CANARY" not in str(caught.value)
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("body", [[], "not-an-object", 1, None])
def test_non_object_reply_is_safe_and_unpriced(tmp_path, body):
    provider, requests, record, evidence = invoke(
        tmp_path, handler=lambda request: httpx.Response(200, content=json.dumps(body))
    )
    reply = provider.invoke(record, evidence, 1, 2)
    assert reply["error"] == "invalid_provider_usage"
    assert reply["usage"] is None
    assert len(requests) == 1
