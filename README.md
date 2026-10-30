# Observable Python AI service

A local, synthetic portfolio demonstration of Python service operation. An operator
submits a failed sales export; a read-only lookup establishes receiver facts and a
controlled provider returns a structured explanation with evidence references.

The three cases are explicit rejection, receipt despite a timeout, and unresolved
receiver outcome. There is no resend, accounting change or autonomous remediation.
The default provider is deterministic. An explicit live overlay supports the separately
approved three-case Haiku study. Its [actual sample](docs/live-report.md) stopped after
the second case: one passed, one failed semantic validation and one was unrun, at
USD0.0003902 estimated known API usage cost before tax/FX. No production capacity or
customer adoption is claimed.

The separately approved [context follow-up](docs/context-followup-report.md) also
stopped: its first case returned the correct rejection but omitted the required citation.
Only one new inference ran; the other two cases were unrun. Cumulative known usage
across both stopped studies is USD0.0005674 before tax/FX, with no unresolved reservation.

The later [offline receipt-context repair](docs/receipt-context-repair.md) carries
persisted export/sale IDs into the model input and rejects invalid bindings before
request construction. The follow-up did not reach the receipt case, so its effect on
that model response remains untested. Both studies are stopped; unspent balance does
not authorize another sample under the cumulative USD2 ceiling.

The workflow uses FastAPI, PostgreSQL, Redis/Celery, OpenTelemetry and a local Jaeger
viewer. PostgreSQL owns job state, attempts and replayable progress. SSE disconnects
do not cancel work. A committed dispatch intent marks the uncertainty boundary: a
worker crash after that point leaves an unknown outcome and never automatically calls
the provider again. Only a confirmed non-executed controlled 429 can retry, once.

## Run locally

Use Docker with Linux containers and Compose. On the development Windows machine,
run these commands from one persistent Ubuntu WSL terminal in this checkout. Short
Windows `wsl --exec` commands can allow the distro and containers to stop when the
last foreground session ends. No globally installed Python package is required.

```sh
python3 scripts/setup.py
docker compose -p p19-demo up -d --build api dispatcher worker jaeger
docker compose -p p19-demo run --rm tools python scripts/demo.py
```

The API binds `127.0.0.1:8199` and Jaeger binds `127.0.0.1:16699`. Database, Redis and
OTLP ports stay inside the project network. If a chosen port is occupied, change the
loopback binding; do not stop an unrelated service. Credentials are generated into the
ignored `.env`; read the local file to use another client. They are not included in
screenshots or reports. All investigation operations require its bearer token.

The CLI commands are `p19 submit --file FILE --idempotency-key KEY`, `p19 get JOB`,
`p19 follow JOB --after EVENT_ID`, and `p19 cancel JOB`. Run through the `tools` service
to inherit its header credential and internal API URL. `demo.py` uses these actual
HTTP/CLI paths. A repeated key/body returns the original job; a changed body conflicts.

Progress is committed events, not token streaming or a fabricated percentage. Cancel
before dispatch prevents a call. After dispatch it records the request and preserves
usage/uncertainty; it does not establish that provider billing stopped. A timeout is
not proof of non-delivery, and absence of a receipt is not proof the receiver rejected
the sale. Saved results contain the trace ID for the local viewer.

## Checks and controlled recovery

The test project has separate database volumes and names. Keep test execution serial.

```sh
docker compose -p p19-check run --rm --build checks python scripts/verify.py
```

This runs the locked environment checks, lint/format, PostgreSQL/Redis integration,
actual HTTP/SSE and Celery behavior, abrupt owned-worker crashes and collector export.
Required services must be ready; a missing Docker dependency is a failure, not a skip.
The checks service and lifecycle tooling can access the local Docker socket. The API,
dispatcher and worker cannot. Use this tooling only on a trusted local machine.

Recovery is intentionally conservative. Stop/kill the exact owned worker container,
then run `python -m p19.lifecycle restart-worker --container CONTAINER_ID --project
p19-demo` through checks/lifecycle tooling. It verifies stopped state, exact labels,
hostname/instance identity, network and permitted mounts before recovering that
instance. Preparing work becomes interrupted; dispatched work becomes unknown. A
running/foreign target or existing running replacement is refused. This is a controlled
local restart protocol, not automatic failover under network partitions.

Limits are eight active admitted jobs and one supported worker process/call at a time.
Jobs waiting 60 seconds expire; each gets at most three publication reservations, five
seconds apart. Lookup/provider/execution limits are 2/10/30 seconds. Controlled fault
profiles test behavior; their simulated timeouts do not measure real provider timing.
Unknown usage is absent, never silently zero. No provider SDK, key or paid allowance is
configured by setup. A live provider would require a separately specified adapter and
costed acceptance scope.

## Evidence and cleanup

### Approved context follow-up

The original `p19-real-20261030` sample remains stopped: one pass, one semantic
failure and one unrun case, with USD0.0003902 known usage. The owner separately
approved one fresh run, `p19-real-20261030-context-1`, with at most three additional
Haiku calls under the same cumulative USD2 allowance before tax/FX. Never combine
the old pass with new cases or reset the old ledger.

The [follow-up runbook](docs/context-followup-runbook.md) covers read-only original
history capture before migration, exact evidence reconciliation, explicit run IDs,
secret isolation, one free preflight, per-case assistant assessment and cleanup.
The CLI requires `--study p19-real-20261030-context-1` before every subcommand.
Only worker/admin receive the protected key; ordinary checks remain controlled.

Per-study slots share one durable allowance and the transaction lock. Unknown usage
retains its reservation and stops that run; failure never authorizes a replacement.
No retries, warming, fallback or paid judge is allowed. Source/request/fixture hashes,
10/30-second bounds and the original failed evidence are preserved. Actual improvement
on the receipt case remains untested because the follow-up stopped before it. Public publication/hosted CI
and any additional study remain separate decisions.

The dated [local report](docs/local-report.md) records actual checks, source/runtime
digests, sample counts, original failures and limitations. The load script permits one
named output receipt for its 24 unique requests, concurrency four and 200 ms controlled
provider delay. Existing receipts cannot be overwritten. This sample is functional
evidence rather than a production benchmark.

Raw traces/logs and database state stay under ignored `.local/` or named project
volumes. Sanitized examples are in `docs/evidence/`. Jaeger's default storage is
in-memory: export needed traces before stopping it. Metrics come from persisted job
and attempt records, not assumed completeness of telemetry.

```sh
docker compose -p p19-demo stop
docker compose -p p19-check stop
```

These commands retain evidence volumes. Do not use broad Docker prune or delete
unrelated containers, volumes or source. Public publication/hosted CI are separate
decisions; this local project performs no cloud provisioning.
