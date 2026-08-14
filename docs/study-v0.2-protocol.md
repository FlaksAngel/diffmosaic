# Study v0.2 protocol

## Purpose

Study v0.2 evaluates whether the fixed, explainable DiffMosaic review score
orders changed Python symbols with weaker mutation evidence above a simple
repository-level baseline: **no test file changed**. It evaluates a frozen
tool version and frozen inputs; it is not a defect-prediction study.

The protocol deliberately separates three states:

| State | Meaning | Permitted commands |
| --- | --- | --- |
| `design` | Sampling and metrics are written down; no study claim exists. | `corpus-validate` |
| `preliminary` | Subjects are being prepared; results must not be aggregated. | `corpus-validate` |
| `frozen` | Subject list and all artifacts are fixed by checksum. | `corpus-validate --verify-artifacts`, `evaluate`, `reproduce` |

`corpus/study-v0.2.json` is currently `preliminary`: it contains seven
checksum-pinned sampled subjects from four independent public projects. Two
attrs subjects have the five required artifacts and recorded executions; one
Requests subject is retained as an explicit network-policy exclusion; the
remaining records are candidates or development qualifications. There is no
aggregate finding, and `evaluate` and `reproduce` reject a manifest until its
status is `frozen`.

## Research question and unit of analysis

The unit of analysis is a changed production Python symbol within one fixed
`(repository, base_commit, head_commit)` subject. A symbol becomes an
evaluation row only when its changed code has at least one planned diff-local
mutation.

**RQ1.** Does the predeclared DiffMosaic score rank changed symbols with weak
mutation evidence above the baseline `no_test_file_changed`?

The score is fixed in [review-prioritisation.md](review-prioritisation.md).
The baseline is intentionally simple and applies equally to every symbol in a
subject. No mutation outcome may be used by `prioritize` itself.

## Predeclared outcome

For each symbol, DiffMosaic calculates:

```text
mutation_adequacy = killed / (killed + survived)
```

Only `killed` and `survived` are conclusive. `timeout` and
`infrastructure_error` remain visible but do not enter the denominator. The
manifest fixes two parameters before outcomes are inspected:

- `weak_adequacy_threshold`: `0.8`; a symbol below this value is labelled
  `weak_test_evidence`;
- `minimum_conclusive_candidates`: `1`; fewer conclusive candidates produce
  no label and no ranking contribution.

`evaluate` reports rows, mean adequacy and tie-aware expected average precision
for both the DiffMosaic score and baseline. Equal scores are averaged over all
their possible internal orders, so subject identifiers cannot accidentally
improve either ranker. The metric is `null` if there is no weak-evidence row.
It is a descriptive comparison, not a statistical significance claim.

## Sampling and corpus size

Start with a reproducible sampling rule. `diffmosaic screen` records a bounded
newest-first first-parent non-merge history window and marks a commit eligible
when its static v0.2 plan has at least one site in a changed named Python
symbol. It neither executes code nor uses mutation outcomes. Record every
candidate and every exclusion; do not
replace a result after seeing its mutation outcome.

The committed preliminary frame applies that rule to four repositories: it
retains the first two eligible revisions per screen, except Jinja which has one
eligible revision in the bounded window. The exact reports are in
[`experiments/study-v0.2/`](../experiments/study-v0.2/). These entries are not
study observations until their runtime artifacts are preserved.

The minimum feasibility target is six eligible subjects from three independent
maintainer communities. The target for an empirical paper is 18–24 eligible
subjects from at least four communities, with both changed-test and
no-changed-test subjects represented. Exclusions are data: zero supported
sites, incompatible clean-archive runtime, unavailable dependencies, missing
license information and unstable tests must remain in the manifest with a
reason.

## Versioned mutation operators

The plan records `operator_set_version`; a study may use exactly one set.

| Set | Operators |
| --- | --- |
| `v0.1` | `==/!=`, `< / <=`, `> / >=`, `and/or` |
| `v0.2` | All `v0.1` operators, `is/is not`, `in/not in`, `+/-` |

