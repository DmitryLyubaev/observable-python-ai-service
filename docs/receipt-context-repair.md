# Offline receipt-context repair

30 October 2026, Australia/Brisbane. Bounded synthetic CV/portfolio demonstration.

The original [real-model sample](live-report.md) stopped after one pass and one
semantic failure, leaving the third case unrun. The failed receipt explanation
explicitly cited absent export/sale links. SQL already filtered by both identities,
but returned only the record ID and fact to the model. Preserve that observed failure
and its USD0.0003902 known usage estimate before tax/FX; this repair is later evidence.

## Change

Implementation commit `e072593` selects `export_id` and `sale_id` from the persisted
evidence columns alongside the record ID and fact. Both existing SQL predicates remain.
`claude.build_request` rejects any row with missing or mismatched bindings using
`ValueError('evidence_identity_mismatch')` before constructing request bytes. Empty
evidence remains valid. Frozen manifest construction checks the same complete record
shape against the existing fixture values.

No expected labels or reference explanations enter the serialized user input. The
generic system prompt, fixture bytes, model, schema, token caps, no-retry behavior,
deadlines and original study schema/allowance remain unchanged. The stopped original
manifest is not rewritten or reactivated. No new-run support is implemented here.

## Offline evidence

Existing baseline: 3 evidence/provider checks passed in 0.89 seconds. New checks first
reproduced 7 failures with 28 passing in 2.82 seconds: missing stored identity fields
and six missing/foreign binding variants that previously formed request bytes. After
the minimal repair, all 65 focused evidence/Claude/provider/live-budget/live-demo checks
passed in 32.45 seconds.

The real PostgreSQL test inserts two foreign receipts, each sharing only one identity,
and proves neither reaches the selected evidence or frozen request. The matched receipt
retains both persisted IDs in request bytes and the manifest; a reference-label canary
stays absent. Parameterized checks cover both fields with missing, null and foreign
values. Empty evidence still builds the unresolved request. Existing stopped-study,
wrong-manifest and source-change regressions remain in the verification set.

Candidate canonical verification passed **117 tests in 95.18 seconds**, plus lock,
lint and format, receipt `verify-fa4fe5f08a2a472fbfa8208c79b0728a`.
Linux runtime source fingerprint:
`cb46e62d3fccdfba586f0603a4bc96f0821c98afaadd431b526b0a40dad9dcb6`.
One fresh read-only review of `faa825b..f140404` found zero Critical, Important or new
Minor findings. It checked all five focus conditions and the separate follow-up proposal.
Primary `main` fast-forwarded from `faa825b` to `50e3a1c`. Fresh primary canonical
verification passed **117 tests in 117.34 seconds**, plus lock/lint/format, receipt
`verify-84395c7e7d5b4bc39082e4bcb4431e12`, with the same runtime fingerprint above.
The original 24-submission controlled load experiment was not repeated.
Full-suite fixtures and transport stubs are offline checks, not new model evaluations.

## Limits and next decision

No provider credential was read/copied, no authenticated preflight or inference was
made, and the real study database was not opened or changed during this repair. Only
the disposable `p19-check` database was used. Actual model benefit remains untested.

A separate portfolio proposal describes a distinct fresh three-case run, preserving
the original stopped history and charging all calls to the same cumulative USD2 meter.
It needs new additional-call approval and a tested minimal schema/orchestration extension
before activation. The original remaining balance does not authorize continuation.
Public publication, hosted CI and cloud provisioning remain outside this change.

The existing deferred Minors remain: explicit follow-up/recovery trace links and
partial CLI progress retention after timeout/nonzero exit. Neither affects the scope
of this receipt-context repair.

Review rulings: actual model improvement awaits an approved sample; migration/runtime
correctness awaits implementation of that proposal; current provider availability and
real-ledger reconciliation await approved preflight (public rates were rechecked today).
Those uncertainties can stop the proposed run, not justify a scope/rate change. Existing
diagnostic Minors stay deferred, so some context still requires persisted-event readback.
Production-scale readiness is excluded by the user's scope, so no such claim follows.
Primary integration verification was required after review and passed; a failure would
have retained the checkout/branch. Git worktree fallback was used after the native
tool rejected this product root; isolation metadata differs, not the implementation.
The direct proceed instruction authorized this named offline repair and proposal with
the existing local-main choice, with no paid/public side effects.

## Preservation and cleanup

All **206 private execution/configuration files**, including the task ledger and
candidate receipts, were copied and SHA-256 verified under primary ignored
`.local/pre-integration-receipt-2026-10-30-62f0973f`; a full archive recheck found zero
mismatches. Only local application configuration was included, with no provider key.
Primary verification has its separate original receipt under `.local/runs/`.
Historical live report/evidence, fixtures and study schema have no diff from `faa825b`.

After preservation and successful primary checks, unforced `git worktree remove`
removed the new checkout's files and registration, then reported permission denied
when deleting its empty root directory. Readback found zero remaining files. That
empty `.worktrees/receipt-context` directory and fully merged `codex/receipt-context`
branch were retained; no forced or alternative deletion was attempted. The old
`.worktrees/local` checkout, branch and scratch were not touched.

Final readback showed zero running `p19-demo`/`p19-check` containers and no listeners
on 8199/16699. Both database volumes remain. The owned temporary WSL shell was closed
normally. No public push, hosted CI, cloud provisioning or additional paid call occurred.
