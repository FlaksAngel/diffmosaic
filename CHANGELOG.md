# Changelog

All notable changes to DiffMosaic are documented here.

## 0.6.0 - 2026-08-14

- Added the explainable `prioritize` command for deterministic review queues.
- Added a fixed-rule protocol that distinguishes evidence gaps from defect
  predictions and exposes every score contribution.

## 0.5.0 - 2026-08-14

- Added reviewed, lock-file-based image profiles for the three public pilot
  candidates.
- Added a separate image-provisioning protocol; DiffMosaic still never builds
  images or executes target-project Dockerfiles.

## 0.4.0 - 2026-08-14

- Added data-only pilot-corpus validation with exact commit, image-identity and
  command requirements.
- Added a calibration manifest and a preregistered pilot-study protocol.
- Corrected documentation to distinguish ordinary static analysis from the
  explicitly enabled isolated execution path.

## 0.3.0 - 2026-08-14

- Added opt-in Docker execution for planned mutations.
- Runs each baseline/candidate in a fresh temporary `git archive` workspace.
- Requires a prebuilt local image and records bounded experiment JSON.
- Added isolation controls and an execution protocol.

## 0.2.0 - 2026-08-14

- Added a safe, deterministic `mutate-plan` command for diff-local Python
  mutation candidates.
- Added comparison-boundary and Boolean-connector mutation operators.
- Added candidate metadata linking each mutation to changed source and its
  enclosing Python symbol.
- Kept mutation execution out of scope until isolated runner controls exist.

## 0.1.0 - 2026-08-14

- Initial diff, AST, and coverage-artifact analysis prototype.
- Added JSON/Markdown reports, documentation, tests, and CI.
