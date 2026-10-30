import os
import socket
import subprocess
import sys
import time

import httpx
from conftest import record


def test_actual_api_process_restart_preserves_same_job_result_and_events(store):
    from p19.broker import publish

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "p19.api:create_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "critical",
        "--no-access-log",
    ]

    def start():
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.3).status_code == 200:
                    return process
            except httpx.HTTPError:
                pass
            assert process.poll() is None
            time.sleep(0.05)
        process.kill()
        process.wait(timeout=5)
        raise AssertionError("api_not_ready")

    headers = {"Authorization": f"Bearer {os.environ['P19_TOKEN']}"}
    process = start()
    first_pid = process.pid
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", headers=headers, timeout=5
        ) as client:
            job = client.post(
                "/investigations", json=record(), headers={"Idempotency-Key": "process-restart"}
            ).json()
        process.kill()
        process.wait(timeout=5)
        publish(job["id"], {})
        deadline = time.monotonic() + 10
        while store.get(job["id"])["state"] != "succeeded" and time.monotonic() < deadline:
            time.sleep(0.05)
        process = start()
        assert process.pid != first_pid
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", headers=headers, timeout=5
        ) as client:
            saved = client.get(f"/investigations/{job['id']}").json()
            assert saved["id"] == job["id"] and saved["state"] == "succeeded"
            assert len(saved["attempts"]) == 1
            stream = client.get(
                f"/investigations/{job['id']}/events",
                headers={"Last-Event-ID": str(job["sequence"])},
            )
            ids = [int(line[3:]) for line in stream.text.splitlines() if line.startswith("id:")]
            assert ids == [
                event["sequence"] for event in store.events_after(job["id"], job["sequence"])
            ]
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
