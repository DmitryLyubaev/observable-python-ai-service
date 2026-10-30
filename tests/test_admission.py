from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import record


def test_concurrent_admission_and_lost_response_retry(store):
    def admit(n):
        try:
            return store.admit(record(n), f"key{n}")["id"]
        except Exception as exc:
            assert type(exc).__name__ == "AdmissionFull"
            return None

    with ThreadPoolExecutor(max_workers=12) as pool:
        ids = [x for x in pool.map(admit, range(12)) if x]
    assert len(set(ids)) == 8
    original = store.get(ids[0])
    assert store.admit(original["failure"], original["idempotency_key"])["id"] == ids[0]
    with pytest.raises(Exception, match="key_conflict"):
        store.admit(record(99), original["idempotency_key"])


def test_simultaneous_same_key_has_one_identity(store):
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda _: store.admit(record(), "same")["id"], range(8)))
    assert len(set(ids)) == 1
    assert len(store.all()) == 1
