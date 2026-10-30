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
        mode = os.environ.get("P19_PROVIDER", "controlled")
        study = os.environ.get("P19_LIVE_STUDY") if mode == "live" else None
        if mode not in {"controlled", "live"} or (mode == "live" and study != "p19-real-20261030"):
            print("worker_provider_configuration_invalid", flush=True)
            return
        store = JobStore()
        run_job(
            job_id,
            socket.gethostname(),
            store=store,
            profile=os.environ.get("P19_PROFILE", "success"),
            hook=lambda stage: process_barrier(store, job_id, stage),
            live_study_id=study,
        )
    except Exception:
        print("worker_execution_failed", flush=True)
