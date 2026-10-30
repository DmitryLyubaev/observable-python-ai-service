# Publication readiness

30 October 2026. This package is prepared for owner review. The proposed repository is
`DmitryLyubaev/observable-python-ai-service`, public `main`; it has not been created or
pushed. Hosted CI remains unproven until an approved push runs the workflow.

The presentation adds an architecture/evidence README, CV/interview notes and one
offline GitHub Actions workflow. The current license-file state is retained: no
LICENSE file or new licensing terms are added. Application code, fixtures, dependencies,
container definitions, stopped studies and their measured reports are unchanged.

## Prepared checks

- Official checkout v7.0.1 and upload-artifact v7.0.2 releases were resolved to full
  immutable commit SHAs. [Checkout release](https://github.com/actions/checkout/releases/tag/v7.0.1),
  [artifact release](https://github.com/actions/upload-artifact/releases/tag/v7.0.2).
- Portable actionlint 1.7.12 and Gitleaks 8.30.1 came from their official releases and
  were SHA-256 checked against the published checksums before execution. They are local
  review tools, not application dependencies or committed binaries.
- actionlint passed. The workflow uses Ubuntu hosted workers, read-only repository
  permission, no persisted checkout credential, controlled base Compose only and seven
  explicitly named verification artifact patterns. It receives no provider key.
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
  or credential access is part of publication preparation.

Fresh Linux checkout verification, the independent review and final payload identity
will be recorded after completion. Local verification is separate from hosted Actions
checkout/artifact delivery, which must be observed after actual publication.

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
