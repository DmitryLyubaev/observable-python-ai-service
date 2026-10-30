"""One bounded, non-retrying direct Claude request. No credentials in telemetry."""

import asyncio
import json
import math
import re
from decimal import Decimal

import httpx

from p19.acceptance import write_once
from p19.provider import ProviderFailure

MODEL = "claude-haiku-5-5"
API_VERSION = "2026-10-21"
ENDPOINT = "https://api.anthropic.com"
MAX_OUTPUT = 1024
SYSTEM = (
    "Investigate only this synthetic sales-export failure and the supplied evidence. "
    "A matching receiver receipt establishes received; an explicit rejection establishes "
    "rejected; otherwise the receiver outcome is unresolved. A timeout alone establishes "
    "neither rejection nor receipt. Cite only supplied record IDs, and use an empty list "
    "when no records exist. Explain the supported fact and uncertainty concisely. Suggest "
    "one read-only diagnostic step. Do not send, repair or change a sale. Do not invent "
    "records or claim an action was performed. Return only the requested JSON object."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "integer", "const": 1},
        "summary": {"type": "string"},
        "receiver_outcome": {"type": "string", "enum": ["rejected", "received", "unresolved"]},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "uncertainty": {"type": "string"},
        "next_diagnostic_step": {"type": "string"},
    },
    "required": [
        "schema_version",
        "summary",
        "receiver_outcome",
        "evidence_ids",
        "uncertainty",
        "next_diagnostic_step",
    ],
    "additionalProperties": False,
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def build_request(record, evidence):
    for row in evidence["records"]:
        if row.get("export_id") != record["export_id"] or row.get("sale_id") != record["sale_id"]:
            raise ValueError("evidence_identity_mismatch")
    return canonical(
        {
            "model": MODEL,
            "max_tokens": MAX_OUTPUT,
            "stream": False,
            "service_tier": "standard_only",
            "thinking": {"type": "adaptive"},
            "system": SYSTEM,
            "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            "messages": [
                {
                    "role": "user",
                    "content": canonical(
                        {
                            "failure": record,
                            "records": evidence["records"],
                        }
                    ).decode(),
                }
            ],
        }
    )


def priced_usage(body):
    """A known charge requires recognized billing dimensions and integer token usage."""
    try:
        if body["model"] != MODEL:
            return None
        usage = body["usage"]
        incoming, outgoing = usage["input_tokens"], usage["output_tokens"]
        if not (type(incoming) is int and 0 <= incoming <= 1_000_000):
            return None
        if not (type(outgoing) is int and 0 <= outgoing <= MAX_OUTPUT):
            return None
        if (
            usage.get("service_tier", "standard") != "standard"
            or usage.get("speed", "standard") != "standard"
            or usage.get("inference_geo", "global") != "global"
        ):
            return None
        for name in ("cache_creation_input_tokens", "cache_read_input_tokens"):
            count = usage.get(name, 0)
            if type(count) is not int or count != 0:
                return None
        for name in ("cache_creation", "server_tool_use"):
            if any(type(count) is not int or count != 0 for count in usage.get(name, {}).values()):
                return None
        thinking = usage.get("output_tokens_details", {}).get("thinking_tokens", 0)
        if type(thinking) is not int or not 0 <= thinking <= outgoing:
            return None
        input_rate, output_rate = (
            (Decimal("0.10"), Decimal("0.50"))
            if incoming <= 100_000
            else (Decimal("0.50"), Decimal("2.50"))
        )
        cost = (incoming * input_rate + outgoing * output_rate) / Decimal(1_000_000)
        return {
            "provenance": "provider",
            "model": MODEL,
            "input_tokens": incoming,
            "output_tokens": outgoing,
            "thinking_tokens_included": thinking,
            "cost_usd": format(cost.normalize(), "f"),
            "rate_date": "2026-10-30",
        }
    except (KeyError, TypeError, AttributeError):
        return None


def read_key(path):
    try:
        key = path.read_text().strip()
        if not key or len(key) > 8192 or "\n" in key or "\r" in key:
            raise ValueError
        return key
    except (OSError, ValueError):
        pass
    raise ProviderFailure("provider_key_unavailable", True)


async def _request(method, path, key, payload, timeout_seconds, transport=None):
    async with asyncio.timeout(timeout_seconds):
        async with httpx.AsyncClient(
            transport=transport,
            follow_redirects=False,
            trust_env=False,
            timeout=httpx.Timeout(timeout_seconds),
            headers={
                "Authorization": f"Bearer {key}",
                "anthropic-version": API_VERSION,
                "Content-Type": "application/json",
            },
        ) as client:
            async with client.stream(method, ENDPOINT + path, content=payload) as response:
                chunks, length = [], 0
                async for chunk in response.aiter_bytes():
                    length += len(chunk)
                    if length > 262_144:
                        raise ValueError("provider_reply_too_large")
                    chunks.append(chunk)
                request_id = response.headers.get("request-id", "")
                if not re.fullmatch(r"[A-Za-z0-9_-]{0,128}", request_id):
                    request_id = ""
                return response.status_code, request_id, b"".join(chunks)


def bounded_request(method, path, key_path, payload=None, timeout_seconds=10, transport=None):
    if path not in {"/v1/messages", "/v1/messages/count_tokens", f"/v1/models/{MODEL}"}:
        raise ValueError("provider_path_not_allowed")
    if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 10:
        raise ProviderFailure("provider_deadline", True)
    key = read_key(key_path)
    failure = None
    try:
        return asyncio.run(_request(method, path, key, payload, timeout_seconds, transport))
    except (TimeoutError, httpx.TimeoutException):
        failure = "provider_timeout"
    except (httpx.HTTPError, OSError, ValueError):
        failure = "provider_transport_failure"
    # Raise outside the handler so raw connection/header exceptions are not chained.
    raise ProviderFailure(failure)


class ClaudeProvider:
    def __init__(self, payload, key_path, *, receipt_path, transport=None):
        self.payload = payload
        self.key_path = key_path
        self.receipt_path = receipt_path
        self.transport = transport

    def invoke(self, record, evidence, attempt, timeout_seconds):
        status, request_id, raw = bounded_request(
            "POST", "/v1/messages", self.key_path, self.payload, timeout_seconds, self.transport
        )
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeError):
            body = {"unparseable": raw.decode(errors="replace")}
        artifact_error = False
        try:
            write_once(
                self.receipt_path, {"status": status, "request_id": request_id, "body": body}
            )
        except (OSError, ValueError):
            artifact_error = True
        if status != 200:
            kind = "rate_limit" if status == 429 else "provider_http_failure"
            # No live retry, including rate limits. Preserve conservative uncertainty.
            raise ProviderFailure(kind)
        usage = priced_usage(body)
        error = "provider_receipt_failed" if artifact_error else None
        result = None
        if usage is None:
            error = error or "invalid_provider_usage"
        try:
            if (
                body["stop_reason"] != "end_turn"
                or (body.get("stop_details") or {}).get("type") == "refusal"
            ):
                raise ValueError
            text = [block["text"] for block in body["content"] if block["type"] == "text"]
            if len(text) != 1:
                raise ValueError
            result = json.loads(text[0])
            if not isinstance(result, dict):
                raise ValueError
        except (ValueError, KeyError, TypeError, AttributeError):
            error = error or "invalid_provider_output"
        return {
            "result": result,
            "usage": usage,
            "error": error,
            "provider_request_id": request_id,
            "provider_model": body.get("model") if isinstance(body, dict) else None,
        }
