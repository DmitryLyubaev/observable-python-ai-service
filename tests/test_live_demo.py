import importlib.util
import json
import os
import threading
import uuid
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import docker
import httpx
import pytest
from sqlalchemy import text
from test_api import serve

from p19.evidence import seed
from p19.live import STUDY, LiveGuard, LiveStudy
from p19.runner import run_job


@pytest.fixture
def tool():
    spec = importlib.util.spec_from_file_location("live_tool", "scripts/live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def trial(store):
    assert os.environ["P19_PROJECT"] == "p19-check"
    with store.db.write() as conn:
        conn.execute(text("DELETE FROM live_calls"))
        conn.execute(text("DELETE FROM live_studies"))
    seed(store)
    root = Path(".local") / f"offline-live-{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    key = root / "fake-key"
    key.write_text("fake-test-key")
    yield store, root, key
    with store.db.write() as conn:
        conn.execute(text("DELETE FROM live_calls"))
        conn.execute(text("DELETE FROM live_studies"))


def model_metadata():
    return {
        "id": "claude-haiku-5-5",
        "lifecycle": "active",
        "max_input_tokens": 1000000,
        "max_tokens": 128000,
        "capabilities": {
            "structured_outputs": {"supported": True},
            "effort": {"low": {"supported": True}},
            "thinking": {"types": {"adaptive": {"supported": True}}},
        },
    }


def transport_responder(seen, *, fail=None, count=1000):
    def respond(request):
        seen.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=model_metadata())
        if request.url.path == "/v1/messages/count_tokens":
            return httpx.Response(200, json={"input_tokens": count})
        assert request.url.path == "/v1/messages"
        if fail == "timeout":
            raise httpx.ReadTimeout("PRIVATE_CANARY", request=request)
        supplied = json.loads(json.loads(request.content)["messages"][0]["content"])
        case = supplied["failure"]["export_id"]
        outcomes = {"export_0": "rejected", "export_1": "received", "export_2": "unresolved"}
        ids = {"export_0": ["ev_reject"], "export_1": ["ev_receipt"], "export_2": []}
        result = {
            "schema_version": 1,
            "summary": "Synthetic evidence supports this outcome.",
            "receiver_outcome": outcomes[case],
            "evidence_ids": ids[case],
            "uncertainty": "Only supplied evidence was checked.",
            "next_diagnostic_step": "Perform an independent read-only receiver check.",
        }
        return httpx.Response(
            200,
            json={
                "model": "claude-haiku-5-5",
                "stop_reason": "end_turn",
                "content": [
                    {
                        "type": "text",
                        "text": "bad json" if fail == "invalid" else json.dumps(result),
                    }
                ],
                "usage": {"input_tokens": 1000, "output_tokens": 100},
            },
        )

    return respond


def test_live_overlay_isolates_secret(tool, tmp_path):
    config = json.loads(Path("compose.live.yaml").read_text())
    tool.validate_secret_configuration(config)
    unsafe = deepcopy(config)
    unsafe["services"]["api"] = {"secrets": ["claude_api_key"]}
    with pytest.raises(LiveGuard):
        tool.validate_secret_configuration(unsafe)
    # Build only dummy context bytes, using the actual current exclusion rules.
    (tmp_path / "Dockerfile").write_text("FROM scratch\nCOPY . /\n")
    (tmp_path / ".dockerignore").write_bytes(Path(".dockerignore").read_bytes())
    (tmp_path / ".secrets").mkdir()
    (tmp_path / ".secrets/key").write_text("DUMMY_CONTEXT_CANARY")
    (tmp_path / "marker").write_text("public probe")
    client = docker.from_env()
    image, _ = client.images.build(
        path=str(tmp_path), tag=f"p19-check-probe:{uuid.uuid4().hex}", rm=True
    )
    container = client.containers.create(image.id, command=["not-started"])
    try:
        assert container.get_archive("/marker")[1]["size"] > 0
        with pytest.raises(docker.errors.NotFound):
            container.get_archive("/.secrets/key")
    finally:
        container.remove(v=False)
        client.images.remove(image.id)


