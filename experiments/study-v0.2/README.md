# Study v0.2 artifacts

This directory contains outcome-blind static screens and clearly labelled
development qualifications for `corpus/study-v0.2.json`.

## Static screening

Each JSON file records a fixed newest-first, first-parent, non-merge history
window. A revision is eligible only when the v0.2 mutation plan includes at
least one candidate in a changed named Python symbol. The reports do not run
tests, construct images, generate coverage, or record mutation outcomes.

The preliminary registry retains the first two eligible revisions from each
report, except `jinja-screening.json`, which has only one eligible revision in
its 120-commit window. The manifest pins each report's SHA-256 and ordinal, so
validation can prove the selected commit was present before execution work
began.

Do not interpret these files as evidence that DiffMosaic ranks weak tests.
That claim requires a later frozen corpus with the five execution artifacts for
every `study` subject.

## Development qualification: HTTPX `version-028`

The local image for `httpx-version-028` was built from the pinned commit and
is recorded as `built` in `images/profiles-v0.2.json`. It is **not** a frozen
study image yet. An initial whole-suite qualification command was rejected:
four otherwise unrelated tests require either external DNS access or writing a
key-log file in the source directory, both intentionally disallowed by the
sandbox.

The candidate therefore remains `candidate`, and no outcome from that attempt
is used as research evidence. Before the next development validation, its
manifest now explicitly records a module-level command for the changed SSL
configuration function and `/tmp` as the container working directory. Source
code remains mounted read-only at `/workspace`; `/tmp` is a size-limited tmpfs.
The absolute test-file path makes this choice visible and reproducible. A
future result becomes a study artifact only after all five required artifacts
are generated, checksummed, and the subject list is frozen.
