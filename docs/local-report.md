# Local investigation-service evidence

30 October 2026, Australia/Brisbane. Bounded synthetic CV/portfolio demonstration.
Local acceptance and one independent whole-branch review/correction pass are complete.
Local main integration is complete. The primary-checkout canonical command passed 54
tests plus lock/lint/format after packaging and verifier-reporting corrections.
[Integration record](integration-record.md) preserves the original failed attempts,
private-evidence preservation and current fingerprint. Publication remains separate.

## Measured outcome

The corrected canonical Linux command passed **53 tests**, Ruff lint/format and the frozen
lock check; pytest took 74.32 seconds. The reviewed candidate had 42 passing tests.
The actual CLI returned
the expected receiver outcomes for all three business cases. A separate CLI/lifecycle
demonstration passed five scenarios: cancellation before dispatch, CLI disconnect and
resume, cancellation after dispatch followed by timeout, pre-dispatch worker crash and
crash after a response but before its durable commit. These are automated assistant-run
observations, not human acceptance or real-model evaluation.

The original pre-correction load sample submitted **24 unique requests at concurrency four**, with a configured
200 ms controlled-provider delay. Eight were admitted and succeeded; sixteen received
429 at the admission boundary. There were eight provider attempts, maximum eight active
admitted jobs and maximum one active provider call. No favorable repeat was selected.

| Measurement | Sample | Min | Median | Max |
|---|---|---|---|---|
| Client admission response | 24 responses, including 429 | 46.98 ms | 79.98 ms | 234.36 ms |
| Server admission work | 8 admitted jobs | 9.25 ms | 12.85 ms | 34.55 ms |
| Queue wait | 8 admitted jobs | 3.387 s | 4.333 s | 5.209 s |
| Evidence lookup | 8 admitted jobs | 1.48 ms | 2.52 ms | 4.59 ms |
| Provider attempt, including local bookkeeping | 8 attempts | 207.04 ms | 210.10 ms | 214.34 ms |
| Creation to completion | 8 admitted jobs | 3.631 s | 4.580 s | 5.457 s |

The worker was deliberately restarted into its load profile immediately before this
sample; startup/queue delay is included. Results are local functional observations,
not production capacity, percentiles at scale, an SLA or real-provider latency. Local
PostgreSQL UTC timestamps join stages; individual durations use monotonic timers.

All provider usage is controlled/simulated. Actual external provider calls and charges
are zero. Unknown post-dispatch outcomes remain unknown with absent usage, not a zero
cost estimate. No provider account, key, paid budget or cloud resource was needed.

## Provenance and reproduction

The original business demo, failure demo, load sample and pre-review canonical manifest share runtime
fingerprint `4d4f3f1a4d56df69998c5adb4d9f0439fa66f17c292c32273375444c1c5bd00a`.
The fingerprint covers executable Python/SQL, tests, scripts, fixtures, lockfile,
pyproject, Dockerfile and Compose bytes; it excludes this report and other prose/media.
Git branch is `codex/local-demo`, based on initial commit `d9c3aa1`. Task 6 source is
`f60c6c2`; `2b3fd7a` adds the fingerprinted acceptance scripts and tests. Review corrections
are committed at `362b193` and verified at runtime fingerprint
`11a66bf2f254afc4cf93faacdeff262186706b0d07c084734fdd4181823dd483`.
The corrected canonical check and fresh three-case/five-scenario demos share that newer
fingerprint. The original load was not repeated; its measurements and old source identity
remain unchanged. No final-source load-performance measurement is claimed.

Original load/demo image configuration IDs:

- API: `sha256:3dd4fa9a639f762d8f6e02554e250640063ac99ea219f2d8577ccc74b041de84`
- Dispatcher: `sha256:3ba709820ef4409812a021720e881f010ffad3a3f1c8cdeef6f5531258ba3b9f`
- Worker: `sha256:3ea84f992356e2722a04c0e73b1ba590e5fbf176c33680b027935867e74da313`

Immutable base-image manifest digests and the full dependency lock are checked in.
Image IDs differ by build configuration; the runtime fingerprint binds their source.
Corrected demo images were API `sha256:a16204fb6a785cf07f0363f1d234390c5452f16aca03cce8b98667865ce4c168`,
dispatcher `sha256:3c2e406a9294759474c6c0b548a5308cc3a122d9336b76e135442c5f018b8d95`
and worker `sha256:076cad7a5afa043b8718442f9e03e45073965816eff66fecefbe098aeb25ba64`.

```sh
docker compose -p p19-check run --rm --build checks python scripts/verify.py
docker compose -p p19-demo up -d --build api dispatcher worker jaeger
docker compose -p p19-demo run --rm --no-deps tools python scripts/demo.py
docker compose -p p19-demo run --rm --no-deps lifecycle python scripts/failure_demo.py
docker compose -p p19-demo run --rm --no-deps lifecycle python scripts/load.py --output .local/runs/load-2026-10-30.json
```

The last command refuses to overwrite its original named receipt. A reproduction must
use a new output name and report it as a different sample. Run serially from a persistent
WSL terminal. The canonical verifier stops its owned services and retains volumes.

