import pytest
from conftest import record


def test_state_and_event_rollback_together(store):
    job = store.admit(record(), "rollback")
    before = store.events_after(job["id"], 0)
    with pytest.raises(RuntimeError, match="injected"):
        store.claim(job["id"], "worker", fault=True)
    assert store.get(job["id"])["state"] == "queued"
    assert store.events_after(job["id"], 0) == before
    assert type(store)(store.url).get(job["id"])["id"] == job["id"]
