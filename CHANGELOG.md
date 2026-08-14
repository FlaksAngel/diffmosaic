# Changelog

All notable changes to DiffMosaic are documented here.

## 0.3.0 — 2026-08-14

- Added opt-in Docker execution for planned mutations.
- Runs each baseline/candidate in a fresh temporary `git archive` workspace.
- Requires a prebuilt local image and records bounded experiment JSON.
- Added isolation controls and an execution protocol.

## 0.2.0 — 2026-08-14

- Added a safe, deterministic `mutate-plan` command for diff-local Python
  mutation candidates.
- Added comparison-boundary and Boolean-connector mutation operators.
- Added candidate metadata linking each mutation to changed source and its
  enclosing Python symbol.
- Kept mutation execution out of scope until isolated runner controls exist.

## 0.1.0 — 2026-08-14

- Initial diff, AST, and coverage-artifact analysis prototype.
- Added JSON/Markdown reports, documentation, tests, and CI.
