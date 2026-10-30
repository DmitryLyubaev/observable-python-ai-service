import time

from conftest import record


def test_real_celery_duplicate_messages_have_one_call(store):
    from p19.broker import publish

    job = store.admit(record(), "real_worker")
    publish(job["id"], {})
    publish(job["id"], {})
    until = time.monotonic() + 15
    while time.monotonic() < until:
        saved = store.get(job["id"])
        if saved["state"] == "succeeded":
            break
        time.sleep(0.1)
    assert saved["state"] == "succeeded"
    time.sleep(0.3)
    assert len(store.get(job["id"])["attempts"]) == 1
    assert len([x for x in store.observations(job["id"]) if x["kind"] == "provider_start"]) == 1
