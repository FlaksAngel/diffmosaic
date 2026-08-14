# DiffMosaic project charter

## Working title

**DiffMosaic: Detecting Test-Evidence Gaps in Python Pull Requests**

## Problem

Line coverage and the mere presence of a changed test file are weak evidence
that a pull request's new behaviour is actually tested. A changed condition,
validation path, or exception branch can be executed without an assertion that
would distinguish its old and new behaviour.

## Objective

Build an open, reproducible analyser for Python pull requests that combines
diff-aware static information, test-change evidence, execution coverage, and
diff-local mutation testing into an explainable test-evidence report.

## Version 0.1 scope

- Local Git repository only.
- Python source files only.
- AST mapping from changed new lines to functions, async functions, and class
  methods.
- Explicit classification of production versus test paths.
- Safe reading of an already generated `coverage.py` JSON artefact.
- Safe planning of bounded, diff-local comparison and boolean mutations.
- Deterministic JSON and Markdown reports.

## Explicit non-goals for version 0.1

- Generating tests.
- LLM inference or a chat interface.
- Supporting multiple languages.
- Running untrusted code.
- Running mutation candidates before an isolated execution protocol exists.
- Claiming a test is "correct" or "complete".

## Research questions

1. How often do changed Python symbols lack execution evidence from a test
   suite?
2. How often do changed test files provide evidence related to changed
   production symbols?
3. Can a transparent Test Evidence Gap Index (TEGI), calculated without using
   mutation results, rank pull requests with low diff-local mutation adequacy
   above simple baselines?

## Planned primary outcome

For each analysed pull request, DiffMosaic will publish a report containing
the source revisions, changed symbols, raw evidence signals, exclusions, and
the exact analyser version. A later research data release will also contain
the protocol and aggregate, non-sensitive results.

## Success criteria for the first milestone

- `diffmosaic analyze` maps changed lines to Python symbols in fixture
  repositories.
- Tests cover normal, renamed, added, deleted, test, and unmapped source
  changes.
- Results are deterministic for identical source revisions.
- The tool never writes to the analysed repository.

## Risks and controls

| Risk | Control |
| --- | --- |
| Scope expands to an all-language review bot | Freeze Python + pytest scope until the first dataset release. |
| Coverage is mistaken for behaviour verification | Report it as one signal, never as proof of adequacy. |
| Mutation tests are slow or unsafe | Run later in isolated containers, without network, secrets, or write access to the source checkout. |
| Dataset is biased toward one repository | Split evaluation by repository and record inclusion/exclusion rules before the main collection. |
| Results look stronger than the evidence permits | Report inconclusive executions and threats to validity explicitly. |
