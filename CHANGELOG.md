# Changelog

All notable changes to DiffMosaic are documented here.

## 0.10.0 - 2026-08-14

- Recorded and validated the Docker working directory (`/workspace` or `/tmp`)
  as a frozen execution control, while preserving the read-only source mount.
- Accepted empty `executed_lines` lists and the `0` sentinel emitted by
  `coverage.py` for measured files without executable statements.
- Extended v0.2 image profiles with reviewed setuptools-scm version inputs
  for source trees whose build context deliberately excludes `.git` metadata.
- Materialised in-archive Git symbolic links as contained files or directories
  for mutation workspaces, while continuing to reject external link targets.
- Added versioned mutation-operator sets: the reproducible legacy `v0.1` set
  and the extended `v0.2` set.
- Added schema `0.2` study manifests with local artifact checksums, frozen
  execution limits and reviewed equivalent-mutant exclusions.
- Added `evaluate` for deterministic symbol-level study tables and baseline
  comparison, plus opt-in `reproduce` for a frozen study subject.
- Added `screen` for an auditable, newest-first static scan of a bounded local
  Git history before environment preparation or mutation execution.

## 0.9.0 - 2026-08-14

- Added a reviewed, narrowly scoped `setuptools-scm` version input to image
  profiles for projects whose editable build cannot access Git metadata in a
  Docker build context.

## 0.8.0 - 2026-08-14

- Added validated mutation-screening metadata and an explicit `excluded` corpus
  role so zero-site source candidates remain auditable but cannot be mistaken
  for mutation-adequacy observations.
- Added the first eligibility-screened Flask candidate and preserved screening
  reports for all initial source candidates.

## 0.7.0 - 2026-08-14

- Redirected pytest's cache to the sandbox `/tmp` filesystem so read-only
  workspaces do not turn cache warnings into baseline failures.

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
