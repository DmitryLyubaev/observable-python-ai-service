import os
import socket

from celery.signals import worker_process_init

from p19.broker import app
from p19.jobs import JobStore
from p19.runner import process_barrier, run_job


@worker_process_init.connect(weak=False)
def init_worker(**kwargs):
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    from p19.telemetry import configure_telemetry

    configure_telemetry("p19-worker")
    CeleryInstrumentor().instrument()


@app.task(name="p19.investigate", ignore_result=True)
def investigate(job_id):
    try:
        store = JobStore()
        run_job(
            job_id,
            socket.gethostname(),
            store=store,
            profile=os.environ.get("P19_PROFILE", "success"),
            hook=lambda stage: process_barrier(store, job_id, stage),
        )
    except Exception:
        print("worker_execution_failed", flush=True)
