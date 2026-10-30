from conftest import record


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
