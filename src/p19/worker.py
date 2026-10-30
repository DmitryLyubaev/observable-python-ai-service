import os
import socket

from p19.broker import app
from p19.jobs import JobStore
from p19.runner import process_barrier, run_job


@app.task(name="p19.investigate", ignore_result=True)
def investigate(job_id):
    store = JobStore()
    run_job(
        job_id,
        socket.gethostname(),
        store=store,
        profile=os.environ.get("P19_PROFILE", "success"),
        hook=lambda stage: process_barrier(store, job_id, stage),
    )
