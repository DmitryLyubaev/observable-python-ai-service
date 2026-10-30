# Publication readiness

30 October 2026. The owner approved the prepared package. The repository is now public
at [DmitryLyubaev/observable-python-ai-service](https://github.com/DmitryLyubaev/observable-python-ai-service),
with secret scanning and push protection enabled before the approved source push.
[The initial exact-ref hosted run](https://github.com/DmitryLyubaev/observable-python-ai-service/actions/runs/41028172986)
passed 134 tests and lock/lint/format. The preparation evidence below remains dated;
actual publication results are recorded separately at the end.

The presentation adds an architecture/evidence README, CV/interview notes and one
offline GitHub Actions workflow. The current license-file state is retained: no
LICENSE file or new licensing terms are added. Application code, fixtures, dependencies,
container definitions, stopped studies and their measured reports are unchanged.

## Prepared checks

- Official checkout v7.0.1 was resolved to its full immutable commit SHA.
  [Checkout release](https://github.com/actions/checkout/releases/tag/v7.0.1).
- Portable actionlint 1.7.12 and Gitleaks 8.30.1 came from their official releases and
  were SHA-256 checked against the published checksums before execution. They are local
  review tools, not application dependencies or committed binaries.
- actionlint passed. The workflow uses Ubuntu hosted workers, read-only repository
  permission, no persisted checkout credential and controlled base Compose only. It
  receives no provider key. Receipts and JUnit totals go to job logs/run summary rather
  than uploaded artifacts; no cache, artifact storage or paid runner is requested.
  [GitHub billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
  distinguishes free standard public-repository runners and logs/summaries from stored
  artifacts. This preparation does not change an account-wide billing setting.
- The reachable history scan first flagged two environment-variable identifiers in
  code that rejects credential-bearing environments. Both exact source lines were
  inspected. `.gitleaksignore` contains only those historical fingerprints; it does
  not exclude files, rules or future findings. The reviewed scan passed.
- All commits use the personal author identity. No ignored credentials, raw `.local`
  evidence, worktrees or execution scratch are tracked. Local README/portfolio links
  resolve. The screenshot was visually inspected and shows the synthetic Jaeger demo.
- Tracked runtime-source digest remains
  `669f99160ff70b9e393835278a57182acc5a3e3c91b644076e56a20550c7430d`, matching the last
  134-test candidate/primary verification and actual follow-up. No new provider call
  or provider credential access is part of publication preparation.

## Fresh Linux verification

An exact Git archive of presentation commit `9b3a75a` was extracted into a fresh Linux
filesystem directory, without Windows working-copy files, credentials or ignored raw
artifacts. Setup generated fresh local-only credentials. A private Compose volume-name
override isolated this cold test database while keeping the workflow's setup/verifier/
cleanup commands and the application configuration unchanged. Both existing project
database volumes were retained.

The canonical verifier passed **134 tests in 96.19 seconds**, plus lock/lint/format,
receipt `verify-af4da5345d63428b83ccbe1d9de964ac`. Its runtime-source digest equals the
recorded `669f9916...` source above. The temporary owned test volume was removed after
copying the complete private evidence; no original study was opened or reset.

The final workflow replaces artifact upload with receipt logging/run summary. Its exact
summary shell block was executed directly against those fresh Linux receipts: success,
134 tests, zero failures/errors/skips and the correct source were recorded. actionlint
passed again. This reporting-only change leaves the tested verifier/application bytes
unchanged. At preparation time this local verification did not establish hosted delivery;
the actual post-approval hosted result is recorded below.

## Independent review

One fresh read-only review of `5024174..a62e762` found zero Critical, zero Important and
one presentation Minor. The reviewer independently checked the source/history identities,
cold Linux evidence, workflow and claims. No fix pass or second review occurred.

Deferred presentation Minor: the README load table's maximum of one provider call means
one **concurrent active** provider call, with eight attempts total in that historical
sample. The underlying measured report is explicit. Four previously deferred runtime/
test Minors stay unchanged. No new provider quality or production claim follows.

Execution decisions: existing proceed/Native/local-main authorization covers this local
package, with public action reserved for the final named-ref approval. Git fallback
changes only isolation metadata. Documentation/configuration checks use direct tooling
and existing tests rather than mirror unit tests. Job logs/summaries replace uploaded
artifacts, so there is no downloadable hosted artifact. Hosted checkout/delivery still
requires the actual run; current target/account facts are not future account-wide
guarantees. Model quality/settlement/improvement, general production/adversarial capacity
and prior diagnostic limits remain outside this preparation. Closeout must verify the
resulting ref/archive identities before outward approval.

## Local integration and preservation

Primary `main` fast-forwarded from `5024174` to `5e9abd8`. Integrated workflow lint,
reachable-history scan, links, author/committer identity, source equality and exact
executed summary-block checks passed. Runtime/fixture/container/dependency files have
no diff from `5024174`; the cold Linux 134-test receipt remains applicable. Reporting
metadata does not require repeating that unchanged full suite.

All **246 private preparation files** were copied and SHA-256 checked under ignored
primary `.local/pre-publication-2026-10-30-a2129b14`, with zero mismatches on full recheck.
The cold Linux evidence copy separately verified 192 files with zero mismatches. Its
canonical receipt directory is also preserved under primary `.local/runs/`. No provider
credential was read/copied or included in these preparation artifacts.

Unforced Linux snapshot cleanup reached write-protected files and was interrupted,
leaving the owned `/tmp/p19-publication-20261030-1fd730ae` snapshot retained (294 files
on readback). Its temporary Docker test volume was already removed after preservation.
Unforced Git worktree removal deleted the new checkout's files/registration, but Windows
refused the empty root directory; zero files remained. The empty `.worktrees/publication`
directory and fully merged `codex/publication` branch remain. No forced cleanup or
retry against older retained paths occurred.

Final readback showed no owned running containers or 8199/16699 listeners. The two
existing `p19-demo_database` and `p19-check_database` volumes remain. The temporary WSL
shell was closed normally. That preparation made no remote/public/hosted or paid/cloud
change. The exact approved ref/tree and local review bundle are named in the separate
owner proposal; the later authorized publication follows.

## Approval boundary

The recorded owner approval covers creating this named public repository, enabling its
secret scanning/push protection, pushing only reviewed `main` and allowing the prepared
offline workflow to run. It includes source history, synthetic fixtures, safe dated
reports/traces and the historical screenshot, not ignored local configuration, raw
provider receipts, protected keys, worktrees or database volumes. No cloud deployment,
paid model evaluation, new study or additional budget is included.

Both failed studies remain explicit. The latest model sample stopped on its first
missing-citation result, leaving the receipt case unrun. No public wording claims
successful model quality, human validation, improved receipt behavior or production use.
Four previously deferred diagnostic/test Minors remain documented in the follow-up report.

## Approved public delivery

Dmitry approved publication of `c5583e293918637ca98a7bd1ab368605d10c89be`, tree
`92a1321e8671d1be6ce7a945468b64bcbbf0b132`, with 102 tracked files/31 reachable commits.
The personal account, target absence and exact clean payload were rechecked before
creating the named empty public repository. Secret scanning and push protection were
enabled and read back before pushing only reviewed `main`, without force. Existing
license-file state was retained.

Initial hosted run **41028172986** succeeded on that exact commit: 134 tests passed in
37.57 seconds, zero failures/errors/skips, plus lock/lint/format. Its runtime-source
digest equals `669f99160ff70b9e393835278a57182acc5a3e3c91b644076e56a20550c7430d`.
Generated configuration, verification receipt/JUnit summary delivery and owned-container
cleanup all passed on the hosted runner. Anonymous repository, README, source and
historical PNG reads succeeded; downloaded file hashes matched the reviewed files.

This follow-up changes only publication status, verified links/badge and safe delivery
metadata. Current reporting-ref CI is visible through the workflow badge/run history;
the final exact reporting ref is verified in the portfolio closeout. No application,
workflow, fixture, dependency, license, provider call or cloud resource changed during
publication. Both unsuccessful model samples and all previously stated limits remain.
