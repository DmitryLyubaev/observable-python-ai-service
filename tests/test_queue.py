from datetime import timedelta

from conftest import record


def test_publication_reservations_survive_redis_failure(store):
    from p19.dispatcher import Dispatcher

    job = store.admit(record(), "queue")

    def unavailable(*args):
        raise ConnectionError("synthetic")

    dispatcher = Dispatcher(store, unavailable)
    now = job["created_at"]
    for seconds in [0, 1, 5, 6, 10, 15]:
        dispatcher.tick(now + timedelta(seconds=seconds))
    assert store.get(job["id"])["publications"] == 3
    dispatcher.tick(now + timedelta(seconds=60))
    assert store.get(job["id"])["error"] == "queue_expired"
    assert store.claim(job["id"], "late") is None
