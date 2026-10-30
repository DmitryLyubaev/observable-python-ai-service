"""One immutable three-case allowance, sharing the existing dispatch transaction."""

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

from p19.acceptance import source_digest
from p19.claude import API_VERSION, MAX_OUTPUT, MODEL, build_request, canonical, priced_usage
from p19.contracts import FailureRecord
from p19.evidence import lookup
from p19.jobs import json_value

STUDY = "p19-real-20261030"
RESERVATION = Decimal("0.50256")
PROPOSAL_SHA = "e65ebcd6cf3ed79f3b85a815c0846ba3ed6e1d22ea5929fd18ecde7c223395a6"
FIXTURE_HASHES = {
    "cases.json": "34320becd7802404c2d674ffbda2de649235e03c2319490ea26ad4366f92c75f",
    "evidence.json": "8643ffa1ccd3527c08c0431bd9f754fb4fa0f803124bbdf6edea156f84f4f399",
}
CONFIG = {
    "model": MODEL,
    "api_version": API_VERSION,
    "cap_usd": "2",
    "reservation_usd": "0.50256",
    "max_output_tokens": MAX_OUTPUT,
    "max_input_estimate": 4096,
    "provider_seconds": 10,
    "job_seconds": 30,
    "input_usd_per_million": "0.10",
    "output_usd_per_million": "0.50",
    "high_input_usd_per_million": "0.50",
    "high_output_usd_per_million": "2.50",
    "rates_checked": "2026-10-30",
    "max_calls": 3,
    "automatic_retries": 0,
}


class LiveGuard(Exception):
    pass


def digest(value):
    return hashlib.sha256(value).hexdigest()


def overlay_digest():
    path = Path("compose.live.yaml")
    return digest(path.read_bytes()) if path.exists() else None


def fixture_cases():
    for name, expected in FIXTURE_HASHES.items():
        if digest((Path("fixtures") / name).read_bytes()) != expected:
            raise LiveGuard("live_fixture_changed")
    return [
        FailureRecord.model_validate(row).model_dump(mode="json")
        for row in json.loads(Path("fixtures/cases.json").read_text())
    ]


def make_manifest(store, approval, counts):
    if (
        approval.get("owner_confirmed") is not True
        or len(counts) != 3
        or any(type(n) is not int or not 0 <= n <= 4096 for n in counts)
    ):
        raise LiveGuard("live_preflight_invalid")
    fixture_evidence = json.loads(Path("fixtures/evidence.json").read_text())
    cases = []
    for record, count in zip(fixture_cases(), counts, strict=True):
        evidence = lookup(record, store)
        expected = [
            {
                "id": row["id"],
                "export_id": row["export_id"],
                "sale_id": row["sale_id"],
                "fact": row["fact"],
            }
            for row in fixture_evidence
            if row["export_id"] == record["export_id"] and row["sale_id"] == record["sale_id"]
        ]
        if evidence["records"] != expected:
            raise LiveGuard("live_evidence_changed")
        payload = build_request(record, evidence)
        cases.append(
            {
                "case_id": record["export_id"],
                "record_hash": digest(canonical(record)),
                "payload": payload.decode(),
                "payload_hash": digest(payload),
                "input_estimate": count,
            }
        )
    return {
        "study_id": STUDY,
        "configuration": CONFIG.copy(),
        "source_digest": source_digest(),
        "overlay_sha256": overlay_digest(),
        "approval": {
            "approved_proposal_sha256": PROPOSAL_SHA,
            **approval,
        },
        "cases": cases,
    }


@dataclass(frozen=True)
class PreparedLiveCall:
    study_id: str
    case_id: str
    payload: bytes
    payload_hash: str
    configuration_hash: str


