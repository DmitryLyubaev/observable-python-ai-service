import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text

from p19.claude import canonical, priced_usage
from p19.live import PROPOSAL_SHA, STUDY, LiveGuard, LiveStudy, digest, make_manifest

FOLLOWUP = "p19-real-20261030-context-1"
FOLLOWUP_SHA = "65480db71891ff5b3dcc449636cc04ca7abef68b66c466c27deb0991b1900f16"


def snapshot(conn):
    from p19.live_history import original_snapshot

    return original_snapshot(conn)


def prior_history(store):
    from p19.evidence import seed
    from p19.jobs import json_value
    from p19.live_history import capture_history

    seed(store)
    root = Path(".local") / f"followup-history-{uuid.uuid4().hex}"
    (root / "provider").mkdir(parents=True)
    manifest = {"study_id": STUDY, "approval": {"approved_proposal_sha256": PROPOSAL_SHA}}
    (root / "manifest.json").write_text(json.dumps(manifest))
    with store.db.write() as conn:
        conn.execute(text("DELETE FROM live_calls"))
        conn.execute(text("DELETE FROM live_studies"))
        conn.execute(
            text(
                "INSERT INTO live_studies(id,manifest,manifest_hash,state,reason) "
                "VALUES(:id,CAST(:manifest AS jsonb),:hash,'stopped','job_failed')"
            ),
            {"id": STUDY, "manifest": json_value(manifest), "hash": digest(canonical(manifest))},
        )
        for n, (input_tokens, output_tokens) in enumerate([(732, 218), (735, 269)]):
            body = {
                "model": "claude-haiku-5-5",
                "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
            }
            usage = priced_usage(body)
            (root / "provider" / f"old-attempt-{n}.json").write_text(json.dumps({"body": body}))
            conn.execute(
                text(
                    "INSERT INTO live_calls(case_id,ordinal,study_id,job_id,attempt_id,"
                    "reservation_usd,cost_usd,usage,state,assessment) VALUES(:case,:n,:study,"
                    ":job,:attempt,0.50256,:cost,CAST(:usage AS jsonb),'settled',:assessment)"
                ),
                {
                    "case": f"export_{n}",
                    "n": n,
                    "study": STUDY,
                    "job": f"old-job-{n}",
                    "attempt": f"old-attempt-{n}",
                    "cost": Decimal(usage["cost_usd"]),
                    "usage": json_value(usage),
                    "assessment": "pass" if n == 0 else None,
                },
            )
    proof = capture_history(store.db.engine, root)
    path = root / "history.json"
    path.write_bytes(canonical(proof))
    approval = {
        "owner_confirmed": True,
        "approved_proposal_sha256": PROPOSAL_SHA,
        "additional_call_proposal_sha256": FOLLOWUP_SHA,
        "history_receipt": str(path),
        "history_sha256": digest(path.read_bytes()),
    }
    return root, approval, proof


def new_study(store, approval):
    manifest = make_manifest(store, approval, [1000] * 3, study_id=FOLLOWUP)
    value = LiveStudy(store, FOLLOWUP)
    value.initialize(manifest)
    return value, manifest


def test_run_identity_is_explicit_and_allowlisted(store):
    with pytest.raises(TypeError):
        LiveStudy(store)
    with pytest.raises(LiveGuard, match="live_study_identity_invalid"):
        LiveStudy(store, "arbitrary-fresh-name")


def test_fresh_database_cannot_create_followup(store):
    with store.db.write() as conn:
        conn.execute(text("DELETE FROM live_calls"))
        conn.execute(text("DELETE FROM live_studies"))
    with pytest.raises(LiveGuard):
        new_study(store, {"owner_confirmed": True, "additional_call_proposal_sha256": FOLLOWUP_SHA})


@pytest.mark.parametrize("change", ["proof", "manifest", "provider", "database", "approval"])
def test_history_mismatch_refuses_activation(store, change):
    root, approval, _ = prior_history(store)
    if change == "proof":
        Path(approval["history_receipt"]).write_text("{}")
    elif change == "manifest":
        (root / "manifest.json").write_text("{}")
    elif change == "provider":
        (root / "provider/old-attempt-1.json").write_text("{}")
    elif change == "database":
        with store.db.write() as conn:
            conn.execute(
                text("UPDATE live_studies SET reason='changed' WHERE id=:id"), {"id": STUDY}
            )
    else:
        approval["additional_call_proposal_sha256"] = "0" * 64
    with pytest.raises(LiveGuard):
        new_study(store, approval)
    assert LiveStudy(store, FOLLOWUP).status()["state"] == "uninitialized"


