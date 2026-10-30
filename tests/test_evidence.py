import json

from conftest import record
from sqlalchemy import text


def test_exact_export_identity_controls_receiver_outcome(store):
    from p19.evidence import lookup, seed

    seed(store)
    assert [lookup(record(n), store)["receiver_outcome"] for n in range(3)] == [
        "rejected",
        "received",
        "unresolved",
    ]
    other = record(1)
    other["sale_id"] = "different"
    assert lookup(other, store)["receiver_outcome"] == "unresolved"
    seed(store)
    assert len(lookup(record(1), store)["records"]) == 1


def test_lookup_bindings_reach_frozen_request(store):
    from p19.claude import build_request
    from p19.evidence import lookup, seed
    from p19.live import fixture_cases, make_manifest

    seed(store)
    failure = fixture_cases()[1]
    foreign = [
        {"id": "test_foreign_sale", "export_id": "export_1", "sale_id": "sale_foreign"},
        {"id": "test_foreign_export", "export_id": "export_foreign", "sale_id": "sale_1"},
    ]
    try:
        with store.db.write() as conn:
            for row in foreign:
                conn.execute(
                    text(
                        "INSERT INTO evidence_records(id,export_id,sale_id,fact) "
                        'VALUES(:id,:export_id,:sale_id,\'{"kind":"receipt"}\'::jsonb)'
                    ),
                    row,
                )
        evidence = lookup(failure, store)
        expected = [
            {
                "id": "ev_receipt",
                "export_id": "export_1",
                "sale_id": "sale_1",
                "fact": {"kind": "receipt", "receiver_reference": "receipt_101"},
            }
        ]
        assert evidence["records"] == expected
        evidence["receiver_outcome"] = "REFERENCE_CANARY"
        payload = build_request(failure, evidence)
        manifest = make_manifest(store, {"owner_confirmed": True}, [1000] * 3)
        assert manifest["cases"][1]["payload"] == payload.decode()
        supplied = json.loads(json.loads(payload)["messages"][0]["content"])
        assert supplied == {"failure": failure, "records": expected}
        assert b"REFERENCE_CANARY" not in payload
    finally:
        with store.db.write() as conn:
            for row in foreign:
                conn.execute(text("DELETE FROM evidence_records WHERE id=:id"), {"id": row["id"]})