class LiveStudy:
    def __init__(self, store):
        self.store = store

    def initialize(self, manifest):
        if (
            manifest.get("study_id") != STUDY
            or manifest.get("configuration") != CONFIG
            or manifest.get("approval", {}).get("approved_proposal_sha256") != PROPOSAL_SHA
        ):
            raise LiveGuard("live_manifest_invalid")
        expected = make_manifest(
            self.store, manifest["approval"], [row["input_estimate"] for row in manifest["cases"]]
        )
        if manifest != expected:
            raise LiveGuard("live_manifest_changed")
        identity = digest(canonical(manifest))
        with self.store.db.write() as conn:
            row = (
                conn.execute(text("SELECT * FROM live_studies WHERE id=:id"), {"id": STUDY})
                .mappings()
                .first()
            )
            if row:
                if row["manifest_hash"] != identity or row["state"] != "active":
                    raise LiveGuard("live_study_already_used")
                return
            conn.execute(
                text(
                    "INSERT INTO live_studies(id,manifest,manifest_hash,state) VALUES(:id,CAST(:manifest AS jsonb),:hash,'active')"
                ),
                {"id": STUDY, "manifest": json_value(manifest), "hash": identity},
            )

    def prepare(self, record, evidence):
        with self.store.db.engine.connect() as conn:
            row = (
                conn.execute(text("SELECT * FROM live_studies WHERE id=:id"), {"id": STUDY})
                .mappings()
                .first()
            )
        if not row or row["state"] != "active":
            raise LiveGuard("live_study_inactive")
        manifest = row["manifest"]
        if (
            source_digest() != manifest["source_digest"]
            or overlay_digest() != manifest["overlay_sha256"]
        ):
            raise LiveGuard("live_source_changed")
        payload = build_request(record, evidence)
        match = [
            case for case in manifest["cases"] if case["record_hash"] == digest(canonical(record))
        ]
        if len(match) != 1 or match[0]["payload_hash"] != digest(payload):
            raise LiveGuard("live_case_not_frozen")
        return PreparedLiveCall(
            STUDY, match[0]["case_id"], payload, digest(payload), row["manifest_hash"]
        )

    def stop(self, reason):
        with self.store.db.write() as conn:
            conn.execute(
                text(
                    "UPDATE live_studies SET state='stopped',reason=:reason WHERE id=:id AND state='active'"
                ),
                {"id": STUDY, "reason": reason},
            )

    def require_preflight(self):
        manifest = self.status()["manifest"]
        if not manifest:
            raise LiveGuard("live_preflight_missing")
        approval = manifest["approval"]
        try:
            path = Path(approval["preflight_receipt"]).resolve()
            if not path.is_relative_to(Path(".local").resolve()):
                raise LiveGuard("live_preflight_path_invalid")
            raw = path.read_bytes()
            receipt = json.loads(raw)
            if (
                digest(raw) != approval["preflight_sha256"]
                or receipt["status"] != "passed"
                or receipt["model"] != MODEL
                or receipt["source_digest"] != manifest["source_digest"]
                or receipt["counts"] != [row["input_estimate"] for row in manifest["cases"]]
            ):
                raise LiveGuard("live_preflight_changed")
        except (KeyError, OSError, ValueError, TypeError):
            raise LiveGuard("live_preflight_unverified") from None

    def assess(self, case_id, decision, notes):
        if (
            decision not in {"pass", "fail"}
            or not isinstance(notes, str)
            or not 1 <= len(notes) <= 4096
        ):
            raise LiveGuard("live_assessment_invalid")
        with self.store.db.write() as conn:
            study = conn.execute(
                text("SELECT state FROM live_studies WHERE id=:id"), {"id": STUDY}
            ).scalar_one_or_none()
            row = (
                conn.execute(text("SELECT * FROM live_calls WHERE case_id=:id"), {"id": case_id})
                .mappings()
                .first()
            )
            if study != "active" or not row or row["state"] != "settled" or row["assessment"]:
                raise LiveGuard("live_assessment_not_ready")
            state = conn.execute(
                text("SELECT state FROM jobs WHERE id=:id"), {"id": row["job_id"]}
            ).scalar_one_or_none()
            if state != "succeeded":
                raise LiveGuard("live_case_not_successful")
            conn.execute(
                text(
                    "UPDATE live_calls SET assessment=:decision,assessment_notes=:notes WHERE case_id=:id"
                ),
                {"decision": decision, "notes": notes, "id": case_id},
            )
            if decision == "fail":
                conn.execute(
                    text(
                        "UPDATE live_studies SET state='stopped',reason='assistant_assessment_failed' WHERE id=:id"
                    ),
                    {"id": STUDY},
                )
            elif row["ordinal"] == 2:
                conn.execute(
                    text("UPDATE live_studies SET state='completed' WHERE id=:id"), {"id": STUDY}
                )

    def status(self):
        with self.store.db.engine.connect() as conn:
            study = (
                conn.execute(text("SELECT * FROM live_studies WHERE id=:id"), {"id": STUDY})
                .mappings()
                .first()
            )
            calls = [
                dict(row)
                for row in conn.execute(
                    text("SELECT * FROM live_calls ORDER BY ordinal")
                ).mappings()
            ]
        return {
            "study_id": STUDY,
            "state": study["state"] if study else "uninitialized",
            "reason": study["reason"] if study else None,
            "cap_usd": "2",
            "consumed_slots": len(calls),
            "known_cost_usd": str(
                sum((row["cost_usd"] or Decimal(0) for row in calls), Decimal(0))
            ),
            "reserved_usd": str(
                sum(
                    (row["reservation_usd"] for row in calls if row["cost_usd"] is None), Decimal(0)
                )
            ),
            "manifest": study["manifest"] if study else None,
            "calls": calls,
        }


