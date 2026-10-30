# Context follow-up: stopped after the first case

30 October 2026, Australia/Brisbane. Bounded synthetic CV/portfolio demonstration.

The approved fresh sample **failed its first case and stopped**. Haiku returned the
correct `rejected` outcome for `export_0`, but its actual `evidence_ids` was empty
instead of citing `ev_reject`. The study driver enforced that declared criterion.
The new receipt case and unresolved case were not submitted. No retry, replacement,
warm-up, fallback, judge call or additional inference occurred.

This does not test whether the receipt-context repair improves the original receipt
failure. Preserve both separate unsuccessful samples; do not combine cases into a
three-case success. [Safe measured evidence](evidence/context-followup-summary.json)
and [the actual collected trace](evidence/context-followup-failure-trace.json) accompany
this report. The [original report](live-report.md) remains unchanged.

## Implementation and verification

The owner approved the detailed follow-up proposal, SHA-256
`65480db71891ff5b3dcc449636cc04ca7abef68b66c466c27deb0991b1900f16`, including minimal
history-preserving support and at most three new calls under the original cumulative
USD2 allowance. Existing Native execution and local-main choices were retained. The
implementation plan translated that approved scope without another call/budget decision.

Implementation `944ae75` adds per-study case/ordinal uniqueness, keeps global job/attempt
uniqueness without foreign keys to resettable jobs, and retains the shared transaction
lock `190019` with one durable USD2 allowance row. Reservation sums all studies while
case ordering and assessment remain study-specific. CLI and worker explicitly select
only `p19-real-20261030-context-1`. Original-study initialization/dispatch is closed outside
disposable checks. Preflight binds run ID, source and exact request hashes. Original
history/evidence is reconciled before preflight and the snapshot is rechecked under the
dispatch transaction lock. The [runbook](context-followup-runbook.md) records the procedure.

Baseline 18 budget checks passed. New history/run checks first reproduced 11 failures,
then passed 31 focused checks. CLI checks reproduced two failures before implementation.
The rebuilt focused suite passed 45 checks in 39.13 seconds; two additional boundary/
read-only-history checks passed. Canonical verification passed **134 tests in 146.52
seconds**, plus lock/lint/format, receipt `verify-63c086978b62453894e03bf1ff19ac0b`.
One stale-image focused attempt had 43 passes/two configuration failures; rebuilding
the baked Compose overlay resolved those failures without a product-code correction.

One fresh read-only review of `eafff72..944ae75` found zero Critical, zero Important and
two Minor findings, deferred below. No fix pass or second review occurred. Linux source
fingerprint for verification and the actual live runtime:
`669f99160ff70b9e393835278a57182acc5a3e3c91b644076e56a20550c7430d`.
Live overlay SHA-256:
`e62c9baa371a17bb49e7d3a41f9ed9152f14ebb8d7fd35045d94a92f87fbd7b1`.
Fixture bytes, generic system prompt, response schema, model and 10/30-second bounds
were unchanged. The original controlled 24-submission load experiment was not repeated.

## Real-history preservation and preflight

Before application migration, only the retained real PostgreSQL was started. A private
74,317-byte `pg_dump` retained original live tables and job/attempt/event/evidence data.
The read-only history command bypassed JobStore/schema initialization and reconciled
the original DB manifest/calls with retained manifest and raw provider receipts.
Original full-snapshot hash:
`7c4a9840f965578ae1d29a1cfc718882cbeffd43ea34a781a0e8289cc7f5974f`.
Original manifest hash:
`ba6abc77a278247b0beb9332af7a8e74157ad01eb5a053bb7df762d4aa14edb7`.
The additive migration preserved that exact snapshot. It was equal again after the
new call. The original study stays stopped with its two original consumed slots,
USD0.0003902 known usage, no reservation and its original third case unrun.

