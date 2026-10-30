from sqlalchemy import text

from p19.jobs import event


def recover_worker(store, stopped_instance_id):
    changed = []
    with store.db.write() as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT id,state FROM jobs WHERE worker_instance_id=:owner AND state IN ('preparing','calling')"
                ),
                {"owner": stopped_instance_id},
            )
            .mappings()
            .all()
        )
        for row in rows:
            state = "interrupted" if row["state"] == "preparing" else "outcome_unknown"
            conn.execute(
                text("UPDATE jobs SET state=:state,error='worker_stopped' WHERE id=:id"),
                {"id": row["id"], "state": state},
            )
            event(conn, row["id"], state, {"reason": "verified_worker_stopped"})
            conn.execute(
                text(
                    "UPDATE live_studies SET state='stopped',reason='worker_stopped' "
                    "WHERE state='active' AND id IN "
                    "(SELECT study_id FROM live_calls WHERE job_id=:job)"
                ),
                {"job": row["id"]},
            )
            changed.append(row["id"])
    return changed
