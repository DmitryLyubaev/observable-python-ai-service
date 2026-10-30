from conftest import record


def test_failed_dispatch_commit_prevents_call(store):
    from p19.runner import run_job

    job = store.admit(record(), "dispatch_fault")
    run_job(job["id"], "worker", store=store, fault="dispatch")
    assert not store.get(job["id"])["attempts"]
    assert not [x for x in store.observations(job["id"]) if x["kind"] == "provider_start"]


def test_unsaved_reply_remains_unknown(store):
    from p19.runner import run_job

    job = store.admit(record(), "reply_fault")
    run_job(job["id"], "worker", store=store, fault="result")
    assert store.get(job["id"])["state"] == "outcome_unknown"
    assert store.get(job["id"])["attempts"][0]["usage"] is None
