# HTTPX `version-028`: development validation

## Status

This directory is an engineering validation of the DiffMosaic pipeline, **not
a study observation**. The v0.2 manifest still gives the subject role
`candidate` and the corpus status remains `preliminary`. Its data must not be
used in `evaluate`, in a table of research findings, or as evidence that the
prioritisation method works in general.

The distinction matters. The initial whole-suite qualification showed that a
networkless, read-only sandbox is not compatible with four unrelated HTTPX
tests. The focused test command was documented only after that discovery, so
its successful result is useful to validate the tool but not an outcome-blind
study result.

## Fixed inputs for this validation

- Repository and revision: public HTTPX revision
  `80960fa31918d7663c3f4c3ad61661cf0e80628f`, with parent
  `a33c87852b8a0dddc65e5f739af1e0a6fca4b91f`.
- Operator set: `v0.2`.
- Locally built image:
  `diffmosaic/httpx-version-028:80960fa`, identity
  `diffmosaic/httpx-version-028@sha256:25fa8f3a7594168566de00615d5a813ec3034a87199cdaeb95a2986e5e5b4433`.
- Test command: `python -m pytest /workspace/tests/test_config.py -q`.
- Work directory: `/tmp`; source remains a read-only `/workspace` mount.
- Isolation: no network, read-only root filesystem, no Linux capabilities,
  `no-new-privileges`, one CPU, 1 GiB memory, 256 processes and a 120-second
  limit for each invocation.

## Observations

`qualification-whole-suite.json` is deliberately retained. It records that
the default full suite had 4 failures and 1412 passes under the restricted
environment: network-dependent tests cannot resolve DNS, and a key-log test
tries to create a relative file in the read-only source mount. DiffMosaic did
not run any mutant after that failed baseline.

The focused development validation then ran 28 configuration tests. Its
baseline passed in 2.281 seconds. The static plan contains two changed-symbol
mutations in `httpx/_config.py::create_ssl_context`; both were killed by the
test command (2.110 and 2.125 seconds). The recorded mutation adequacy is
therefore `1.0` for this narrow validation only.

The independent coverage collection ran the same 28 tests. Of 34 changed
lines in `create_ssl_context`, 8 were executed. The priority report consequently
records partial changed-line execution and no changed test file. Mutation
adequacy and changed-line coverage are different signals, so neither replaces
the other.

## Files

- `qualification-whole-suite.json` — rejected full-suite qualification;
- `coverage.json` — independently generated coverage.py JSON;
- `analysis.json` — AST and coverage analysis of the pinned Git diff;
- `priority.json` — explainable review queue from that analysis;
- `mutation-plan.json` — two planned v0.2 mutations;
- `mutation-results-development.json` — passing baseline and two mutation
  results under the focused command.

All file paths inside the JSON reports are container paths such as
`/workspace/...`; no local user path is part of this public artifact set.
