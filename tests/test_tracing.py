import json
import os
import time

from conftest import record
from test_api import serve


def traces_for(job_id):
    from p19.telemetry import read_collected_traces

    return read_collected_traces(job_id)


def test_collected_trace_connects_admission_publication_worker_lookup_provider(store):
    from p19.dispatcher import Dispatcher
    from p19.telemetry import configure_telemetry, flush

    configure_telemetry("p19-api")
    with serve(store) as client:
        job = client.post(
            "/investigations", json=record(), headers={"Idempotency-Key": "trace"}
        ).json()
    Dispatcher(store).tick()
    assert job["trace_id"] == store.get(job["id"])["trace_context"]["traceparent"].split("-")[1]
    deadline = time.monotonic() + 15
    required = {
        "investigation.admit",
        "queue.publish",
        "worker.execute",
        "evidence.lookup",
        "provider.attempt",
    }
    while time.monotonic() < deadline:
        flush()
        traces = traces_for(job["id"])
        names = {span["operationName"] for trace in traces for span in trace["spans"]}
        if required <= names:
            break
        time.sleep(0.3)
    assert required <= names
    assert len(traces) == 1
    assert store.get(job["id"])["trace_context"].get("traceparent")
    os.makedirs(".local/traces", exist_ok=True)
    with open(".local/traces/collected-success.json", "w") as handle:
        json.dump(traces, handle)


def test_error_telemetry_excludes_canaries(store):
    from p19.telemetry import configure_telemetry, flush, safe_span

    configure_telemetry("p19-api")
    canary = "payload_marker_do_not_export"
    try:
        with safe_span("controlled.error", job_id="error-case"):
            raise ValueError(canary + os.environ["P19_TOKEN"])
    except ValueError:
        pass
    flush()
    deadline = time.monotonic() + 5
    traces = []
    while not traces and time.monotonic() < deadline:
        traces = traces_for("error-case")
        time.sleep(0.1)
    assert traces
    serialized = json.dumps(traces)
    assert canary not in serialized
    assert os.environ["P19_TOKEN"] not in serialized


def test_collector_outage_does_not_fail_business_job(store):
    import docker

    from p19.runner import run_job
    from p19.telemetry import flush

    collector = docker.from_env().containers.get(f"{os.environ['P19_PROJECT']}-jaeger-1")
    collector.stop(timeout=2)
    try:
        job = store.admit(record(), "telemetry-outage")
        run_job(job["id"], "local", store=store)
        flush()
        assert store.get(job["id"])["state"] == "succeeded"
    finally:
        collector.start()
