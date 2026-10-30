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
Local integration evidence is recorded below after completion.
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
