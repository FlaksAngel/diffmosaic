# Pilot v0.1: Click declaration-order qualification

This directory preserves all runs used to qualify the Click subject. The
source revisions are `00e592cea702e0b2caa0dee42489fdb1c22cd845` (base) and
`047adef258fc25566163ffc3efd14effc0ef7352` (head). The source project is not
vendored here; its URL and exact revisions are recorded in
`corpus/pilot-v0.1.json`.

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
0.7.0. Therefore its mutation adequacy is `null`: this run establishes a
reproducible qualifying baseline, not evidence for or against mutation
effectiveness. The raw JSON records contain bounded test-output tails and were
reviewed before inclusion.
