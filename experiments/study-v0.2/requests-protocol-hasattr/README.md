# Requests `protocol-hasattr`: recorded exclusion

## Status

This public revision passed the outcome-blind static screen but is retained as
an `excluded` v0.2 subject. It was not replaced after execution. The exclusion
is about the pre-recorded full test command under the study's safety policy,
not about whether the source change is important.

## Fixed inputs and observed baseline

- Repository: `https://github.com/psf/requests` (Apache-2.0).
- Revisions: base `6f205ff422bccd5e4c4fc0b64c5f3e7df5181db6`; head
  `6f66281a1d6326b1b9c4ac09ca30de0fc4e6ef43`.
- Operator set: `v0.2`; saved plan: two mutations.
- Command: `python -m pytest`.
- Image: `diffmosaic/requests-protocol-hasattr:6f66281` with the recorded
  image identity in `images/profiles-v0.2.json`.
- Isolation: no network, read-only source/root filesystem, one CPU, 1 GiB
  memory, 256 processes and a 120-second limit.

The baseline ran for 81.609 seconds. It had 615 passes, 15 skips, one expected
failure, and four failures. The failures are timeout tests that deliberately
connect to `10.255.255.1`; this is incompatible with the intentional
`network=none` rule. DiffMosaic therefore executed no mutant and did not
produce a mutation-adequacy value.

## Why this remains public

`mutation-plan.json` and `mutation-results.json` are kept beside this note.
They show the exact screened mutations and the failed baseline. Removing this
subject or substituting a more convenient revision would bias the sampling
frame. No coverage, priority, or aggregate result is claimed for this
exclusion.
