# Local main integration

30 October 2026, Australia/Brisbane. Bounded synthetic CV/portfolio demonstration.

Dmitry selected option 1, local integration. The primary checkout at
`E:\Projects\observable-python-ai-service` fast-forwarded `main` from `d9c3aa1` to
`5aef63d`. The final integration commit adds the packaging correction, verifier
reporting fix and this record. No remote is configured and nothing was pushed.

## Preservation and packaging

Before integration, 196 private evidence/configuration files were copied into ignored
`.local/pre-integration-2026-10-30-3b75e9bd`. All 196 SHA-256 hashes were checked again
after integration, with zero mismatches. The primary `.env` matches its archived copy.
The first incomplete snapshot is also retained, with its incomplete-status record.
No secret values or raw diagnostic exports are included in this document.

The retained nested worktree exposed a packaging gap: `.dockerignore` did not exclude
`.worktrees`. An isolated Docker context probe using only dummy files reproduced the
inclusion, then verified exclusion after adding that rule. The actual private worktree
was excluded before the primary application build.

## Verification and retained failures

The first primary-checkout attempt lost its Docker socket during a WSL restart. Two
subsequent standard checks reached pytest but exceeded the unchanged 240-second bound.
Their logs are retained. The original harness captured output in memory, losing partial
pytest output and the failed receipt on timeout. A direct verbose diagnostic passed all
53 tests in 66.98 seconds; a separate nested diagnostic with stack capture passed the
four checks and 53 tests in 66.03 seconds. Those altered diagnostic invocations are not
reported as successful standard-command runs. The original timeout cause is unproven.

The reporting defect was reproduced with a new test, then fixed: each check now writes
directly to its log, preserves its actual exit status and returns 124 with
`check_timeout` on expiry. The existing verifier records that as a failed receipt.
The focused regression covers successful, unsuccessful and timed-out subprocesses and
passed after the fix. The standard command, pytest assertions and 240-second limit are
unchanged. No application lifecycle/provider module changed during integration.

Final standard-command results and the safe receipt are recorded in
[integration evidence](evidence/integration.json).
The unchanged canonical command passed lock, lint, format and **54 tests in 70.77
seconds**, exit 0. Receipt: `verify-d2c812b0a0eb493e8fbdc369f0c25b91`.
Source fingerprint: `9e239cc96914b2f3bc05fc66494f3f10d85be611766f303144762bf93ef52c15`.
The fingerprint changed because the verifier and its regression test are included.
This fingerprint uses the canonical Linux path ordering. A native Windows check using
default `Path` sorting differed; recomputing the same file bytes in Linux lexical order
matched the canonical receipt. Cross-platform default-sort identity is not claimed.

## Scope and retained material

The original 24-submission load sample was not repeated. Existing business and failure
demos remain bound to their documented historical fingerprints. No real provider call,
paid evaluation, cloud resource, hosted CI or public publication occurred.

The `codex/local-demo` branch, worktree, ignored scratch and both database volumes remain
retained. A prior automatic approval review rejected a combined monitor-termination and
scratch-deletion command as "blocked by policy". It was not retried. The old read-only
monitor was no longer running after the later WSL restart; no replacement kill or scratch
deletion was attempted. The temporary foreground WSL shell used for integration is
closed normally after verification.
Final readback found zero running `p19-check`/`p19-demo` containers, zero listeners on
8199/16699 and the two retained database volumes.

The existing deferred Minor remains: follow-up/status/cancellation/recovery observations
use persisted job IDs without universal explicit trace links. Real-model usefulness,
human acceptance, public visibility and production operation remain unproven.
