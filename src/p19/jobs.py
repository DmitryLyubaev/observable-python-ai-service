import hashlib
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text

from p19.config import database_url
from p19.contracts import TERMINAL, FailureRecord
from p19.db import Database


class AdmissionFull(Exception):
    pass


class KeyConflict(Exception):
    pass


class JobNotFound(Exception):
    pass


class TerminalConflict(Exception):
    pass


def json_value(value):
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


def event(conn, job_id, kind, data=None):
    seq = conn.execute(
        text(
            "UPDATE jobs SET sequence=sequence+1, updated_at=clock_timestamp() WHERE id=:id RETURNING sequence"
        ),
        {"id": job_id},
    ).scalar_one()
    conn.execute(
        text(
            "INSERT INTO events(job_id,sequence,kind,data) VALUES(:id,:seq,:kind,CAST(:data AS jsonb))"
        ),
        {"id": job_id, "seq": seq, "kind": kind, "data": json_value(data or {})},
    )


class JobStore:
    def __init__(self, url=None):
        self.url = url or database_url()
        self.db = Database(self.url)

    def reset(self):
        if os.environ.get("P19_TEST") != "1":
            raise RuntimeError("test_reset_disabled")
        with self.db.write() as conn:
            conn.execute(text("TRUNCATE events,attempts,jobs,observations CASCADE"))

    def admit(self, record, key, trace_context=None):
        record = FailureRecord.model_validate(record).model_dump(mode="json")
        if not isinstance(key, str) or not 1 <= len(key) <= 128:
            raise ValueError("invalid_key")
        digest = hashlib.sha256(json_value(record).encode()).hexdigest()
        with self.db.write() as conn:
            previous = (
                conn.execute(
                    text("SELECT id,body_hash FROM jobs WHERE idempotency_key=:key"), {"key": key}
                )
                .mappings()
                .first()
            )
            if previous:
                if previous["body_hash"] != digest:
                    raise KeyConflict("key_conflict")
                job_id = previous["id"]
            else:
                count = conn.execute(
                    text(
                        "SELECT count(*) FROM jobs WHERE state IN ('queued','preparing','calling')"
                    )
                ).scalar_one()
                if count >= 8:
                    raise AdmissionFull("admission_full")
                job_id = str(uuid4())
                conn.execute(
                    text(
                        "INSERT INTO jobs(id,idempotency_key,body_hash,state,failure,trace_context) VALUES(:id,:key,:hash,'queued',CAST(:failure AS jsonb),CAST(:trace AS jsonb))"
                    ),
                    {
                        "id": job_id,
                        "key": key,
                        "hash": digest,
                        "failure": json_value(record),
                        "trace": json_value(trace_context or {}),
                    },
                )
                event(conn, job_id, "queued")
        return self.get(job_id)

    def get(self, job_id):
        with self.db.engine.connect() as conn:
            value = (
                conn.execute(text("SELECT * FROM jobs WHERE id=:id"), {"id": str(job_id)})
                .mappings()
                .first()
            )
            if not value:
                raise JobNotFound("job_not_found")
            value = dict(value)
            value["attempts"] = [
                dict(x)
                for x in conn.execute(
                    text("SELECT * FROM attempts WHERE job_id=:id ORDER BY number"),
                    {"id": str(job_id)},
                ).mappings()
            ]
            return value

    def all(self):
        with self.db.engine.connect() as conn:
            ids = list(conn.execute(text("SELECT id FROM jobs ORDER BY created_at")).scalars())
        return [self.get(x) for x in ids]

    def events_after(self, job_id, sequence, limit=100):
        self.get(job_id)
        with self.db.engine.connect() as conn:
            return [
                dict(x)
                for x in conn.execute(
                    text(
                        "SELECT * FROM events WHERE job_id=:id AND sequence>:seq ORDER BY sequence LIMIT :limit"
                    ),
                    {"id": str(job_id), "seq": sequence, "limit": min(limit, 100)},
                ).mappings()
            ]

    def claim(self, job_id, worker_instance_id, fault=False):
        with self.db.write() as conn:
            row = conn.execute(
                text(
                    "UPDATE jobs SET state='preparing',worker_instance_id=:owner,claimed_at=clock_timestamp() WHERE id=:id AND state='queued' AND created_at>clock_timestamp()-interval '60 seconds' RETURNING id"
                ),
                {"id": str(job_id), "owner": worker_instance_id},
            ).first()
            if not row:
                return None
            event(conn, str(job_id), "preparing")
            if fault:
                raise RuntimeError("injected")
        return self.get(job_id)

    def cancel(self, job_id):
        with self.db.write() as conn:
            job = conn.execute(
                text("SELECT state FROM jobs WHERE id=:id"), {"id": str(job_id)}
            ).scalar_one_or_none()
            if job is None:
                raise JobNotFound("job_not_found")
            if job in TERMINAL and job != "cancelled":
                raise TerminalConflict("terminal_conflict")
            if job != "cancelled":
                state = "cancelled" if job in {"queued", "preparing"} else "calling"
                conn.execute(
                    text("UPDATE jobs SET state=:state,cancel_requested=true WHERE id=:id"),
                    {"id": str(job_id), "state": state},
                )
                event(conn, str(job_id), "cancellation_requested", {"state": state})
        return self.get(job_id)

    def finish(self, job_id, owner, state, error=None, result=None):
        with self.db.write() as conn:
            row = (
                conn.execute(
                    text(
                        "SELECT state,cancel_requested FROM jobs WHERE id=:id AND worker_instance_id=:owner"
                    ),
                    {"id": str(job_id), "owner": owner},
                )
                .mappings()
                .first()
            )
            if not row or row["state"] in TERMINAL:
                return False
            if row["cancel_requested"] and state != "outcome_unknown":
                state, result = "cancelled", None
            conn.execute(
                text(
                    "UPDATE jobs SET state=:state,error=:error,result=CAST(:result AS jsonb) WHERE id=:id"
                ),
                {"id": str(job_id), "state": state, "error": error, "result": json_value(result)},
            )
            event(conn, str(job_id), state)
        return True

    def observe(self, job_id, kind, data=None):
        with self.db.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO observations(job_id,kind,data) VALUES(:id,:kind,CAST(:data AS jsonb))"
                ),
                {"id": str(job_id), "kind": kind, "data": json_value(data or {})},
            )

    def observations(self, job_id=None):
        with self.db.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM observations WHERE (:id IS NULL OR job_id=:id) ORDER BY id"),
                {"id": job_id},
            ).mappings()
            return [dict(row) for row in rows]

    def reserve_publication(self, job_id, now=None):
        now = now or datetime.now(timezone.utc)
        with self.db.write() as conn:
            row = (
                conn.execute(text("SELECT * FROM jobs WHERE id=:id"), {"id": str(job_id)})
                .mappings()
                .one()
            )
            if row["state"] != "queued":
                return None
            if (now - row["created_at"]).total_seconds() >= 60:
                conn.execute(
                    text("UPDATE jobs SET state='failed',error='queue_expired' WHERE id=:id"),
                    {"id": str(job_id)},
                )
                event(conn, str(job_id), "failed", {"reason": "queue_expired"})
                return None
            if row["publications"] >= 3 or (
                row["last_publication_at"]
                and (now - row["last_publication_at"]).total_seconds() < 5
            ):
                return None
            conn.execute(
                text(
                    "UPDATE jobs SET publications=publications+1,last_publication_at=:now WHERE id=:id"
                ),
                {"id": str(job_id), "now": now},
            )
            event(conn, str(job_id), "publication_reserved")
            return dict(row)