Public [model specifications](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
and [pricing](https://platform.claude.com/docs/en/about-claude/pricing) were rechecked
unchanged on 30 October. Small-prompt rates remain USD0.10 input/USD0.50 output per
million tokens; the existing USD0.50256 conservative reservation was retained. The
protected existing key was copied only into owner-restricted `.secrets`, hash-compared
without logging its value/digest and mounted only into worker/admin. Resolved secret
isolation passed in a keyless tools container. API, dispatcher and checks got no key.

Exactly one authenticated model GET and three free token counts passed, with full
request estimates **752/755/698**, no inference probe. Corrected source/configuration,
approval, original-history proof, payload hashes and image identities were frozen
before the inference. Actual worker source matched canonical verification, API health
passed and one worker answered the readiness ping.

## Separate observed outcomes

| Study | Case | Observed result |
|---|---|---|
| Original | `export_0` | Passed and assistant-assessed; rejected with `ev_reject`. |
| Original | `export_1` | Failed; unresolved/no citations against received reference. |
| Original | `export_2` | Unrun after the original failure. |
| Context follow-up | `export_0` | Failed study criterion; correct rejection but missing `ev_reject` citation. |
| Context follow-up | `export_1` | Unrun after first-case failure. |
| Context follow-up | `export_2` | Unrun after first-case failure. |

The actual new response was HTTP200 / `end_turn`, with 752 input and 204 output tokens,
zero reported thinking tokens and known usage estimate **USD0.0001772** before tax/FX.
It described the fictional account-code rejection and proposed a read-only mapping/
receiver check. Its empty citation list is present in the raw provider response, not
introduced by parsing. Its uncertainty prose also ends in a stray brace, but missing
citation alone is sufficient to fail the approved criterion.

The general service job was mechanically `succeeded`: schema, cited-ID subset and
outcome validation passed. The stricter study driver additionally requires the exact
case citation and therefore wrote `live_case_automated_check_failed`, stopped the study
as `live_driver_failure` and prohibited another dispatch. These are different recorded
states, not a claimed successful model sample. Actual assistant-authored FAIL notes and
an assessment artifact were retained after inspection. The stopped DB call's assessment
remains null because stopped-study mutation is refused; no database-assessed PASS is
claimed and no next case was enabled.

For this one new observation: queue 1.282796 seconds, provider attempt 5.313293917 seconds,
job completion 6.675342 seconds. One actual 12-span trace covers API/dispatcher/worker.
This is one local synthetic case, not general latency, throughput or accuracy evidence.

Across both studies: **3 inference calls**, 2,219 input/691 output tokens and
**USD0.0005674** known API-usage estimate before tax/FX, with zero unresolved reservation.
The same USD2 ceiling leaves USD1.9994326 unused. Unused money or unrun cases do not
authorize resuming either stopped study. Provider settlement and unrelated account
activity were not reconciled; this application meter is not an account-wide invoice cap.

## Deferred findings and execution rulings

- New Minor: the race test covers competing follow-up requests, with a separate global
  budget boundary test and shared-lock inspection; a race across different studies is
  not directly exercised.
- New Minor: direct programmatic original-study `prepare` on a fresh non-check DB can
  issue four free authenticated preflight requests before initialization rejects it.
  The CLI/worker reject that identity, and the retained original is already stopped,
  so the approved operational path cannot enter it.
- Existing Minors: partial CLI progress retention after timeout/nonzero exit, and
  explicit follow-up/recovery trace links. Some context still needs persisted-event
  readback. No unsolicited diagnostic expansion was added.

Rulings: the detailed approved proposal authorized this support and sample with the
existing Native/local-main choices, not additional calls or public actions. Git fallback
was used after the native tool rejected this product root; only isolation metadata
differs. Baked configuration changes required a local checks-image rebuild. Real
provider/DB/model claims required operational evidence beyond review, and mismatches
would stop the sample. Existing diagnostic limits stay deferred. Production hardening
and malicious privileged proof/database forgery remain outside this trusted-operator
CV demonstration; no adversarial or production reliability claim follows.

## Local integration and preservation

Primary `main` fast-forwarded from `eafff72` to `2806b63`. Fresh primary canonical
verification passed **134 tests in 207.80 seconds**, plus lock/lint/format, receipt
`verify-6eaba086f1e24a9c879735e18f0a17a1`, with the same source fingerprint as the
candidate and actual live runtime. No executable source changed after the fresh review.
Post-merge checks used controlled transports in `p19-check`, with no extra paid call.

All **673 private execution/configuration files** were copied and SHA-256 verified
under primary ignored `.local/pre-integration-context-followup-2026-10-30-1b1d52de`.
A full archive recheck found zero mismatches. Of the active `.local` paths, 661 files
were copied and one generic diagnostic trace conflicted: the worktree's
`traces/collected-success.json` is preserved in the archive without overwriting the
primary diagnostic. Original immutable study receipts and original reports were not
replaced. The new run, original input proof files and raw evidence are also retained
at their original relative paths in primary `.local`.

Primary `.env` and the separately protected primary provider key matched the execution
copies. No key value/digest was printed, committed, included in Docker context or
placed in the shared archive. The key remains in owner-restricted primary `.secrets`.

After successful primary checks and preservation, unforced `git worktree remove`
removed `.worktrees/context-followup`; the fully merged branch was deleted normally.
The old `.worktrees/local` checkout/branch/scratch and the earlier empty receipt-context
directory/merged branch remain untouched. No prior rejected cleanup was retried.

Final readback showed zero running `p19-demo`/`p19-check` containers and no 8199/16699
listeners. Both database volumes remain, preserving both stopped studies and their
shared allowance/history. The owned temporary WSL shell was closed normally. No public
push, hosted CI or cloud resources were involved. The remaining decision is how to
present/publish the honest bounded evidence, not automatic continuation of either study.
