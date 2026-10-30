import pytest
from conftest import record


@pytest.mark.parametrize(
    "profile,state,count",
    [
        ("success", "succeeded", 1),
        ("rate_then_success", "succeeded", 2),
        ("rate_exhausted", "failed", 2),
        ("long_retry", "failed", 1),
        ("timeout", "outcome_unknown", 1),
        ("ambiguous_5xx", "outcome_unknown", 1),
        ("rejected", "failed", 1),
        ("malformed", "failed", 1),
        ("lookup_timeout", "failed", 0),
    ],
)
def test_provider_failure_dispositions(store, profile, state, count):
    from p19.runner import run_job

    job = store.admit(record(), "run")
    run_job(job["id"], "worker", store=store, profile=profile)
    saved = store.get(job["id"])
    assert saved["state"] == state
    assert len(saved["attempts"]) == count
    assert len([x for x in store.observations(job["id"]) if x["kind"] == "provider_start"]) == count
    if state == "outcome_unknown":
        assert saved["attempts"][0]["usage"] is None


def test_duplicate_delivery_has_one_invocation(store):
    from p19.runner import run_job

    job = store.admit(record(), "duplicate")
    run_job(job["id"], "worker", store=store)
    run_job(job["id"], "worker", store=store)
    assert len(store.get(job["id"])["attempts"]) == 1