Original receipts are retained privately:
`verify-6da49fbd33cd4cb697f706533a42a505`,
`demo-5919f7cf009c4ae99cd0a3fc87f93578`,
`failure-demo-533f4c9c0596432d8e96a5e491be8e28`, and
`load-2026-10-30.json` under ignored `.local/runs/`.
[Safe aggregate](evidence/local-summary.json) contains the measured counts and manifests;
[additional metrics](evidence/lookup-admission-metrics.json) were read from the original
persisted load jobs without another submission or provider invocation.
Corrected receipts are `verify-8e93ec1c8790491fb196f69f5e3d1725`,
`demo-9972c27b17d54e4f97e3dd719d33a34a` and
`failure-demo-fce51e794b004d809122a32f16232d2c` under the same ignored directory.
[Corrected safe aggregate](evidence/corrected-summary.json) binds those current results.

## Acceptance observations

| Group | Evidence and limit |
|---|---|
| A1 | Three actual CLI submissions returned rejection/receipt/unresolved with saved structured results and allowed evidence IDs. Explanations are deterministic. |
| A2 | Real HTTP tests reject bad/missing auth, invalid/oversized chunked bodies and missing IDs; actual stopped PostgreSQL returns safe 503. One local operator only. |
| A3 | Concurrent admission and key races, changed-body conflict and actual duplicate Celery messages retain one job/attempt identity. |
| A4 | Actual Redis stop/restart preserves a queued identity; controlled publication failure, reservation spacing/count and expiry checks retain the declared dispositions. |
| A5 | Pre/post-dispatch cancellation, result race and cancellation during rate-limit wait are tested; actual failure demo retains unknown usage after in-flight cancellation. |
| A6 | Actual HTTP/SSE and CLI disconnect/resume preserve work, replay committed IDs and finish terminal streams. Progress is not token streaming. |
| A7 | Controlled 429, long Retry-After, timeout/5xx, lookup timeout, rejection and invalid output have checked states and counts. This is not a real-provider reliability study. |
| A8 | Actual abrupt Linux worker kills at three barriers retain interrupted/unknown outcomes without replay; new queued work continues. API process restarts in HTTP tests preserve results/events. |
| A9 | Transaction rollback and injected dispatch/result-commit faults preserve no-call/unknown behavior; actual post-response crash leaves no fabricated success. |
| A10 | Actual collected traces and a visible Jaeger timeline show API, dispatcher and worker correlation. Canary/error checks and collector outage pass. |
| A11 | One 24-submission sample gives 8 successes/16 admission rejections, at most 8 active jobs and 1 active provider call. |
| A12 | Locked clean image builds, canonical checks, receipts and this report provide reproduction; final owned-container/listener closeout is recorded separately. |

The viewer observation showed a 12-span investigation across three services, including
`investigation.admit`, `queue.publish`, `worker.execute`, `evidence.lookup` and
`provider.attempt`. [Success trace](evidence/success-trace.json) and
[cancellation/timeout trace](evidence/timeout-trace.jsonl) were exported before shutdown.
Those original examples and the screenshot remain historical; the
[corrected success trace](evidence/corrected-success-trace.json) and
[corrected timeout trace](evidence/corrected-timeout-trace.jsonl) are separately retained.

![Observed local Jaeger timeline](evidence/trace-viewer.png)

## Original failures and limits

One fresh review found no Critical, three Important and two Minor findings. The API
exception telemetry leak, expired dispatch-budget boundary and missing failed-load
receipts were reproduced and fixed in one regression-tested pass. New checks cover
chained API/Celery errors, deadlines inside/after the dispatch transaction, bounded lock
waits, late replies, partial transport observations and immutable run-name reservation.
An additional real API subprocess restart test closes the report's previous evidence
gap. The corrected suite passed 53 tests; no second independent review was performed.
[Review disposition and rulings](review-closeout.md) record the exact scope.

Deferred Minor: status, cancellation and recovery observations do not yet have explicit
span links to the original investigation. Persisted job IDs correlate their database
history. The main admission/queue/lookup/provider trace is evidenced; universal tracing
of every follow-up/recovery operation is not claimed.

- The initial Windows dependency download failed certificate validation. Command-scoped
  Windows native certificate trust resolved it; TLS verification was not disabled.
- An early WSL command exit stopped local dependency services. A bounded foreground
  diagnostic session held the distro active for the demonstrations.
- Tests found an ambiguous PostgreSQL null parameter; the query now casts its type.
- One combined run was invalidated by overlapping tests resetting the same database.
  It is retained as failed; subsequent canonical checks ran serially.
- Jaeger 2.22 readback rejected the legacy API route and an incompatible v3 filter;
  current v3 readback and bounded no-match polling now pass. The original failures
  remain in ignored logs.

One worker and one trusted local operator are the supported boundary. Recovery requires
proof that the exact old worker stopped; there is no partition-tolerant failover,
exactly-once inference or proof that in-flight cancellation stops billing. Jaeger storage
is transient. Real-model usefulness, provider access/costs, hosted CI, remote HTTPS,
publication and customer production use remain unproven.

Final application closeout verified zero owned running containers and no listeners on
8199/16699, with two database volumes retained. Automatic approval review rejected the
subsequent combined command to stop the bounded read-only diagnostic monitor and remove
the ignored plan scratch directory, stating "blocked by policy". Neither action was
retried. Scratch remains retained. The monitor originally kept its four-hour timeout;
after a later WSL restart it was no longer running. The integration record gives current closeout.
