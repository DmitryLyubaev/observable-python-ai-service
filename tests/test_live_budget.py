import json
import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text

from p19.attempts import AttemptStore
from p19.evidence import lookup, seed


@pytest.fixture
def study(store):
    from p19.live import LiveStudy, make_manifest

    assert os.environ["P19_PROJECT"] == "p19-check"
    with store.db.write() as conn:
        conn.execute(text("DELETE FROM live_calls"))
        conn.execute(text("DELETE FROM live_studies"))
    seed(store)
    manifest = make_manifest(store, approval={"owner_confirmed": True}, counts=[1000] * 3)
    value = LiveStudy(store)
    value.initialize(manifest)
    yield value, store, manifest
    with store.db.write() as conn:
        conn.execute(text("DELETE FROM live_calls"))
        conn.execute(text("DELETE FROM live_studies"))


def create_job(store, n=0, key="case"):
    case = json.loads(Path("fixtures/cases.json").read_text())[n]
    job = store.admit(case, key)
    store.claim(job["id"], "owner")
    return store.get(job["id"])


def reserve_job(study, store, n=0, key="case", fault=False):
    job = create_job(store, n, key)
    call = study.prepare(job["failure"], lookup(job["failure"], store))
    attempt_id, number = AttemptStore(store).begin(job["id"], "owner", fault=fault, live_call=call)
    return job, attempt_id, number


def known_usage():
    return {
        "provenance": "provider",
        "model": "claude-haiku-5-5",
        "input_tokens": 1000,
        "output_tokens": 100,
        "thinking_tokens_included": 25,
        "cost_usd": "0.00015",
        "rate_date": "2026-10-30",
    }


def test_study_cannot_reset(study):
    from p19.live import LiveGuard

    value, store, manifest = study
    value.initialize(manifest)
    changed = deepcopy(manifest)
    changed["source_digest"] = "0" * 64
    with pytest.raises(LiveGuard):
        value.initialize(changed)
    changed = deepcopy(manifest)
    changed["study_id"] = "fresh-name"
    with pytest.raises(LiveGuard):
        value.initialize(changed)
    assert value.status()["cap_usd"] == "2"
    value.stop("operator_stop")
    with pytest.raises(LiveGuard):
        value.initialize(manifest)


def test_case_reservation_is_atomic(study):
    from p19.live import LiveGuard

    value, store, _ = study
    jobs = [create_job(store, key=f"race-{n}") for n in range(2)]
    calls = [value.prepare(j["failure"], lookup(j["failure"], store)) for j in jobs]

    def attempt(n):
        try:
            return AttemptStore(store).begin(jobs[n]["id"], "owner", live_call=calls[n])
        except LiveGuard:
            return None

    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(attempt, range(2)))
    assert sum(reply is not None for reply in replies) == 1
    status = value.status()
    assert status["consumed_slots"] == 1
    assert Decimal(status["reserved_usd"]) == Decimal("0.50256")
    assert Decimal("0.50256") * 3 == Decimal("1.50768") < Decimal("2")


def test_dispatch_rollback_and_predispatch_cancel_use_no_slot(study):
    value, store, _ = study
    with pytest.raises(RuntimeError):
        reserve_job(value, store, fault=True)
    assert value.status()["consumed_slots"] == 0
    job = create_job(store, key="cancelled")
    call = value.prepare(job["failure"], lookup(job["failure"], store))
    store.cancel(job["id"])
    assert AttemptStore(store).begin(job["id"], "owner", live_call=call) is None
    assert value.status()["consumed_slots"] == 0


def test_unknown_and_rejected_slots_survive_reset_and_restart(study):
    from p19.live import LiveGuard, LiveStudy

    value, store, manifest = study
    job, attempt, _ = reserve_job(value, store)
    store.cancel(job["id"])
    AttemptStore(store).finish(attempt, "unknown")
    assert Decimal(value.status()["reserved_usd"]) == Decimal("0.50256")
    store.reset()
    restarted = LiveStudy(store)
    assert restarted.status()["consumed_slots"] == 1
    with pytest.raises(LiveGuard):
        reserve_job(restarted, store, key="new-name")
    assert restarted.status()["consumed_slots"] == 1


def test_unassessed_or_failed_predecessor_blocks_dispatch(study):
    from p19.live import LiveGuard

    value, store, _ = study
    job, attempt, _ = reserve_job(value, store)
    AttemptStore(store).finish(attempt, "responded", known_usage())
    store.finish(job["id"], "owner", "succeeded", result={"synthetic": True})
    with pytest.raises(LiveGuard):
        reserve_job(value, store, n=1, key="later")
    value.assess("export_0", "fail", "Assistant: explanation contradicted facts.")
    with pytest.raises(LiveGuard):
        reserve_job(value, store, n=1, key="later-again")
    assert value.status()["consumed_slots"] == 1


def test_assessed_success_allows_next_case_and_known_cost(study):
    value, store, _ = study
    for n in range(3):
        job, attempt, _ = reserve_job(value, store, n=n, key=f"live-{n}")
        AttemptStore(store).finish(attempt, "responded", known_usage())
        store.finish(job["id"], "owner", "succeeded", result={"synthetic": True})
        value.assess(f"export_{n}", "pass", "Assistant: facts and next step checked.")
    status = value.status()
    assert status["state"] == "completed" and status["consumed_slots"] == 3
    assert Decimal(status["known_cost_usd"]) == Decimal("0.00045")
    assert Decimal(status["reserved_usd"]) == 0


