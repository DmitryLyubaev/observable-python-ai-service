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

### Approved small live study

The optional live mode is one fixed study, `p19-real-20261030`: Claude Haiku 5.5,
three ordered synthetic cases, no inference retries and a USD2 cumulative API-usage
allowance before tax/FX. It is a bounded demonstration, not a general spend platform.
This study is now stopped. The following commands document its original procedure;
reinitialization and further paid calls are refused. See the dated report for the
observed receipt-identity context gap and retained original failure.
The default setup, checks and examples above remain keyless and controlled.

The owner supplies a personal API key in ignored `.secrets/claude-api-key`, with local
file access restricted to the owner. This directory is excluded from Docker builds.
Only worker and `live-admin` mount that file as a read-only Compose secret; API,
dispatcher and checks do not receive it. Keep it outside the shared `.local` directory.
The private `.local/live-approval.json` records the specific approved proposal/allowance
and owner-confirmed account/alert readiness. Setup does not fabricate that approval.

After offline verification and review, use a persistent WSL terminal:

```sh
docker compose -p p19-demo up -d --build postgres redis api dispatcher jaeger
docker compose -p p19-demo -f compose.yaml -f compose.live.yaml run --rm --build live-admin python scripts/live.py prepare
docker compose -p p19-demo -f compose.yaml -f compose.live.yaml up -d --build worker
docker compose -p p19-demo -f compose.yaml -f compose.live.yaml run --rm --no-deps live-admin python scripts/live.py run --next
```

Preflight performs bounded model metadata and three free token-count requests, never an
inference probe. It freezes exact source/configuration/request identities before activating
the allowance. It refuses an existing study or active unrelated jobs. The worker verifies
the retained preflight receipt. API requests cannot select a provider or model.

Inspect the saved result in `.local/live/p19-real-20261030/run/` and write an actual
assistant assessment to a private notes file. For a passing first case:

```sh
docker compose -p p19-demo -f compose.yaml -f compose.live.yaml run --rm --no-deps live-admin python scripts/live.py assess --case export_0 --decision pass --notes-file .local/live/p19-real-20261030/export_0-assessment.txt
docker compose -p p19-demo -f compose.yaml -f compose.live.yaml run --rm --no-deps live-admin python scripts/live.py run --next
docker compose -p p19-demo -f compose.yaml -f compose.live.yaml run --rm --no-deps live-admin python scripts/live.py status
```

Use `fail` when warranted. Assess `export_1` and `export_2` separately after their own
responses. Only a successful, settled, assessed predecessor enables the next case.
A failed/unknown call or failed assessment stops the study. Re-entering `run --next`
at an assessment checkpoint reads the existing job; it does not repost it. Other
output names, restarts and rejected calls never restore consumed slots.

Each dispatch reserves USD0.50256 using conservative full-context/high-tier rates,
although the prompts are tiny. Known usage replaces that reservation; unknown usage
retains it. Cancellation does not prove billing stopped. Output truncation/refusal may
still have known usage. The 10-second provider/30-second job deadlines stay unchanged;
cold schema compilation may cause the first call to time out. No warming call or
silent timeout extension is permitted. Usage estimates remain distinct from an invoice,
tax/FX and unrelated account activity. Raw responses and failed receipts remain private.

To validate resolved credential configuration without printing it, pipe
`docker compose -p p19-demo -f compose.yaml -f compose.live.yaml config --format json`
into `python scripts/live.py check-config` in a keyless checks container. The canonical
suite also builds a dummy-only Docker context to verify secret exclusion.

Stop owned services after exporting needed traces. Retain database volumes, the allowance,
private receipts and any unresolved reservation. Public publication and hosted CI are
separate decisions. No real-provider throughput, general accuracy or human review follows
from this three-case study.

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