Study v0.2 fixes `operator_set` to `v0.2`. Results made with v0.1 are useful
pilot evidence but must not be pooled with v0.2 results. Adding or changing an
operator requires a new study version.

Each `candidate` and `study` subject also pins its `screening_report` path,
SHA-256 and ordinal. Validation checks that the referenced static report uses
the same public repository, planner version and operator set, and contains the
exact base/head pair as an eligible symbol-level candidate.

## Required artifacts

Every `study` subject in a frozen v0.2 manifest references these repository
relative JSON artifacts and their SHA-256 digests:

1. `analysis` from `diffmosaic analyze`;
2. `priority` from `diffmosaic prioritize`;
3. `coverage`, produced independently in an authorised environment;
4. `mutation_plan` from `diffmosaic mutate-plan --operator-set v0.2`;
5. `mutation_results` from `diffmosaic mutate-run --operator-set v0.2`.

The manifest also records the Docker digest, test command, working directory,
candidate limit and sandbox limits. The mutation result must record the same
image identity, command, working directory, limits, passing baseline and exactly the candidate ids in the saved
plan. `corpus-validate --verify-artifacts` checks every local path, checksum,
base/head revision and operator-set version without executing code.

## Equivalent and duplicate mutants

A surviving mutant is not automatically a missing test. A reviewer may add a
`manual_mutant_assessments` entry with `classification` equal to `equivalent`
or `duplicate`, the candidate id and a specific rationale. The validator accepts
such an exclusion only for a candidate that is present in the plan and whose
recorded execution outcome is `survived`. Killed, timed-out and missing
candidates cannot be hidden this way. The evaluator reports the exclusion count
per symbol and omits only the reviewed candidates from adequacy.

## Collection workflow

For an authorised, trusted local checkout, preserve the outputs in a dedicated
`experiments/study-v0.2/<subject-id>/` directory.

```powershell
# This is read-only static screening, before an image exists.
diffmosaic screen --repo C:\work\target --repository-label https://github.com/example/project `
  --max-commits 120 --operator-set v0.2 `
  --output screening.json

# Coverage is generated independently; run only a project you are authorised to execute.
coverage run -m pytest
coverage json -o coverage.json

diffmosaic analyze --repo C:\work\target --base <base-sha> --head <head-sha> `
  --coverage-json C:\work\target\coverage.json --output analysis.json

diffmosaic prioritize --repo C:\work\target --base <base-sha> --head <head-sha> `
  --coverage-json C:\work\target\coverage.json --output priority.json

diffmosaic mutate-plan --repo C:\work\target --base <base-sha> --head <head-sha> `
  --operator-set v0.2 --output mutation-plan.json

diffmosaic mutate-run --repo C:\work\target --base <base-sha> --head <head-sha> `
  --operator-set v0.2 --image trusted-target-tests:locked `
  --output mutation-results.json --workdir /workspace `
  --allow-execution --test-command python -m pytest
```

`/workspace` is the default and is always read-only. `/tmp` is the only other
accepted working directory; use it only for a reviewed test command with
explicit `/workspace/...` paths when the test needs a temporary relative file.
The chosen directory is a frozen execution control, not an implicit detail.

After recording the relative paths and SHA-256 values in the manifest, freeze
the subject list and run:

```powershell
diffmosaic corpus-validate --manifest corpus\study-v0.2.json --verify-artifacts --format markdown
diffmosaic evaluate --manifest corpus\study-v0.2.json --format markdown --output study-results.md
```

## Reproduction

`reproduce` does not accept an ad-hoc test command or image. It uses the
frozen subject's commits, planner version, operator set, Docker image identity,
command and sandbox limits. It rebuilds the plan and compares its candidate
identifiers with the frozen plan, then fails before execution if they or the
local image identity differ.

```powershell
diffmosaic reproduce --manifest corpus\study-v0.2.json --subject <subject-id> `
  --repo C:\work\target --output reproduced-results.json --allow-execution
```

The command still executes project tests. Its Docker restrictions reduce risk
but do not make arbitrary code trustworthy; review the execution protocol and
run only authorised source and images.
