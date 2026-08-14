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

## pytest option-destination baseline exclusion

The static plan for `8d40684d1f997e62758785aebb3132c2f5b712e1` to
`532b20103ecf9972f752353f20088c5cc878003b` contained two eligible sites and
is preserved in `pytest-option-destination-screening.json`. The image build
was itself reproducible only with the reviewed
`SETUPTOOLS_SCM_PRETEND_VERSION=9.2.0.dev0` input, whose final identity is
`diffmosaic/pytest-option-destination@sha256:6ab76681451d2b71132f568ce8b9ba39ed987a2ff481643f1850c7578be1eb0e`.

`pytest-option-destination.json` records the unsuccessful baseline rather than
hiding it. `setuptools-scm` generated `src/_pytest/_version.py` during the
image build, but the file is untracked and therefore absent from the clean
runtime `git archive`; import then raises `ModuleNotFoundError`. DiffMosaic did
not inject that generated file into the archive, and it skipped both mutations.
This subject is excluded from mutation-adequacy analysis under the documented
runner scope.

## Click color-validation mutation result

The source revisions are `7925a3410d7098c28cfca3b2baa6c852666bbd14` (base)
and `07c909f23f0f83b5ca137c167b9a134d66201f67` (head). The static plan in
`click-color-validation-screening.json` identifies five changed Boolean or
comparison sites in `src/click/termui.py::_interpret_color`.

`click-color-validation.json` records a passing full-suite baseline: 1749
passed, 24 skipped, 31000 deselected and 1 xfailed in 8.06 s of pytest time
(11.125 s wall time). All five mutations were killed, giving `5 / (5 + 0) =
1.0` for this revision. The failures are concentrated in the changed
`tests/test_utils/test_style.py` behaviour: the five mutants produced 9, 37,
28, 13 and 10 failures respectively.

The exact runtime image is
`diffmosaic/click-color-validation@sha256:80f9c137b1a8669e26a81f2bb861988e6b663282e437d2f860a540ec92a4fca2`.
As with the Flask result, this is a per-revision observation. It must not be
pooled into a conclusion while the pilot has only two study observations from
one maintainer community.

## Textual multiple-keys image-preparation exclusion

`textual-multiple-keys-screening.json` records nine eligible static mutation
sites for the fixed Textual revision. It was not executed. Although the project
has `uv.lock`, its test dependencies are declared in a legacy Poetry group,
which the deliberately narrow `uv sync --locked --group` image recipe does not
interpret. The attempted image preparation produced no image and no baseline;
the subject is recorded as an exclusion rather than silently dropped or built
using an unreviewed second dependency manager.
