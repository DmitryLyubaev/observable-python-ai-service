# Publication readiness

30 October 2026. This package is prepared for owner review. The proposed repository is
`DmitryLyubaev/observable-python-ai-service`, public `main`; it has not been created or
pushed. Hosted CI remains unproven until an approved push runs the workflow.

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
unchanged. Local verification is separate from hosted Actions checkout/run-summary
delivery, which must be observed after actual publication.

Independent review and final payload/preservation identity are recorded after completion.

## Approval boundary

The final owner decision covers creating this named public repository, enabling its
secret scanning/push protection, pushing only reviewed `main` and allowing the prepared
offline workflow to run. It includes source history, synthetic fixtures, safe dated
reports/traces and the historical screenshot, not ignored local configuration, raw
provider receipts, protected keys, worktrees or database volumes. No cloud deployment,
paid model evaluation, new study or additional budget is included.

Both failed studies remain explicit. The latest model sample stopped on its first
missing-citation result, leaving the receipt case unrun. No public wording claims
successful model quality, human validation, improved receipt behavior or production use.
Four previously deferred diagnostic/test Minors remain documented in the follow-up report.
