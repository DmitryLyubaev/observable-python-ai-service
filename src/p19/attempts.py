from uuid import uuid4

from sqlalchemy import text

from p19.jobs import event, json_value


class AttemptStore:
    def __init__(self, jobs):
        self.jobs = jobs

    def begin(self, job_id, owner, fault=False):
        with self.jobs.db.write() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM jobs WHERE id=:id AND worker_instance_id=:owner"),
                    {"id": job_id, "owner": owner},
                )
                .mappings()
                .one()
            )
            if row["state"] != "preparing" or row["cancel_requested"]:
                return None
            number = conn.execute(
                text("SELECT count(*)+1 FROM attempts WHERE job_id=:id"), {"id": job_id}
            ).scalar_one()
            if number > 2:
                return None
            attempt_id = str(uuid4())
            conn.execute(
                text(
                    "INSERT INTO attempts(id,job_id,number,state) VALUES(:id,:job,:number,'unknown')"
                ),
                {"id": attempt_id, "job": job_id, "number": number},
            )
            conn.execute(text("UPDATE jobs SET state='calling' WHERE id=:id"), {"id": job_id})
            event(conn, job_id, "dispatch_intent", {"attempt_id": attempt_id, "number": number})
            if fault:
                raise RuntimeError("dispatch_commit_fault")
        return attempt_id, number

    def finish(self, attempt_id, state, usage=None, duration=None):
        with self.jobs.db.write() as conn:
            conn.execute(
                text(
                    "UPDATE attempts SET state=:state,usage=CAST(:usage AS jsonb),finished_at=clock_timestamp(),duration_seconds=:duration WHERE id=:id"
                ),
                {
                    "id": attempt_id,
                    "state": state,
                    "usage": json_value(usage),
                    "duration": duration,
                },
            )

    def retry_ready(self, job_id, owner):
        with self.jobs.db.write() as conn:
            row = conn.execute(
                text(
                    "UPDATE jobs SET state='preparing' WHERE id=:id AND worker_instance_id=:owner AND state='calling' AND NOT cancel_requested RETURNING id"
                ),
                {"id": job_id, "owner": owner},
            ).first()
            if row:
                event(conn, job_id, "retry_wait")
            return bool(row)