def reserve(conn, job_id, attempt_id, call):
    study = (
        conn.execute(text("SELECT * FROM live_studies WHERE id=:id"), {"id": STUDY})
        .mappings()
        .first()
    )
    if (
        not study
        or study["state"] != "active"
        or call.study_id != STUDY
        or study["manifest_hash"] != call.configuration_hash
    ):
        raise LiveGuard("live_permission_unavailable")
    cases = study["manifest"]["cases"]
    indexes = [
        n
        for n, case in enumerate(cases)
        if case["case_id"] == call.case_id
        and case["payload_hash"] == digest(call.payload) == call.payload_hash
    ]
    if len(indexes) != 1:
        raise LiveGuard("live_case_not_frozen")
    ordinal = indexes[0]
    rows = list(conn.execute(text("SELECT * FROM live_calls ORDER BY ordinal")).mappings())
    if len(rows) != ordinal or any(
        row["state"] != "settled" or row["assessment"] != "pass" for row in rows
    ):
        raise LiveGuard("live_case_order_or_slot")
    used = sum(
        (
            row["cost_usd"] if row["cost_usd"] is not None else row["reservation_usd"]
            for row in rows
        ),
        Decimal(0),
    )
    if used + RESERVATION > Decimal("2"):
        raise LiveGuard("live_allowance_exhausted")
    conn.execute(
        text(
            "INSERT INTO live_calls(case_id,ordinal,study_id,job_id,attempt_id,reservation_usd,state) VALUES(:case,:ordinal,:study,:job,:attempt,:reserve,'reserved')"
        ),
        {
            "case": call.case_id,
            "ordinal": ordinal,
            "study": STUDY,
            "job": job_id,
            "attempt": attempt_id,
            "reserve": RESERVATION,
        },
    )


def settle(conn, attempt_id, usage, *, definitely_not_processed=False):
    row = (
        conn.execute(text("SELECT * FROM live_calls WHERE attempt_id=:id"), {"id": attempt_id})
        .mappings()
        .first()
    )
    if not row:
        return
    if row["state"] != "reserved":
        raise LiveGuard("live_accounting_already_settled")
    valid = None
    if usage and usage.get("provenance") == "provider":
        valid = priced_usage(
            {
                "model": usage.get("model"),
                "usage": {
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "output_tokens_details": {
                        "thinking_tokens": usage.get("thinking_tokens_included", 0)
                    },
                },
            }
        )
        if not valid or valid != usage:
            valid = None
    if valid or definitely_not_processed:
        cost = Decimal(valid["cost_usd"]) if valid else Decimal(0)
        conn.execute(
            text(
                "UPDATE live_calls SET state=:state,cost_usd=:cost,usage=CAST(:usage AS jsonb) WHERE attempt_id=:id"
            ),
            {
                "id": attempt_id,
                "state": "settled" if valid else "rejected",
                "cost": cost,
                "usage": json_value(valid),
            },
        )
    else:
        conn.execute(
            text(
                "UPDATE live_studies SET state='stopped',reason='unknown_provider_usage' WHERE id=:id AND state='active'"
            ),
            {"id": STUDY},
        )
