# attrs `drop-python-39`: preliminary study record

## Status

This is one complete `study` record in the v0.2 manifest. Its subject list is
still `preliminary`, so it is not aggregated and does not support a general
claim about DiffMosaic. The command, image, limits and static-selection rule
were recorded before the test and mutation outcomes were interpreted.

## Fixed inputs

- Public repository: `https://github.com/python-attrs/attrs` (MIT).
- Revisions: base `c1c1e0e25f855be68caf1d1a1dfa832a25acbf58`; head
  `9b98a730bf71cabae9bcedb8a3aac72289c23733`.
- Operator set: `v0.2`.
- Command: `python -m pytest`.
- Image: `diffmosaic/attrs-drop-python-39:9b98a73`, pinned in the manifest by
  its recorded SHA-256 identity.
- Isolation: no network, read-only source and root filesystem, one CPU, 1 GiB
  memory, 256 processes, 120 seconds per invocation.

## Recorded outcome

The baseline passed in 13.047 seconds. The saved plan contains one mutation in
`src/attr/_make.py::attrs.wrap`, replacing `and` with `or` at line 1602. It was
killed in 12.907 seconds, so this single-symbol observation has mutation
adequacy `1.0`.

The independent coverage run completed 1401 tests, with 9 skips and 1 expected
failure. All six changed symbols have available coverage evidence, and the
review queue assigns each a low score. This is one observation, not evidence
that the prioritisation method is broadly effective.

## Integrity

`corpus/study-v0.2.json` records SHA-256 values for `analysis.json`,
`priority.json`, `coverage.json`, `mutation-plan.json`, and
`mutation-results.json`. Run the following command to verify them without
executing attrs:

```powershell
diffmosaic corpus-validate --manifest corpus/study-v0.2.json --verify-artifacts --format markdown
```
