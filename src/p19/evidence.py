import json
from pathlib import Path

from sqlalchemy import text

from p19.jobs import json_value


def seed(store):
    records = json.loads(Path("fixtures/evidence.json").read_text())
    with store.db.write() as conn:
        for record in records:
            conn.execute(
                text(
                    "INSERT INTO evidence_records(id,export_id,sale_id,fact) VALUES(:id,:export_id,:sale_id,CAST(:fact AS jsonb)) ON CONFLICT(id) DO NOTHING"
                ),
                {**record, "fact": json_value(record["fact"])},
            )


def lookup(record, store):
    with store.db.engine.begin() as conn:
        conn.execute(text("SET LOCAL statement_timeout='2s'"))
        records = [
            dict(row)
            for row in conn.execute(
                text(
                    "SELECT id,export_id,sale_id,fact FROM evidence_records WHERE export_id=:export_id AND sale_id=:sale_id ORDER BY id LIMIT 8"
                ),
                record,
            ).mappings()
        ]
    kinds = {row["fact"]["kind"] for row in records}
    outcome = (
        "received" if "receipt" in kinds else "rejected" if "rejection" in kinds else "unresolved"
    )
    return {"receiver_outcome": outcome, "records": records}
