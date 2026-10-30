import pytest
from conftest import record


@pytest.mark.parametrize(
    "stage,count,state",
    [
        ("before_dispatch", 0, "cancelled"),
        ("after_dispatch", 1, "cancelled"),
        ("after_reply_before_commit", 1, "cancelled"),
        ("between_attempts", 1, "cancelled"),
    ],
)
def test_cancel_and_result_serialize(store, stage, count, state):
    from p19.runner import run_job

    job = store.admit(record(), "cancel")

    def hook(name):
        if name == stage:
            store.cancel(job["id"])

    run_job(
        job["id"],
        "worker",
        store=store,
        profile="rate_then_success" if stage == "between_attempts" else "success",
        hook=hook,
    )
    saved = store.get(job["id"])
    assert saved["state"] == state
    assert saved["result"] is None
    assert len(saved["attempts"]) == count


def test_success_winning_cancel_race_conflicts(store):
    from p19.runner import run_job

    job = store.admit(record(), "winner")
    run_job(job["id"], "worker", store=store)
    with pytest.raises(Exception, match="terminal_conflict"):
        store.cancel(job["id"])
