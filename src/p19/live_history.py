"""Read-only reconciliation of the original stopped study and retained provider evidence."""

import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

from p19.claude import canonical, priced_usage
from p19.jobs import json_value
from p19.live import PROPOSAL_SHA, STUDY, LiveGuard, digest


def original_snapshot(conn):
    study = (
        conn.execute(text("SELECT * FROM live_studies WHERE id=:id"), {"id": STUDY})
        .mappings()
        .first()
    )
    calls = (
        conn.execute(
            text("SELECT * FROM live_calls WHERE study_id=:id ORDER BY ordinal"), {"id": STUDY}
        )
        .mappings()
        .all()
    )
    return json.loads(
        json_value({"study": dict(study) if study else None, "calls": [dict(row) for row in calls]})
    )


def local_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(Path(".local").resolve()):
        raise LiveGuard("live_history_path_invalid")
    return path


def capture_history(engine, root):
    """Does not instantiate JobStore or execute DDL; safe before the additive migration."""
    try:
        root = local_path(root)
        with engine.connect() as conn:
            snapshot = original_snapshot(conn)
        study, calls = snapshot["study"], snapshot["calls"]
        if not study or study["state"] != "stopped" or len(calls) != 2:
            raise LiveGuard("live_original_history_invalid")
        manifest_path = root / "manifest.json"
        raw_manifest = manifest_path.read_bytes()
        manifest = json.loads(raw_manifest)
        if (
            manifest != study["manifest"]
            or digest(canonical(manifest)) != study["manifest_hash"]
            or manifest["study_id"] != STUDY
            or manifest["approval"]["approved_proposal_sha256"] != PROPOSAL_SHA
        ):
            raise LiveGuard("live_original_manifest_mismatch")
        files = {"manifest.json": digest(raw_manifest)}
        total = Decimal(0)
        for n, row in enumerate(calls):
            if (
                row["ordinal"] != n
                or row["case_id"] != f"export_{n}"
                or row["state"] != "settled"
                or row["cost_usd"] is None
                or row["assessment"] != ("pass" if n == 0 else None)
            ):
                raise LiveGuard("live_original_calls_invalid")
            name = f"provider/{row['attempt_id']}.json"
            receipt = local_path(root / name).read_bytes()
            usage = priced_usage(json.loads(receipt)["body"])
            if (
                not usage
                or usage != row["usage"]
                or Decimal(usage["cost_usd"]) != Decimal(row["cost_usd"])
            ):
                raise LiveGuard("live_original_usage_mismatch")
            total += Decimal(usage["cost_usd"])
            files[name] = digest(receipt)
        if total != Decimal("0.0003902"):
            raise LiveGuard("live_original_total_mismatch")
        return {"snapshot": snapshot, "root": str(root.relative_to(Path.cwd())), "files": files}
    except (OSError, KeyError, ValueError, TypeError):
        raise LiveGuard("live_original_evidence_unverified") from None


def verify_history(engine, approval):
    try:
        raw = local_path(approval["history_receipt"]).read_bytes()
        proof = json.loads(raw)
        if (
            digest(raw) != approval["history_sha256"]
            or capture_history(engine, proof["root"]) != proof
        ):
            raise LiveGuard("live_original_history_changed")
        return digest(canonical(proof["snapshot"]))
    except (OSError, KeyError, ValueError, TypeError):
        raise LiveGuard("live_original_history_unverified") from None


def check_snapshot(conn, expected):
    if digest(canonical(original_snapshot(conn))) != expected:
        raise LiveGuard("live_original_history_changed")