def test_invalid_accounting_does_not_release_reservation(study):
    value, store, _ = study
    _, attempt, _ = reserve_job(value, store)
    usage = known_usage()
    usage["cost_usd"] = "0"
    AttemptStore(store).finish(attempt, "responded", usage)
    assert Decimal(value.status()["reserved_usd"]) == Decimal("0.50256")
    assert value.status()["state"] == "stopped"


def test_changed_evidence_or_source_prevents_dispatch(study, monkeypatch):
    from p19.live import LiveGuard

    value, store, _ = study
    job = create_job(store)
    evidence = lookup(job["failure"], store)
    evidence["records"][0]["fact"]["reason"] = "changed"
    with pytest.raises(LiveGuard):
        value.prepare(job["failure"], evidence)
    monkeypatch.setattr("p19.live.source_digest", lambda: "different-source")
    with pytest.raises(LiveGuard):
        value.prepare(job["failure"], lookup(job["failure"], store))
    assert value.status()["consumed_slots"] == 0


def test_known_rejection_keeps_its_consumed_slot(study):
    from p19.live import LiveGuard

    value, store, _ = study
    _, attempt, _ = reserve_job(value, store)
    AttemptStore(store).finish(attempt, "rejected")
    assert value.status()["consumed_slots"] == 1
    assert Decimal(value.status()["reserved_usd"]) == 0
    with pytest.raises(LiveGuard):
        reserve_job(value, store, key="retry-after-rejection")


@pytest.mark.parametrize(
    "kind,expected,cost,reserved,calls",
    [
        ("success", "succeeded", "0.00015", "0", 1),
        ("invalid", "failed", "0.00015", "0", 1),
        ("cancel_after", "cancelled", "0.00015", "0", 1),
        ("rate_limit", "outcome_unknown", "0", "0.50256", 1),
        ("timeout", "outcome_unknown", "0", "0.50256", 1),
        ("result_fault", "outcome_unknown", "0", "0.50256", 1),
        ("dispatch_fault", "failed", "0", "0", 0),
        ("cancel_before", "cancelled", "0", "0", 0),
    ],
)
def test_live_runner_preserves_accounting_and_never_retries(
    study, tmp_path, monkeypatch, kind, expected, cost, reserved, calls
):
    from p19 import claude
    from p19.live import STUDY
    from p19.runner import run_job

    value, store, _ = study
    case = json.loads(Path("fixtures/cases.json").read_text())[0]
    job = store.admit(case, f"runner-{kind}")
    key = tmp_path / "key"
    key.write_text("fake-test-key")
    monkeypatch.setenv("P19_CLAUDE_KEY_FILE", str(key))
    monkeypatch.setenv("P19_LIVE_RECEIPTS", str(tmp_path / "receipts"))
    seen = []

    def response(request):
        seen.append(request)
        if kind == "timeout":
            raise httpx.ReadTimeout("SECRET_CANARY", request=request)
        if kind == "rate_limit":
            return httpx.Response(429, json={"error": {"type": "rate_limit_error"}})
        if kind == "cancel_after":
            store.cancel(job["id"])
        result = {
            "schema_version": 1,
            "summary": "The fictional account code was rejected.",
            "receiver_outcome": "rejected",
            "evidence_ids": ["ev_reject"],
            "uncertainty": "Only supplied evidence was checked.",
            "next_diagnostic_step": "Inspect account mapping before deciding on any action.",
        }
        return httpx.Response(
            200,
            json={
                "model": "claude-haiku-5-5",
                "stop_reason": "end_turn",
                "content": [
                    {
                        "type": "text",
                        "text": "bad json" if kind == "invalid" else json.dumps(result),
                    }
                ],
                "usage": {
                    "input_tokens": 1000,
                    "output_tokens": 100,
                    "output_tokens_details": {"thinking_tokens": 25},
                },
            },
        )

    real_provider = claude.ClaudeProvider

    def factory(*args, **kwargs):
        return real_provider(*args, **kwargs, transport=httpx.MockTransport(response))

    monkeypatch.setattr(claude, "ClaudeProvider", factory)

    def hook(stage):
        if kind == "cancel_before" and stage == "before_dispatch":
            store.cancel(job["id"])

    fault = "dispatch" if kind == "dispatch_fault" else "result" if kind == "result_fault" else None
    run_job(job["id"], "owner", store=store, live_study_id=STUDY, hook=hook, fault=fault)
    saved = store.get(job["id"])
    assert saved["state"] == expected
    assert len(seen) == calls
    assert len(saved["attempts"]) == calls
    assert Decimal(value.status()["known_cost_usd"]) == Decimal(cost)
    assert Decimal(value.status()["reserved_usd"]) == Decimal(reserved)
    if calls:
        from p19.reporting import build_summary

        summary = build_summary([job["id"]], store)
        assert summary["provider_provenance"] == "live"
        assert summary["simulated_usage_attempts"] == 0
        if cost == "0":
            assert summary["known_real_cost_usd"] is None
        else:
            assert Decimal(summary["known_real_cost_usd"]) == Decimal(cost)
    if expected != "succeeded":
        assert saved["result"] is None
        assert value.status()["state"] == "stopped"


def test_recovery_preserves_live_unknown_reservation(study):
    from p19.recovery import recover_worker

    value, store, _ = study
    job, _, _ = reserve_job(value, store)
    assert recover_worker(store, "owner") == [job["id"]]
    assert store.get(job["id"])["state"] == "outcome_unknown"
    assert Decimal(value.status()["reserved_usd"]) == Decimal("0.50256")
    assert value.status()["state"] == "stopped"
