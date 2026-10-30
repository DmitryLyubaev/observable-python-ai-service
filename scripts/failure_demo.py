"""Exercise the public CLI and owned lifecycle boundaries; no application-state writes."""

import json
import os
import selectors
import subprocess
import sys
import time
import uuid
from pathlib import Path

import docker
import redis

from p19.acceptance import manifest, write_once
from p19.jobs import JobStore
from p19.lifecycle import restart_worker

store = JobStore()
client = docker.from_env()
project = os.environ["P19_PROJECT"]
run = Path(".local/runs") / f"failure-demo-{uuid.uuid4().hex}"
run.mkdir(parents=True)
case = json.loads(Path("fixtures/cases.json").read_text())[1]
case_file = run / "case.json"
case_file.write_text(json.dumps(case))
broker = redis.Redis.from_url(os.environ["P19_REDIS_URL"], socket_timeout=3)
results = []


def cli(*arguments):
    completed = subprocess.run(
        [sys.executable, "-m", "p19.cli", *arguments],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    return completed.stdout


def submit():
    return json.loads(
        cli("submit", "--file", str(case_file), "--idempotency-key", uuid.uuid4().hex)
    )


def wait_for(job_id, predicate):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        job = store.get(job_id)
        if predicate(job):
            return job
        time.sleep(0.05)
    raise RuntimeError("demo_checkpoint_timeout")


def at_barrier(job_id, stage):
    return wait_for(
        job_id,
        lambda _: any(
            row["kind"] == "barrier" and row["data"]["stage"] == stage
            for row in store.observations(job_id)
        ),
    )


def replace(*, barrier=None, profile="success"):
    worker = client.containers.get(f"{project}-worker-1")
    worker.stop(timeout=5)
    return restart_worker(worker.id, store, project, barrier=barrier, profile=profile)


# Keep the worker stopped while cancellation wins admission/dispatch.
worker = client.containers.get(f"{project}-worker-1")
worker.stop(timeout=5)
job = submit()
cli("cancel", job["id"])
assert store.get(job["id"])["state"] == "cancelled" and not store.get(job["id"])["attempts"]
results.append({"scenario": "cancel_before_dispatch", "job": store.get(job["id"])})
restart_worker(worker.id, store, project)

# A lost follower is independent of job cancellation; resume from its last event.
replace(barrier="before_dispatch")
job = submit()
at_barrier(job["id"], "before_dispatch")
follower = subprocess.Popen(
    [sys.executable, "-m", "p19.cli", "follow", job["id"]],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
try:
    selector = selectors.DefaultSelector()
    selector.register(follower.stdout, selectors.EVENT_READ)
    assert selector.select(timeout=5)
    last = json.loads(follower.stdout.readline())["sequence"]
finally:
    follower.kill()
    follower.communicate(timeout=5)
assert not store.get(job["id"])["cancel_requested"]
broker.rpush(f"release:{job['id']}", "continue")
progress = cli("follow", job["id"], "--after", str(last))
saved = wait_for(job["id"], lambda row: row["state"] == "succeeded")
assert not saved["cancel_requested"]
(run / "resumed-progress.jsonl").write_text(progress)
results.append({"scenario": "cli_disconnect_and_resume", "job": saved})

# Cancellation after dispatch cannot prove provider processing/billing stopped.
replace(barrier="after_dispatch", profile="timeout")
job = submit()
at_barrier(job["id"], "after_dispatch")
cli("cancel", job["id"])
broker.rpush(f"release:{job['id']}", "continue")
saved = wait_for(job["id"], lambda row: row["state"] == "outcome_unknown")
assert saved["cancel_requested"] and saved["attempts"][0]["usage"] is None
results.append({"scenario": "cancel_after_dispatch_timeout", "job": saved})

for stage, expected in [
    ("before_dispatch", "interrupted"),
    ("after_reply_before_commit", "outcome_unknown"),
]:
    worker = replace(barrier=stage)
    job = submit()
    at_barrier(job["id"], stage)
    worker.kill()
    restart_worker(worker.id, store, project)
    saved = wait_for(job["id"], lambda row: row["state"] == expected)
    results.append({"scenario": f"crash_{stage}", "job": saved})

write_once(
    run / "receipt.json",
    {"manifest": manifest(), "observations": results, "passed_scenarios": len(results)},
)
print(
    json.dumps(
        {"failure_demo": "passed", "scenarios": len(results), "receipt": str(run / "receipt.json")}
    )
)
