import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_provider = None


def configure_telemetry(service_name, endpoint=None):
    global _provider
    if _provider is None:
        _provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        exporter = OTLPSpanExporter(
            endpoint=endpoint
            or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318/v1/traces"),
            timeout=1,
        )
        _provider.add_span_processor(
            BatchSpanProcessor(
                exporter,
                max_queue_size=256,
                max_export_batch_size=64,
                schedule_delay_millis=100,
                export_timeout_millis=1500,
            )
        )
        trace.set_tracer_provider(_provider)


@contextmanager
def safe_span(name, job_id=None, context=None):
    tracer = trace.get_tracer("p19")
    with tracer.start_as_current_span(
        name,
        context=extract(context) if context else None,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        if job_id:
            span.set_attribute("job.id", str(job_id))
        try:
            yield span
        except Exception as exc:
            span.set_attribute("error.type", type(exc).__name__)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            raise


def flush():
    if _provider:
        return _provider.force_flush(timeout_millis=2000)
    return True


def read_collected_traces(job_id, endpoint="http://jaeger:16686"):
    import httpx

    now = datetime.now(timezone.utc)
    query = {
        "query.startTimeMin": (now - timedelta(hours=1)).isoformat(),
        "query.startTimeMax": (now + timedelta(seconds=1)).isoformat(),
        "query.searchDepth": 50,
        "query.filter": json.dumps(
            {"op": "eq", "args": [{"attr": {"key": "job.id"}}, {"scalar": {"value": job_id}}]}
        ),
    }
    response = httpx.get(endpoint + "/api/v3/traces", params=query, timeout=5)
    if response.status_code == 404:
        return []  # Jaeger v3 can report no matching indexed trace as 404; poll within caller's bound.
    response.raise_for_status()
    traces = {}
    for line in response.text.splitlines():
        envelope = json.loads(line)
        if "error" in envelope:
            raise RuntimeError("collector_query_failed")
        for resource in envelope.get("result", {}).get("resourceSpans", []):
            service = next(
                (
                    attr["value"].get("stringValue")
                    for attr in resource.get("resource", {}).get("attributes", [])
                    if attr["key"] == "service.name"
                ),
                None,
            )
            for scope in resource.get("scopeSpans", []):
                for span in scope.get("spans", []):
                    trace = traces.setdefault(
                        span["traceId"], {"traceID": span["traceId"], "spans": []}
                    )
                    trace["spans"].append(
                        {**span, "operationName": span["name"], "serviceName": service}
                    )
    return list(traces.values())
