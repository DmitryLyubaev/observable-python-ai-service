import asyncio
import json

from p19.contracts import TERMINAL


async def iter_events(job_id, after, jobs, request=None):
    quiet = 0
    while True:
        if request is not None and await request.is_disconnected():
            return
        events = jobs.events_after(job_id, after)
        for event in events:
            after = event["sequence"]
            payload = json.dumps(event, default=str, separators=(",", ":"))
            yield f"id: {after}\nevent: progress\ndata: {payload}\n\n".encode()
        current = jobs.get(job_id)
        if current["state"] in TERMINAL and after >= current["sequence"]:
            return
        quiet += 1
        if quiet % 20 == 0:
            yield b": keepalive\n\n"
        await asyncio.sleep(0.1)
