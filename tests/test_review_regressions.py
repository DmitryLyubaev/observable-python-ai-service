import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import httpx
import pytest
from conftest import record
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def test_dispatch_lock_wait_is_bounded(store):
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    from p19.attempts import AttemptStore

    job = store.admit(record(), "bounded-lock")
    store.claim(job["id"], "worker")
    with store.db.engine.begin() as held:
        held.execute(text("SELECT pg_advisory_xact_lock(190019)"))
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                AttemptStore(store).begin, job["id"], "worker", deadline=time.monotonic() + 0.1
            )
            with pytest.raises(OperationalError):
                future.result(timeout=1)
    assert not store.get(job["id"])["attempts"]


def test_known_reply_after_deadline_is_not_success(store, monkeypatch):
    import p19.runner as runner

    clock = [0.0]
    timer = SimpleNamespace(monotonic=lambda: clock[0], sleep=lambda _: None)
    monkeypatch.setattr(runner, "time", timer)
    import p19.attempts as attempt_module
    import p19.db as db_module

    monkeypatch.setattr(attempt_module, "time", timer, raising=False)
    monkeypatch.setattr(db_module, "time", timer, raising=False)
    job = store.admit(record(), "late-reply")

    def hook(stage):
        if stage == "after_reply_before_commit":
            clock[0] = 31

    runner.run_job(job["id"], "worker", store=store, hook=hook)
    saved = store.get(job["id"])
    assert saved["state"] == "failed" and saved["result"] is None
    assert saved["attempts"][0]["usage"]["provenance"] == "simulated"


@pytest.mark.parametrize("route", ["admission", "stream"])
def test_unhandled_api_exception_and_chain_do_not_leak_framework_spans(monkeypatch, caplog, route):
    from p19.api import create_app
    from p19.telemetry import configure_telemetry

    configure_telemetry("p19-api")
    exporter = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setenv("P19_TOKEN", "review_dummy_token")

    class BrokenStore:
        def admit(self, *args, **kwargs):
            try:
                raise KeyError("review_dummy_token")
            except KeyError as exc:
                raise RuntimeError("payload_marker_review") from exc

        def get(self, *args):
            return {"sequence": 1, "state": "queued"}

        def events_after(self, *args):
            if args[1] == 0:
                return [{"sequence": 1, "kind": "queued", "job_id": "test", "data": {}}]
            return self.admit()

    async def exercise():
        transport = httpx.ASGITransport(app=create_app(BrokenStore()), raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            if route == "admission":
                response = await client.post(
                    "/investigations",
                    json={},
                    headers={"Authorization": "Bearer review_dummy_token"},
                )
                assert response.status_code == 500
            else:
                response = await client.get(
                    "/investigations/test/events",
                    headers={"Authorization": "Bearer review_dummy_token"},
                )
                assert response.status_code == 200

    asyncio.run(exercise())
    spans = exporter.get_finished_spans()
    assert any(
        span.name in {"POST /investigations", "GET /investigations/{job_id}/events"}
        for span in spans
    )
    serialized = " ".join(span.to_json() for span in spans) + caplog.text
    assert "review_dummy_token" not in serialized
    assert "payload_marker_review" not in serialized


def test_celery_error_path_keeps_chained_exception_out_of_logs(monkeypatch, caplog, capsys):
    from p19 import worker

    def broken():
        try:
            raise KeyError("celery_dummy_token")
        except KeyError as exc:
            raise RuntimeError("celery_payload_marker") from exc

    monkeypatch.setattr(worker, "JobStore", broken)
    worker.investigate.apply(args=("synthetic-job",), throw=True)
    captured = capsys.readouterr()
    serialized = caplog.text + captured.out + captured.err
    assert "worker_execution_failed" in serialized
    assert "celery_dummy_token" not in serialized and "celery_payload_marker" not in serialized


@pytest.mark.parametrize("stage", ["inside_begin", "after_begin", "after_dispatch"])
def test_expired_execution_budget_never_invokes_provider(store, monkeypatch, stage):
    import p19.attempts as attempt_module
    import p19.db as db_module
    import p19.runner as runner

    clock = [0.0]
    timer = SimpleNamespace(monotonic=lambda: clock[0], sleep=lambda seconds: None)
    monkeypatch.setattr(runner, "time", timer)
    monkeypatch.setattr(attempt_module, "time", timer, raising=False)
    monkeypatch.setattr(db_module, "time", timer, raising=False)
    original = attempt_module.AttemptStore.begin

    def begin(*args, **kwargs):
        if stage == "inside_begin":
            clock[0] = 31
        value = original(*args, **kwargs)
        if stage == "after_begin":
            clock[0] = 31
        return value

    monkeypatch.setattr(attempt_module.AttemptStore, "begin", begin)
    calls = []
    original_invoke = runner.ControlledProvider.invoke

    def invoke(*args, **kwargs):
        calls.append(args[-1])
        return original_invoke(*args, **kwargs)

    monkeypatch.setattr(runner.ControlledProvider, "invoke", invoke)
    job = store.admit(record(), "deadline")

    def hook(name):
        if stage == "after_dispatch" and name == "after_dispatch":
            clock[0] = 31

    runner.run_job(job["id"], "worker", store=store, hook=hook)
    assert calls == []
    assert store.get(job["id"])["state"] in {"failed", "outcome_unknown"}


def test_failed_load_receipt_reserves_name_and_preserves_earlier_responses(tmp_path):
    from p19.acceptance import RunJournal

    target = tmp_path / "sample.json"
    with pytest.raises(RuntimeError):
        with RunJournal(target, {"source": "test"}) as journal:
            journal.response({"index": 0, "status": 202, "job_id": "first-job"})
            journal.response({"index": 1, "status": None, "error_type": "TransportError"})
            raise RuntimeError("sensitive_failure_detail")
    receipt = json.loads(target.read_text())
    assert receipt["status"] == "failed"
    assert receipt["responses"][0]["job_id"] == "first-job"
    assert "sensitive_failure_detail" not in target.read_text()
    with pytest.raises(FileExistsError):
        RunJournal(target, {"source": "retry"})
    assert target.with_suffix(".json.intent.json").exists()


def test_load_transport_failure_keeps_partial_responses_and_terminal_readback(tmp_path):
    from p19.acceptance import RunJournal

    target = tmp_path / "transport.json"
    with pytest.raises(ConnectionError):
        with RunJournal(target, {"source": "test"}) as journal:
            journal.job_reader = lambda job_id: {
                "id": job_id,
                "state": "succeeded",
                "attempts": [{}],
            }
            journal.capture_response(0, lambda: {"index": 0, "status": 202, "job_id": "accepted"})

            def disconnected():
                raise ConnectionError("private_transport_detail")

            journal.capture_response(1, disconnected)
    saved = json.loads(target.read_text())
    assert saved["responses"][1] == {"index": 1, "status": None, "error_type": "ConnectionError"}
    assert saved["terminal_observations"][0]["job_id"] == "accepted"
    assert saved["terminal_observations"][0]["state"] == "succeeded"
    assert "private_transport_detail" not in target.read_text()
