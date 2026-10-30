import math
import os
import time
from pathlib import Path

from sqlalchemy import text

from p19.attempts import AttemptStore
from p19.controlled import ControlledProvider
from p19.db import ExecutionDeadline
from p19.evidence import lookup, seed
from p19.jobs import JobStore, json_value
from p19.provider import InvalidProviderOutput, ProviderFailure, validate_reply
from p19.telemetry import safe_span


def run_job(
    job_id,
    worker_instance_id,
    *,
    store=None,
    profile="success",
    hook=None,
    fault=None,
    live_study_id=None,
):
    store = store or JobStore()
    job = store.get(job_id)
    with safe_span("worker.execute", job_id, job["trace_context"]):
        try:
            return _run_job(
                job_id,
                worker_instance_id,
                store=store,
                profile=profile,
                hook=hook,
                fault=fault,
                live_study_id=live_study_id,
            )
        finally:
            if live_study_id is not None:
                from p19.live import LiveStudy

                try:
                    state = store.get(job_id)["state"]
                    if state in {"failed", "cancelled", "interrupted", "outcome_unknown"}:
                        LiveStudy(store, live_study_id).stop("job_" + state)
                except Exception:
                    pass  # An unsatisfied slot/assessment still blocks any later dispatch.


def _run_job(
    job_id,
    worker_instance_id,
    *,
    store=None,
    profile="success",
    hook=None,
    fault=None,
    live_study_id=None,
):
    store = store or JobStore()
    job = store.claim(job_id, worker_instance_id)
    if job is None:
        return
    attempts = AttemptStore(store)
    deadline = time.monotonic() + 30
    hook = hook or (lambda stage: None)
    try:
        seed(store)
        if profile == "lookup_timeout":
            store.finish(job_id, worker_instance_id, "failed", "lookup_timeout")
            return
        lookup_started = time.monotonic()
        with safe_span("evidence.lookup", job_id):
            evidence = lookup(job["failure"], store)
        store.observe(job_id, "lookup", {"duration_seconds": time.monotonic() - lookup_started})
        with store.db.write() as conn:
            conn.execute(
                text(
                    "UPDATE jobs SET evidence=CAST(:evidence AS jsonb) WHERE id=:id AND state='preparing'"
                ),
                {"id": job_id, "evidence": json_value(evidence)},
            )
        live_call = None
        if live_study_id is not None:
            from p19.live import LiveStudy

            live_call = LiveStudy(store, live_study_id).prepare(job["failure"], evidence)
        for _ in range(1 if live_call else 2):
            hook("before_dispatch")
            if time.monotonic() >= deadline:
                store.finish(job_id, worker_instance_id, "failed", "execution_deadline")
                return
            options = {"fault": fault == "dispatch", "deadline": deadline}
            if live_call is not None:
                options["live_call"] = live_call
            intent = attempts.begin(job_id, worker_instance_id, **options)
            if intent is None:
                return
            attempt_id, number = intent
            started = time.monotonic()
            hook("after_dispatch")
            if time.monotonic() >= deadline:
                store.finish(
                    job_id, worker_instance_id, "outcome_unknown", "execution_deadline_after_intent"
                )
                return
            store.observe(
                job_id,
                "provider_start",
                {"attempt_id": attempt_id, "profile": "live" if live_call else profile},
            )
            try:
                with safe_span("provider.attempt", job_id) as span:
                    span.set_attribute("attempt.id", attempt_id)
                    span.set_attribute("provider.mode", "live" if live_call else "controlled")
                    remaining = min(10, deadline - time.monotonic())
                    if remaining <= 0:
                        raise ExecutionDeadline("execution_deadline_after_intent")
                    if live_call is not None:
                        from p19.claude import ClaudeProvider

                        span.set_attribute("provider.model", "claude-haiku-5-5")
                        provider = ClaudeProvider(
                            live_call.payload,
                            Path(
                                os.environ.get("P19_CLAUDE_KEY_FILE", "/run/secrets/claude_api_key")
                            ),
                            receipt_path=Path(
                                os.environ.get(
                                    "P19_LIVE_RECEIPTS", ".local/live/p19-real-20261030/provider"
                                )
                            )
                            / f"{attempt_id}.json",
                        )
                    else:
                        provider = ControlledProvider(profile)
                    reply = provider.invoke(job["failure"], evidence, number, remaining)
                store.observe(job_id, "provider_end", {"attempt_id": attempt_id})
                hook("after_reply_before_commit")
                if fault == "result":
                    raise RuntimeError("result_commit_fault")
                attempts.finish(attempt_id, "responded", reply["usage"], time.monotonic() - started)
                if reply.get("error"):
                    store.finish(job_id, worker_instance_id, "failed", reply["error"])
                    return
                if time.monotonic() >= deadline:
                    store.finish(job_id, worker_instance_id, "failed", "reply_after_deadline")
                    return
                result = validate_reply(reply, evidence)
                store.finish(job_id, worker_instance_id, "succeeded", result=result)
                return
            except ProviderFailure as exc:
                store.observe(job_id, "provider_end", {"attempt_id": attempt_id})
                attempts.finish(
                    attempt_id,
                    "rejected" if exc.definitely_not_processed else "unknown",
                    duration=time.monotonic() - started,
                )
                delay = exc.retry_after_seconds
                retry = (
                    live_call is None
                    and exc.kind == "rate_limit"
                    and exc.definitely_not_processed
                    and number == 1
                    and isinstance(delay, (int, float))
                    and math.isfinite(delay)
                    and 0 <= delay <= 2
                    and time.monotonic() + delay < deadline
                )
                if retry and attempts.retry_ready(job_id, worker_instance_id):
                    hook("between_attempts")
                    time.sleep(delay)
                    continue
                store.finish(
                    job_id,
                    worker_instance_id,
                    "failed" if exc.definitely_not_processed else "outcome_unknown",
                    exc.kind,
                )
                return
            except InvalidProviderOutput:
                store.finish(job_id, worker_instance_id, "failed", "invalid_provider_output")
                return
    except ExecutionDeadline:
        current = store.get(job_id)
        store.finish(
            job_id,
            worker_instance_id,
            "outcome_unknown" if current["state"] == "calling" else "failed",
            "execution_deadline",
        )
    except Exception:
        # The raw exception can contain request/connection secrets. Persist only safe classes.
        try:
            current = store.get(job_id)
            state = "outcome_unknown" if current["state"] == "calling" else "failed"
            store.finish(job_id, worker_instance_id, state, "persistence_or_execution_failure")
        except Exception:
            pass  # A later proof-bound recovery preserves the unfinished attempt as unknown.


def process_barrier(store, job_id, stage):
    if os.environ.get("P19_BARRIER") == stage:
        import redis

        store.observe(job_id, "barrier", {"stage": stage})
        broker = redis.Redis.from_url(os.environ["P19_REDIS_URL"], socket_timeout=27)
        if not broker.blpop(f"release:{job_id}", timeout=25):
            raise RuntimeError("barrier_timeout")
