import argparse
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import docker
import httpx

from p19.acceptance import manifest, write_once
from p19.jobs import JobStore
from p19.lifecycle import restart_worker
from p19.reporting import build_summary, distribution


def max_overlap(intervals):
    events = sorted(
        [(start, 1) for start, end in intervals] + [(end, -1) for start, end in intervals]
    )
    current = maximum = 0
    for _, delta in events:
        current += delta
        maximum = max(maximum, current)
    return maximum


parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
args = parser.parse_args()
target = Path(args.output)
if target.exists():
    raise FileExistsError("load_receipt_already_exists")
store = JobStore()
assert not any(job["state"] in {"queued", "preparing", "calling"} for job in store.all())
project = os.environ["P19_PROJECT"]
worker = docker.from_env().containers.get(f"{project}-worker-1")
worker.stop(timeout=5)
restart_worker(worker.id, store, project, profile="load")
base = json.loads(Path("fixtures/cases.json").read_text())[0]


def submit(index):
    started = time.monotonic()
    response = httpx.post(
        "http://api:8000/investigations",
        json=base,
        headers={
            "Authorization": f"Bearer {os.environ['P19_TOKEN']}",
            "Idempotency-Key": f"load-{uuid.uuid4().hex}",
        },
        timeout=10,
    )
    return {
        "index": index,
        "status": response.status_code,
        "job_id": response.json().get("id"),
        "seconds": time.monotonic() - started,
    }


with ThreadPoolExecutor(max_workers=4) as pool:
    responses = list(pool.map(submit, range(24)))
assert all(response["status"] in {202, 429} for response in responses)
ids = [row["job_id"] for row in responses if row["status"] == 202]
until = time.monotonic() + 45
while time.monotonic() < until and any(
    store.get(job)["state"] in {"queued", "preparing", "calling"} for job in ids
):
    time.sleep(0.1)
jobs = [store.get(job) for job in ids]
assert all(job["state"] == "succeeded" for job in jobs)
active = max_overlap([(job["created_at"], job["updated_at"]) for job in jobs])
intervals = []
for job in jobs:
    observations = store.observations(job["id"])
    starts = [row["at"] for row in observations if row["kind"] == "provider_start"]
    ends = [row["at"] for row in observations if row["kind"] == "provider_end"]
    assert len(starts) == len(ends) == 1
    intervals.append((starts[0], ends[0]))
maximum_calls = max_overlap(intervals)
assert active <= 8 and maximum_calls <= 1
write_once(
    target,
    {
        "manifest": manifest(),
        "responses": responses,
        "summary": build_summary(ids, store),
        "admission_seconds": distribution([r["seconds"] for r in responses]),
        "max_active_jobs": active,
        "max_active_provider_calls": maximum_calls,
        "profile": "load",
        "submissions": 24,
        "client_concurrency": 4,
        "simulated_delay_ms": 200,
    },
)
print(
    json.dumps(
        {
            "receipt": str(target),
            "admitted": len(ids),
            "rejected": 24 - len(ids),
            "max_active_jobs": active,
            "max_calls": maximum_calls,
        }
    )
)
