import os
import time
from datetime import timedelta

import docker
from conftest import record
from test_api import serve


def test_actual_database_outage_is_safe_503(store):
    container = docker.from_env().containers.get(f"{os.environ['P19_PROJECT']}-postgres-1")
    with serve(store) as client:
        container.stop(timeout=2)
        try:
            response = client.post(
                "/investigations", json=record(), headers={"Idempotency-Key": "db-down"}
            )
            assert response.status_code == 503
            assert "password" not in response.text.lower()
        finally:
            container.start()
            until = time.monotonic() + 10
            while time.monotonic() < until:
                try:
                    store.get("missing")
                except Exception as exc:
                    if type(exc).__name__ == "JobNotFound":
                        break
                time.sleep(0.1)


def test_actual_broker_restart_preserves_queued_identity(store):
    from p19.dispatcher import Dispatcher

    container = docker.from_env().containers.get(f"{os.environ['P19_PROJECT']}-redis-1")
    job = store.admit(record(), "redis-restart")
    container.stop(timeout=2)
    try:
        started = time.monotonic()
        Dispatcher(store).tick(job["created_at"])
        assert time.monotonic() - started < 8
        assert store.get(job["id"])["state"] == "queued"
    finally:
        container.start()
    time.sleep(1)
    Dispatcher(store).tick(job["created_at"] + timedelta(seconds=5))
    until = time.monotonic() + 15
    while time.monotonic() < until and store.get(job["id"])["state"] != "succeeded":
        time.sleep(0.1)
    assert store.get(job["id"])["state"] == "succeeded"
    assert len(store.get(job["id"])["attempts"]) == 1
