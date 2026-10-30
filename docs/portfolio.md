# Portfolio presentation

Evidence dated 30 October 2026. Synthetic personal project; no commercial deployment,
customer adoption or successful general model-quality study is claimed. The latest
integrated offline result is 134 tests plus lock/lint/format. Hosted CI is pending.

## CV wording

- Built a synthetic sales-export investigation service with Python/FastAPI, PostgreSQL,
  Redis/Celery and OpenTelemetry; implemented replayable SSE progress, idempotent
  admission, cancellation and conservative worker-crash recovery, verified by 134
  offline tests.
- Integrated a bounded Claude adapter with structured results, evidence checks and a
  durable cumulative API allowance; retained and reported two stopped model samples
  across three actual calls, including the missing-citation failure that blocked the
  fresh study's next dispatch.

Short version:

> Python/FastAPI portfolio service demonstrating durable asynchronous jobs, SSE progress,
> tracing and conservative recovery, with 134 offline tests and honest failure-gating
> evidence from three real Claude calls.

Avoid describing it as production AI, proven model accuracy, a successful three-case
live study, token streaming, model-selected tools or autonomous remediation. The
receipt-context repair was verified offline but its fresh live case was never reached.

## Interview walkthrough

1. Start with the business ambiguity: a timeout alone does not establish rejection or
   receipt. All fixtures are independently created synthetic examples.
2. Trace admission, PostgreSQL dispatch intent, Redis delivery and one Celery worker.
   Explain why duplicates and reconnects must not create another inference.
3. Show persisted SSE progress and cancel-before-dispatch versus uncertainty afterward.
   Explain why unknown calls are not automatically retried.
4. Use a committed synthetic trace to connect API, dispatcher and worker. The latest
   actual follow-up trace has 12 spans; label the older screenshot as historical.
5. Show the offline test result separately from model quality. The original study
   stopped on a receipt semantic failure; the fresh sample stopped on missing citation,
   so the attempted context improvement is still unproven.
6. Explain durable per-study slots, the shared allowance, preserved original snapshot
   and first-failure stop. Three actual calls cost an estimated USD0.0005674 before
   tax/FX, with zero unresolved reservation. This is usage evidence, not a settled bill.

## A short controlled demo

Use the README's startup from a fresh checkout, without an external provider key.
Submit the three synthetic cases through the CLI, follow events and inspect saved
results. Reuse an idempotency key/body to demonstrate the same job. Walk through a saved
failure/recovery trace rather than launching another paid study during a presentation.
Stop the owned runtime afterward and retain its history volume.

Read the dispatch-intent code to explain the trade-off: this demonstration prioritizes
avoiding an uncertain duplicate call over automatic completion. The single supported
worker and fixed limits deliberately keep the project small. The model receives
application-selected evidence and cannot resend or modify a sale.

The [README evidence table](../README.md#evidence-at-a-glance), [original live report](live-report.md)
and [follow-up report](context-followup-report.md) are the primary references for claims.