def test_preflight_freezes_without_inference(tool, trial):
    store, root, key = trial
    seen = []
    tool.prepare(
        store,
        key,
        root / "manifest.json",
        {"owner_confirmed": True},
        transport=httpx.MockTransport(transport_responder(seen)),
    )
    assert len(seen) == 4
    assert all(r.url.path != "/v1/messages" for r in seen)
    counts = [json.loads(r.content) for r in seen if r.method == "POST"]
    assert all(
        set(r) == {"model", "messages", "system", "thinking", "output_config"} for r in counts
    )
    value = LiveStudy(store)
    value.require_preflight()
    assert value.status()["consumed_slots"] == 0
    with pytest.raises(LiveGuard):
        tool.prepare(
            store,
            key,
            root / "different-name.json",
            {"owner_confirmed": True},
            transport=httpx.MockTransport(transport_responder(seen)),
        )
    assert len(seen) == 4


@pytest.mark.parametrize("count", [4097, -1, True])
def test_bad_preflight_count_cannot_activate_allowance(tool, trial, count):
    store, root, key = trial
    seen = []
    with pytest.raises(LiveGuard):
        tool.prepare(
            store,
            key,
            root / "manifest.json",
            {"owner_confirmed": True},
            transport=httpx.MockTransport(transport_responder(seen, count=count)),
        )
    assert LiveStudy(store).status()["state"] == "uninitialized"
    assert all(r.url.path != "/v1/messages" for r in seen)
    assert any(
        json.loads(p.read_text())["status"] == "failed"
        for p in root.glob("preflight-*.json")
        if not p.name.endswith("intent.json")
    )


@pytest.mark.parametrize("fail", [None, "timeout", "invalid"])
def test_actual_cli_progress_retains_cases_and_stops_without_reposting(
    tool, trial, monkeypatch, fail
):
    from p19 import claude

    store, root, key = trial
    seen = []
    responder = transport_responder(seen, fail=fail)
    tool.prepare(
        store,
        key,
        root / "manifest.json",
        {"owner_confirmed": True},
        transport=httpx.MockTransport(responder),
    )
    monkeypatch.setenv("P19_CLAUDE_KEY_FILE", str(key))
    monkeypatch.setenv("P19_LIVE_RECEIPTS", str(root / "provider"))
    real_provider = claude.ClaudeProvider

    def factory(*args, **kwargs):
        return real_provider(*args, **kwargs, transport=httpx.MockTransport(responder))

    monkeypatch.setattr(claude, "ClaudeProvider", factory)
    stop = threading.Event()

    def worker():
        while not stop.is_set():
            for job in store.all():
                if job["state"] == "queued":
                    run_job(job["id"], "offline-worker", store=store, live_study_id=STUDY)
            stop.wait(0.03)

    thread = threading.Thread(target=worker, daemon=True)
    with serve(store) as client:
        thread.start()
        try:
            for n in range(1 if fail else 3):
                receipt = tool.run_next(store, str(client.base_url), root / "run")
                assert receipt["case_id"] == f"export_{n}"
                if fail:
                    assert receipt["state"] == "failed"
                    with pytest.raises(LiveGuard):
                        tool.run_next(store, str(client.base_url), root / "new-run")
                else:
                    assert receipt["state"] == "awaiting_assessment"
                    resumed = tool.run_next(store, str(client.base_url), root / "new-name")
                    assert resumed["job_id"] == receipt["job_id"]
                    LiveStudy(store).assess(f"export_{n}", "pass", "Assistant fixture assessment.")
        finally:
            stop.set()
            thread.join(timeout=35)
            assert not thread.is_alive()
    inference = [r for r in seen if r.url.path == "/v1/messages"]
    assert len(inference) == (1 if fail else 3)
    status = LiveStudy(store).status()
    assert status["state"] == ("stopped" if fail else "completed")
    if fail == "timeout":
        assert Decimal(status["reserved_usd"]) == Decimal("0.50256")
    else:
        assert Decimal(status["known_cost_usd"]) == Decimal("0.00015" if fail else "0.00045")
    receipts = list((root / "run").glob("*.receipt.json"))
    assert len(receipts) == (1 if fail else 3)
