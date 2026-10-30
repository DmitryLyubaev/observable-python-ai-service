# Local integration of the live extension

30 October 2026, Australia/Brisbane. The existing option-1 local integration preference
was preserved; no public push or remote repository was created.

Primary `main` fast-forwarded from `e3e0bed` to `b545051`. Implementation correction is
`ce64c13`; subsequent reporting preserves the stopped sample rather than claiming a
three-case success. Primary-checkout canonical verification passed **109 tests in
93.75 seconds**, plus lock/lint/format, receipt
`verify-57f3042ae6eb4373af8e4120a77eb527`. Its Linux runtime fingerprint matches the
review-corrected candidate and actual live images:
`b6f775dd720b2e2e861717b76ee97cb5cc6511d621f76d8cebde926fc1fe55ac`.
Post-merge checks used the controlled test path and made no additional paid calls.

Before cleanup, **614 private evidence/configuration files** were copied and SHA-256
verified under ignored `.local/pre-integration-live-2026-10-30-4b631438`. A later full
archive recheck again found zero mismatches. Live runtime evidence is also preserved at
its original relative `.local/live/p19-real-20261030/` paths in the primary checkout.
Six hundred `.local` files were copied or already matched in that active location.
One generic test diagnostic trace path conflicted: its source version is preserved in
the snapshot, and copying did not overwrite the primary destination. Canonical tests
regenerate that diagnostic path normally. Original immutable run receipts remain retained.

The primary `.env` matches the archived execution configuration. The provider key was
preserved and hash-checked separately in owner-restricted `.secrets`, excluded from git
and Docker context. It was never copied into the shared `.local` archive. No credential
value or digest is published here.

After successful verification and archive checks, the new `.worktrees/live` checkout
and fully merged `codex/live-demo` branch were removed without forcing removal. The
older `.worktrees/local` / `codex/local-demo` and its ignored scratch remain retained.
The earlier rejected monitor/scratch cleanup was not retried or worked around.

Final readback showed zero running `p19-demo`/`p19-check` containers, zero listeners on
8199/16699, and retained `p19-demo_database` / `p19-check_database` volumes. The temporary
foreground WSL shell was closed normally. The demo volume preserves the stopped study,
two consumed slots, USD0.0003902 estimated known usage and zero unresolved reservations.

[Live report](live-report.md) and [safe integration evidence](evidence/live-integration.json)
give the exact outcome and provenance. One case passed, one failed semantic validation,
and one was not run. The response cited missing identity bindings in the receipt evidence;
an enriched-context fix and any replacement sample remain untested and uncommissioned.
The unused USD1.9996098 allowance is not permission to resume the stopped study.

Public portfolio publication/hosted CI and another paid-study decision remain separate.
