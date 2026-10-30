import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx

from p19.acceptance import manifest, write_once
from p19.jobs import JobStore
from p19.reporting import build_summary
from p19.telemetry import read_collected_traces

run = Path(".local/runs") / f"demo-{uuid.uuid4().hex}"
run.mkdir(parents=True)
cases = json.loads(Path("fixtures/cases.json").read_text())
expected = ["rejected", "received", "unresolved"]
ids = []
with httpx.Client(
    base_url="http://api:8000",
    headers={"Authorization": f"Bearer {os.environ['P19_TOKEN']}"},
    timeout=10,
) as client:
    for index, case in enumerate(cases):
        case_file = run / f"case-{index}.json"
        case_file.write_text(json.dumps(case))
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "p19.cli",
                "submit",
                "--file",
                str(case_file),
                "--idempotency-key",
                f"demo-{uuid.uuid4().hex}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        job = json.loads(result.stdout)
        ids.append(job["id"])
        followed = subprocess.run(
            [sys.executable, "-m", "p19.cli", "follow", job["id"]],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        (run / f"progress-{index}.jsonl").write_text(followed.stdout)
        saved = client.get(f"/investigations/{job['id']}").json()
        assert (
            saved["state"] == "succeeded" and saved["result"]["receiver_outcome"] == expected[index]
        )
        write_once(run / f"result-{index}.json", saved)
        print(
            json.dumps(
                {
                    "job_id": job["id"],
                    "outcome": saved["result"]["receiver_outcome"],
                    "trace_id": saved["trace_id"],
                }
            ),
            flush=True,
        )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        traces = read_collected_traces(ids[0])
        names = {span["name"] for trace in traces for span in trace["spans"]}
        if {
            "investigation.admit",
            "queue.publish",
            "worker.execute",
            "evidence.lookup",
            "provider.attempt",
        } <= names:
            break
        time.sleep(0.2)
    assert traces
    write_once(run / "trace.json", traces)
write_once(
    run / "receipt.json",
    {
        "manifest": manifest(),
        "job_ids": ids,
        "summary": build_summary(ids, JobStore()),
        "passed_cases": 3,
    },
)
print(json.dumps({"demo": "passed", "receipt": str(run / "receipt.json")}))
