# Approved distinct-run follow-up

30 October 2026. Bounded synthetic CV/portfolio demonstration, not production operation.
The owner approved the detailed context-follow-up proposal (SHA-256
`65480db71891ff5b3dcc449636cc04ca7abef68b66c466c27deb0991b1900f16`), its minimal
history-preserving implementation and at most three additional Haiku calls under the
same cumulative USD2 API-usage ceiling before tax/FX. The original two calls and failed
sample remain historical evidence. This is not authorization for repeated studies.

Only `p19-real-20261030-context-1` can be operated by the live CLI and worker. All CLI
commands require `--study` before the subcommand. The original study can be queried
programmatically but cannot be initialized/prepared/dispatched outside disposable checks.

## Before migration or authenticated access

Complete serial offline checks and one fresh review. Start only owned PostgreSQL,
retain its existing volume and back up the original live tables using `pg_dump`.
Copy the original retained manifest and provider receipts into an ignored local input
directory, preserving bytes. The history command deliberately bypasses JobStore/schema
initialization and uses only read queries:

```sh
docker compose -p p19-demo up -d --wait postgres
docker compose -p p19-demo run --rm --build --no-deps tools python scripts/live.py --study p19-real-20261030-context-1 history --source-root .local/original-live
```

This creates exclusive `.local/live/p19-real-20261030-context-1/original-history.json`.
It requires the stopped original study, exactly its two settled cases, the original
manifest/hash, matching raw provider usage, first-case pass and USD0.0003902 total.
Missing/modified history or evidence fails; do not create a fresh zero budget.
The proof retains every original study/call field and the original evidence hashes.
After application migration, compare a new read-only capture with that exact proof.

Prepare the ignored approval JSON at the named run root. It records owner personal
account/alert confirmation, `implementation_approved: true`, `allowance_usd: "2"`,
`max_inference_calls: 3`, `max_total_inference_calls: 5`, `automatic_retries: 0`, model
`claude-haiku-5-5`, `owner_confirmed: true`, the original monetary proposal hash
`e65ebcd6cf3ed79f3b85a815c0846ba3ed6e1d22ea5929fd18ecde7c223395a6`, the additional-call
proposal hash above, and the exact history receipt path/SHA-256. This records approval
of the detailed implementation proposal, not a claim that the owner separately read a
later transcription plan. Never put credentials in this JSON.

Keep the actual key in current-user-restricted `.secrets/claude-api-key`, excluded from
git, Docker context and shared `.local`. Only worker/admin mount it read-only. Resolve
Compose config into a private file and pass it to `check-config` without printing the
configuration or credential. That command requires the named run and checks both admin
and worker run identity as well as secret exposure.

## One preflight, then sequential calls

Use one persistent WSL shell on this Windows machine. Freeze corrected source, image,
overlay and approval identities before access. `prepare` performs exactly one metadata
GET and three free token counts, no inference. It refuses changed model/terms, failed
counts, estimates above 4096, a used study, altered history or nonstandard artifact root.
The preflight receipt binds run ID, source and all exact inference payload hashes.

```sh
docker compose -p p19-demo -f compose.yaml -f compose.live.yaml run --rm --build live-admin python scripts/live.py --study p19-real-20261030-context-1 prepare
docker compose -p p19-demo -f compose.yaml -f compose.live.yaml up -d --build api dispatcher worker jaeger
docker compose -p p19-demo -f compose.yaml -f compose.live.yaml run --rm --no-deps live-admin python scripts/live.py --study p19-real-20261030-context-1 run --next
```

Read the result/progress/raw response before writing an actual assistant-authored
assessment. Only success with settled known usage plus a saved passing assessment
enables the next case. Save honest notes into the named run root, then use:

```sh
docker compose -p p19-demo -f compose.yaml -f compose.live.yaml run --rm --no-deps live-admin python scripts/live.py --study p19-real-20261030-context-1 assess --case export_0 --decision pass --notes-file .local/live/p19-real-20261030-context-1/export_0-assessment.txt
```

Repeat `run --next` only after that assessment. There are at most three calls, in
fixture order, with no warming, retry, replacement, fallback or judge model. Preserve
10-second provider/30-second job deadlines and 1024 output tokens including thinking.
Stop on the first failure/unknown/failed assessment, leaving remaining cases unrun.
The original pass cannot be combined with new cases to claim a fresh three-case pass.

Each case consumes a per-study slot atomically with dispatch intent. All studies share
the existing transaction lock, singleton USD2 allowance and all-run cost/reservation
sum. Each call reserves USD0.50256; unknown accounting keeps it and stops that run.
Status reports per-run and cumulative fields separately. Original rows remain unchanged
and their snapshot is checked again under the dispatch transaction lock.

Collect real traces before stopping Jaeger, retain private raw receipts, reconcile
cumulative usage and unresolved reservations, and compare original proof again. Report
actual new results separately, including unsuccessful/unrun cases and unproven human
validation. Stop only owned services and retain volumes/history. Public publication,
hosted CI, cloud provisioning and any additional study require separate scope.