def test_new_slots_and_global_meter_preserve_old_history(store):
    from test_live_budget import create_job

    from p19.attempts import AttemptStore
    from p19.evidence import lookup

    _, approval, proof = prior_history(store)
    value, manifest = new_study(store, approval)
    jobs = [create_job(store, key=f"new-race-{n}") for n in range(2)]
    calls = [value.prepare(job["failure"], lookup(job["failure"], store)) for job in jobs]

    def reserve(n):
        try:
            return AttemptStore(store).begin(jobs[n]["id"], "owner", live_call=calls[n])
        except LiveGuard:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(reserve, range(2)))
    assert sum(result is not None for result in results) == 1
    status = value.status()
    assert status["consumed_slots"] == 1
    assert Decimal(status["cumulative_known_cost_usd"]) == Decimal("0.0003902")
    assert Decimal(status["cumulative_reserved_usd"]) == Decimal("0.50256")
    assert status["cumulative_consumed_slots"] == 3
    with store.db.engine.connect() as conn:
        assert snapshot(conn) == proof["snapshot"]
    restarted = LiveStudy(store, FOLLOWUP)
    restarted.initialize(manifest)
    attempt = next(result[0] for result in results if result)
    AttemptStore(store).finish(attempt, "unknown")
    assert restarted.status()["state"] == "stopped"
    assert LiveStudy(store, STUDY).status()["reason"] == "job_failed"
    with pytest.raises(LiveGuard):
        restarted.initialize(manifest)
    store.reset()
    assert restarted.status()["consumed_slots"] == 1
    with store.db.engine.connect() as conn:
        assert snapshot(conn) == proof["snapshot"]


def test_changed_history_after_activation_blocks_dispatch(store):
    from test_live_budget import create_job

    from p19.evidence import lookup

    _, approval, _ = prior_history(store)
    value, _ = new_study(store, approval)
    job = create_job(store)
    with store.db.write() as conn:
        conn.execute(text("UPDATE live_studies SET reason='modified' WHERE id=:id"), {"id": STUDY})
    with pytest.raises(LiveGuard):
        value.prepare(job["failure"], lookup(job["failure"], store))


def test_original_cannot_be_activated_outside_checks(store, monkeypatch):
    from p19.evidence import seed

    with store.db.write() as conn:
        conn.execute(text("DELETE FROM live_calls"))
        conn.execute(text("DELETE FROM live_studies"))
    seed(store)
    manifest = make_manifest(store, {"owner_confirmed": True}, [1000] * 3, study_id=STUDY)
    monkeypatch.setenv("P19_PROJECT", "p19-demo")
    with pytest.raises(LiveGuard):
        LiveStudy(store, STUDY).initialize(manifest)


def test_old_schema_migration_is_idempotent_and_keeps_every_row(store):
    from p19.jobs import json_value

    namespace = f"migration_{uuid.uuid4().hex}"
    with store.db.write() as conn:
        conn.execute(text(f"CREATE SCHEMA {namespace}"))
        try:
            conn.execute(text(f"SET LOCAL search_path TO {namespace}"))
            conn.execute(text(Path("tests/fixtures/live_schema_v1.sql").read_text()))
            conn.execute(
                text(
                    "INSERT INTO live_studies(id,manifest,manifest_hash,state) "
                    "VALUES(:id,'{}','original-hash','stopped')"
                ),
                {"id": STUDY},
            )
            conn.execute(
                text(
                    "INSERT INTO live_calls(case_id,ordinal,study_id,job_id,attempt_id,"
                    "reservation_usd,cost_usd,state,assessment,assessment_notes) "
                    "VALUES('export_0',0,:id,'old-job','old-attempt',0.50256,0.0001822,"
                    "'settled','pass','original notes')"
                ),
                {"id": STUDY},
            )
            before = json_value(snapshot(conn))
            for _ in range(2):
                conn.execute(text(Path("src/p19/schema.sql").read_text()))
                assert json_value(snapshot(conn)) == before
            conn.execute(
                text(
                    "INSERT INTO live_studies(id,manifest,manifest_hash,state) "
                    "VALUES(:id,'{}','followup-hash','active')"
                ),
                {"id": FOLLOWUP},
            )
            conn.execute(
                text(
                    "INSERT INTO live_calls(case_id,ordinal,study_id,job_id,attempt_id,"
                    "reservation_usd,state) VALUES('export_0',0,:id,'new-job',"
                    "'new-attempt',0.50256,'reserved')"
                ),
                {"id": FOLLOWUP},
            )
            assert conn.execute(text("SELECT count(*) FROM live_calls")).scalar_one() == 2
        finally:
            conn.execute(text("SET LOCAL search_path TO public"))
            conn.execute(text(f"DROP SCHEMA {namespace} CASCADE"))
