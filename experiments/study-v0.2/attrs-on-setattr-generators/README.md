# attrs `on-setattr-generators`: preliminary study record

## Status

This is the second complete `study` record in the preliminary v0.2 corpus. It
is not pooled into an aggregate result until the entire subject list is frozen.
The revision and full test command were selected before execution through the
committed newest-first static screen.

## Fixed inputs

- Repository: `https://github.com/python-attrs/attrs` (MIT).
- Revisions: base `d3a98cf05ab15769003dcca3eae91cdd6504b83b`; head
  `4b5b295bb815bf845fa3570bf63781a88212db40`.
- Operator set: `v0.2`; command: `python -m pytest`.
- Image: `diffmosaic/attrs-on-setattr-generators:4b5b295`, identified by the
  exact SHA-256 value in the manifest.
- Isolation: no network, read-only source/root filesystem, one CPU, 1 GiB
  memory, 256 processes and a 120-second test limit.

## Recorded outcome

The baseline passed in 13.000 seconds. The plan contains one mutation in
`src/attr/_compat.py::_lazy_is_generator.is_gen`, replacing `not in` with `in`
at line 121. The test suite killed it in 14.547 seconds, giving adequacy `1.0`
for that one mutated symbol.

The independent coverage run completed 1396 tests, with 10 skips and one
expected failure. The report also identifies several other changed symbols
with no executed changed lines; these receive medium review priority. The
single killed mutation does not prove those other symbols have sufficient tests.

## Integrity

The manifest pins the SHA-256 values of every required artifact in this
directory. Verify them without executing attrs:

```powershell
diffmosaic corpus-validate --manifest corpus/study-v0.2.json --verify-artifacts --format markdown
```
