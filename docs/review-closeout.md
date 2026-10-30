# Independent review and correction closeout

30 October 2026. One fresh read-only reviewer examined `d9c3aa1..2b3fd7a` against the
approved local design/plan, tests and retained evidence. It found no Critical,
three Important and two Minor findings. The author made one correction pass at
`362b193`; the corrected canonical command passed 53 tests, lint/format and lock checks.
Three CLI business cases and five failure/recovery demonstrations passed again at the
corrected runtime fingerprint. There was no second review and no repeated load sample.

| Finding | Verified disposition |
|---|---|
| Important: framework spans captured raw unhandled exception messages/chained causes | Reproduced with an in-memory API/exporter canary probe. User middleware now contains the error and retains only its safe class. API admission and late-stream error paths, plus Celery logs, are checked. |
| Important: a deadline could expire during dispatch transaction/bookkeeping and pass a negative provider budget | Reproduced at three scheduling boundaries. Dispatch transactions now accept the deadline, database lock/statement/pool waits are bounded, and invocation rechecks a positive remaining budget. Committed intents remain conservatively unknown when the deadline expires; known late replies retain usage but cannot publish success. Actual lock-wait and late-reply tests pass. |
| Important: a failed load sample could disappear without reserving its output name | The load run now exclusively reserves an intent before work, journals responses/safe transport failures as they occur, preserves available terminal readbacks and writes an immutable failed/passed receipt. Partial-failure and name-reuse tests pass. The original successful sample remains untouched. |
| Minor report/coverage gap: API process restart was not actually demonstrated | Root regraded this as an Important evidence obligation because approved A8 and the report already claimed it. A new actual Uvicorn subprocess kill/restart test retrieves/replays the same job while the real worker continues, with one provider attempt. Existing behavior passed this added acceptance check without an application behavior change. |
| Minor: follow-up/recovery trace links | Deferred. Status/cancellation/recovery database observations have job IDs, but their server/recovery spans lack explicit links to the admission trace. The report narrows the tracing claim accordingly. |

Original failing checks remain private. Eight new RED cases cover the corrected
defects; additional checks cover already-safe Celery/stream handling and the actual
API restart. No Critical/Important finding remains unaddressed by the author. This is
regression verification of the correction pass, not an independent re-review verdict.

## Decisions on the reviewer's set-aside behaviors

Each entry records the retained behavior, why it is acceptable for this bounded demo,
and its practical cost if the assumption is wrong.

1. Admission races/lost responses: retain the transaction lock and key-before-capacity
   ordering, checked with concurrent tests. Cost if wrong: duplicate jobs or admission.
2. Cancellation/result/retry races: retain shared transactional guards and tested
   dispositions. Cost if wrong: an unwanted attempt or successful result after cancellation.
3. SSE integer spellings: accept Python's parsed nonnegative integer cursor when within
   the committed sequence. Cost: clients needing canonical lexical spelling must normalize.
4. Recovery refusal variants: retain inspected exact-owner guards and current tests.
   Cost if an untested variant is wrong: recovery could be refused or mis-scoped.
5. Concurrent unrelated manual Docker mutation: outside the controlled lifecycle proof.
   Cost: concurrent manual changes can invalidate that proof; no failover claim follows.
6. Real provider/model/billing/429 semantics: remain separately deferred. Cost: these
   outcomes cannot be claimed from the controlled adapter.
7. Multiple workers, automatic failover, HA and large histories: outside the supported
   one-worker small demonstration. Cost: no scaling/capacity claim beyond the sample.
8. Versioned SQL, dictionary views, module lifecycle, Jaeger v3 and scoped cleanup:
   retain the earlier recorded rulings. Their evolution/type/command/readback/retention
   costs are listed in [execution record](execution-record.md).
9. Admission response resource URLs: the CLI derives the documented stable routes.
   Cost: another client must construct them; hypermedia discovery is not delivered.
10. Per-job configuration identities and broader telemetry-loss accounting: frozen run
    manifests/profile observations bind this sample. Cost: no universal per-job telemetry
    completeness/accounting claim.
11. Fingerprint ordering: POSIX/Linux is canonical and reproduces the recorded hash.
    Cost: direct native-Windows Path ordering is not a comparable digest.
12. Reviewer did not execute acceptance or final cleanup: author-owned canonical and
    runtime-closeout evidence provide those checks. Cost: these are not independently
    rerun acceptance results.

The implementation remains local and unpublished, with deterministic provider behavior.
No cloud, paid inference, real customer data or production reliability claim is added.
