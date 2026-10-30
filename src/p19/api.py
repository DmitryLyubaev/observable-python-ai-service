import hmac
import json
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from p19.config import token
from p19.jobs import AdmissionFull, JobNotFound, JobStore, KeyConflict, TerminalConflict
from p19.stream import iter_events


def public_view(job):
    view = {
        key: value
        for key, value in job.items()
        if key not in {"idempotency_key", "body_hash", "trace_context"}
    }
    parent = job["trace_context"].get("traceparent")
    view["trace_id"] = parent.split("-")[1] if parent else None
    return view


def create_app(store=None):
    from p19.telemetry import configure_telemetry

    configure_telemetry("p19-api")
    jobs = store or JobStore()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def access(request: Request, call_next):
        if request.url.path != "/health":
            provided = request.headers.get("Authorization", "")
            if not hmac.compare_digest(provided.encode(), f"Bearer {token()}".encode()):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        return JSONResponse({"error": "database_unavailable"}, status_code=503)

    @app.exception_handler(JobNotFound)
    async def not_found(request, exc):
        return JSONResponse({"error": "job_not_found"}, status_code=404)

    @app.exception_handler(KeyConflict)
    @app.exception_handler(TerminalConflict)
    async def conflict(request, exc):
        return JSONResponse({"error": "conflict"}, status_code=409)

    @app.exception_handler(AdmissionFull)
    async def capacity(request, exc):
        return JSONResponse({"error": "admission_full"}, status_code=429)

    @app.get("/health")
    def health():
        from sqlalchemy import text

        with jobs.db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ready": True}

    @app.post("/investigations", status_code=202)
    async def submit(request: Request):
        started = time.monotonic()
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 8192:
                raise HTTPException(422, "body_too_large")
            body.extend(chunk)
        try:
            record = json.loads(body)
            context = {}
            try:
                from opentelemetry.propagate import inject

                inject(context)
            except ImportError:
                pass
            from p19.telemetry import safe_span

            with safe_span("investigation.admit") as span:
                inject(context)
                job = jobs.admit(record, request.headers.get("Idempotency-Key"), context)
                span.set_attribute("job.id", job["id"])
        except (ValidationError, ValueError, TypeError):
            raise HTTPException(422, "invalid_request") from None
        jobs.observe(job["id"], "admission", {"duration_seconds": time.monotonic() - started})
        return public_view(job)

    @app.get("/investigations/{job_id}")
    def get(job_id: str):
        return public_view(jobs.get(job_id))

    @app.post("/investigations/{job_id}/cancel", status_code=202)
    def cancel(job_id: str):
        return public_view(jobs.cancel(job_id))

    @app.get("/investigations/{job_id}/events")
    async def events(job_id: str, request: Request):
        current = jobs.get(job_id)
        try:
            after = int(request.headers.get("Last-Event-ID", "0"))
            if after < 0 or after > current["sequence"]:
                raise ValueError
        except ValueError:
            raise HTTPException(422, "invalid_event_cursor") from None
        return StreamingResponse(
            iter_events(job_id, after, jobs, request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host="0.0.0.0", port=8000, access_log=False, log_level="warning")
