import os
import time

import docker
import pytest
from conftest import record


def await_barrier(store, job_id, stage):
    until = time.monotonic() + 15
    while time.monotonic() < until:
        observations = store.observations(job_id)
        if any(x["kind"] == "barrier" and x["data"]["stage"] == stage for x in observations):
            return
        time.sleep(0.05)
    raise AssertionError("barrier_not_reached")


@pytest.mark.parametrize(
    "stage,expected",
    [
        ("before_dispatch", "interrupted"),
        ("after_dispatch", "outcome_unknown"),
        ("after_reply_before_commit", "outcome_unknown"),
    ],
)
def test_actual_owned_worker_crash_preserves_no_replay(store, stage, expected):
    from p19.broker import publish
    from p19.lifecycle import restart_worker

    project = os.environ["P19_PROJECT"]
    client = docker.from_env()
    worker = client.containers.get(f"{project}-worker-1")
    worker.kill()
    worker = restart_worker(worker.id, store, project, barrier=stage)
    try:
        job = store.admit(record(), "crash")
        publish(job["id"], {})
        await_barrier(store, job["id"], stage)
        calls_before = len(
            [x for x in store.observations(job["id"]) if x["kind"] == "provider_start"]
        )
        if stage == "after_dispatch":
            store.cancel(job["id"])
        worker.kill()
        worker = restart_worker(worker.id, store, project)
        assert store.get(job["id"])["state"] == expected
        publish(job["id"], {})
        followup = store.admit(record(1), "followup")
        publish(followup["id"], {})
        until = time.monotonic() + 15
        while store.get(followup["id"])["state"] != "succeeded" and time.monotonic() < until:
            time.sleep(0.05)
        assert store.get(followup["id"])["state"] == "succeeded"
        assert (
            len([x for x in store.observations(job["id"]) if x["kind"] == "provider_start"])
            == calls_before
        )
        if stage == "after_dispatch":
            assert store.get(job["id"])["cancel_requested"]
    finally:
        worker.reload()
        if worker.status == "running":
            worker.kill()
        restart_worker(worker.id, store, project)
