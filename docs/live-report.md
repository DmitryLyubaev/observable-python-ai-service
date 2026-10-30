# Real-model observation: stopped after the second case

30 October 2026, Australia/Brisbane. Bounded synthetic CV/portfolio demonstration.

**The sample did not pass all three cases.** One case passed, the second failed semantic
validation and the third was not run. The approved stop rule was followed without a paid
retry, warming call or replacement sample. Two actual Claude Haiku 5.5 inference requests
used **1,467 input and 487 output tokens**, with **USD0.0003902 estimated known API usage
cost before tax/FX**. No usage reservation remains unresolved. This is not settled billing.

## What ran

The actual operator CLI submitted through FastAPI, persisted PostgreSQL admission,
dispatcher/Redis/Celery and one live worker, then followed SSE and retrieved the saved
job. The model received the synthetic failure and lookup records, with no expected
receiver label or assessment rubric. Lookup remained application-driven, not model-selected
tool use. Progress was committed events, not model token streaming.

| Case | Reference fact | Returned outcome | Persisted job | Input/output tokens | Known usage USD |
|---|---|---|---|---|---:|
| Explicit rejection | rejected | rejected, cites `ev_reject` | succeeded | 732 / 218 | 0.0001822 |
| Receipt despite timeout | received | unresolved, no citations | failed: `invalid_provider_output` | 735 / 269 | 0.0002080 |
| No conclusive receipt/rejection | unresolved | not run | no live submission | not measured | not incurred |

The first explanation identified the fictional account-code rejection, cited the supplied
record, stated what was not established and proposed a read-only account/mapping check
without resending or altering the sale. An actual assistant-authored assessment was saved
and committed to the study ledger before the second call. No human assessment or separate
judge-model evaluation was performed.

Both attempted requests returned HTTP 200 and `end_turn`. The second failure was a
known-response semantic rejection, not a provider transport timeout or unknown inference.
Its input describes an earlier synthetic sales-export timeout; that is a different event.
Known usage was persisted before validating the explanation, and no invalid explanation
was exposed as a successful saved result.

## Observed context gap

The second response explicitly said `ev_receipt` did not contain an export/sale identity
link and therefore treated the receipt as unconfirmed. The frozen request indeed includes
only each retrieved record's `id` and `fact`. The SQL lookup filters by both `export_id`
and `sale_id`, but those fields and the selection-scope guarantee are not passed to the
model. Thus the local reference knows the matching receipt while the model lacks that
explicit binding.

This omission and the reason stated by the response are observed facts. Enriching the
evidence with its export/sale identity is a proposed improvement; whether it corrects a
future response is untested. The original request/response/job/failure remain intact.
No revised prompt, offline transformation or later favorable run is counted as success.
The third case remains unrun under the approved first-failure stop rule.

## Accounting, timing and source

The new Project 19 allowance was USD2 before tax/FX, separate from other project ledgers.
Each committed live dispatch consumed its case slot and reserved USD0.50256 atomically.
Validated returned usage replaced both reservations. Current study state is `stopped`,
with two consumed slots, USD0.0003902 known usage, zero unresolved reservations and
USD1.9996098 unspent allowance. That balance does not authorize resuming this stopped study.

The independently recalculated cost uses the approved
[dated Claude rates](https://platform.claude.com/docs/en/about-claude/pricing): USD0.10 per
million input tokens and USD0.50 per million output tokens for these small prompts.
Both responses reported zero thinking tokens; thinking would already be included in the
output total. Account-wide billing, settlement, tax/FX and unrelated activity were not
reconciled. The owner confirmed personal account/key and budget-alert readiness; that
confirmation is distinct from an account-console inspection.

| Measurement | Rejection | Receipt case |
|---|---:|---:|
| Queue wait | 3.351 s | 1.115 s |
| Provider attempt, including local bookkeeping | 4.348 s | 2.330 s |
| Creation to terminal state | 7.832 s | 3.502 s |

These are two per-case local observations, not a latency SLA, distribution study or
production-capacity result. Provider/job deadlines remained 10/30 seconds. Four bounded
authenticated preflight requests preceded inference: one model metadata read and three
free token counts, estimated at 732, 735 and 698. No inference was used to probe access.

Implementation revision: `ce64c13`. Canonical Linux runtime fingerprint:
`b6f775dd720b2e2e861717b76ee97cb5cc6511d621f76d8cebde926fc1fe55ac`.
The fingerprint includes executable source/tests/scripts/configuration and excludes
prose/private evidence; the live overlay is bound separately by SHA-256 in the manifest.
All four built images matched this fingerprint and contained no provider credential.
The three persistent service image IDs matched runtime inspection. The live worker independently reported
the same source and a readable file-mounted credential without displaying its value.

[Safe aggregate](evidence/live-summary.json) binds counts, usage, timing, source, overlay,
private-response hashes and image identities. Original provider messages, approval,
preflight records, progress, results, assistant notes and reconciliation remain ignored
under `.local/live/p19-real-20261030/`; the provider key is outside shared `.local` in
excluded `.secrets`, protected by an owner-only Windows ACL.

## Verification, traces and retained limits

Corrected canonical verification passed **109 tests in 135.20 seconds**, plus frozen
lock, Ruff lint and format. Receipt: `verify-a90e13e0f8cb4e1fa4938425fd3556ac`.
One fresh review found zero Critical, one Important and one Minor. The Important
database-dependent failed-receipt defect was reproduced twice and fixed in one
regression-tested pass. [Review closeout](live-review-closeout.md) records the disposition;
no second review is claimed.

Two actual collected traces each contain 12 spans across API, dispatcher and worker,
including admission, publication, lookup and the live provider attempt. Safe exports:
[rejection trace](evidence/live-rejection-trace.json) and
[receipt-validation-failure trace](evidence/live-receipt-validation-failure-trace.json).
Scans found no credential prefix or selected raw fixture/prompt markers. Domain failure
and usage are established from saved database/receipt facts, not inferred from span status.

Deferred Minor: partial CLI progress/diagnostics can be lost on timeout/nonzero exit;
committed database events permit readback when available. The failed-run receipt now
survives independent stop/status failures with accounting explicitly unavailable. The
older follow-up/recovery trace-linking Minor also remains. Actual human acceptance,
general model usefulness, real-provider failure reliability and production operation
remain unproven.

Original baseline failures were retained: forced database recovery exceeded the old test
readiness wait; a child-startup assumption invalidated a short-timeout assertion; one API
restart exceeded its incidental eight-second readiness bound. Test-only readiness and
fault-injection changes preserved application deadlines and business assertions. The
original controlled load was not repeated or relabelled as current-source performance.

Application containers are stopped after trace export, with both database volumes and
private evidence retained. The existing local-integration preference applies to this
implementation and its failed-sample report. Public push, hosted CI, infrastructure
provisioning and another paid study remain separate decisions.
