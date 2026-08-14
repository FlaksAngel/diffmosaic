# Pilot v0.1 experiment records

This directory contains bounded raw results for source screening, environment
qualification and mutation execution. Exact source revisions, image identities
and test commands are in `corpus/pilot-v0.1.json`.

## Click declaration-order qualification

The source revisions are `00e592cea702e0b2caa0dee42489fdb1c22cd845` (base)
and `047adef258fc25566163ffc3efd14effc0ef7352` (head). The source project is
not vendored here.

| Record | Environment | Baseline | Interpretation |
| --- | --- | --- | --- |
| `click-declaration-order.json` | image `sha256:2d91ab…e177d` | failed | Excluded: DiffMosaic before 0.7.0 let pytest try to create its cache in the read-only workspace. |
| `click-declaration-order-attempt-2.json` | same image | failed | Excluded: the reviewed test command requires the `less` pager, absent from the minimal image. |
| `click-declaration-order-attempt-3.json` | image `sha256:477ba…0aa0` | passed in 10.922 s | Qualified baseline: 1953 passed, 24 skipped, 31000 deselected, 1 xfailed. |

The qualified image is
`diffmosaic/click-declaration-order@sha256:477ba5092a70eeea2cd79a54ddd5b924076024e548fe59cc8163598650e70aa0`.
It uses the reviewed `less` system package recorded in
`images/profiles-v0.1.json`; the generic recipe and base-image input are
described in `docs/image-provisioning-protocol.md`.

The mutation plan contains zero candidates because this particular production
diff has no changed comparison or Boolean connector supported by DiffMosaic
0.7.0. It is consequently recorded as an excluded source candidate, not a
mutation-adequacy study subject. The `click-declaration-order-screening.json`
record is the static pre-screen; the final execution report establishes a
reproducible qualifying baseline only. The raw JSON records contain bounded
test-output tails and were reviewed before inclusion.

## Flask automatic-options mutation result

The source revisions are `d8eaaba824655046958d1a97f11780de460c3271` (base)
and `a82e942870b6472bb40017349cca772c242eb1ad` (head). The eligible static
plan is preserved in `flask-automatic-options-screening.json`. Its two sites
are in `src/flask/cli.py::routes_command`: `==` to `!=` and `or` to `and`.

The trusted image was built from the fixed head checkout and the committed
`uv.lock`, using `python:3.11-slim@sha256:a630a63cdb314e2d138a2fca3e375e319e8568346ffafac5b980f888630ac4f1`.
The run records the final image identity
`diffmosaic/flask-automatic-options@sha256:d5b82d1e06f7581b6e09ec765537f20e6e39ad81d2f0f8a09120dc917cbd6552`.

`flask-automatic-options.json` records a passing baseline (495 passed in
6.27 s of pytest time; 8.156 s wall time). Both mutations were killed by the
full test command: the comparison mutation caused three `tests/test_cli.py`
failures and the Boolean mutation caused one. This gives mutation adequacy
`2 / (2 + 0) = 1.0` for this one revision. It is a per-revision observation,
not an estimate for Flask or Python projects generally; the protocol requires
at least six eligible study subjects before any aggregate interpretation.
