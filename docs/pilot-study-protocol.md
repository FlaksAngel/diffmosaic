# Pilot-study protocol

## Research question

For changed Python production code, can a transparent combination of changed
symbol mapping, test-file changes, coverage evidence and diff-local mutation
outcomes identify pull requests with weaker test evidence than the simple
baseline **no test file changed**?

This is a feasibility study. It must not claim that a surviving mutant proves a
defect, or that the selected projects represent all Python software.

## Unit of analysis

One observation is a `(repository, base_commit, head_commit)` triple. The head
commit must change production Python code. Its parent or declared base must be
an exact commit SHA, never a moving branch name.

## Corpus registry

`corpus/pilot-v0.1.json` is the versioned source of truth. A subject contains:

- public repository URL and license;
- role: `calibration`, `candidate`, `study`, or `excluded`;
- exact base and head SHA;
- Python version and raw test-command arguments;
- Docker image name and resolved digest for executable study subjects;
- a written selection rationale and, for an excluded subject, the recorded
  exclusion reason.

Run `diffmosaic corpus-validate --manifest corpus/pilot-v0.1.json` before
freezing a corpus version. Validation is offline and does not clone, pull or
execute anything.

The committed calibration subject validates this project's data path and must
be reported separately from third-party study results. A `candidate` has passed
the public-source and commit-selection checks but has no execution image yet;
it must not produce or support an experimental claim. A `study` subject also
requires a recorded eligible mutation screening and a trusted image with a
resolved identity. `excluded` keeps an auditable record of a source candidate
that was not suitable for the planned analysis; it is not silently removed.

The first three third-party source candidates are retained as exclusions after
screening found zero sites for the prototype's two mutation operators. A later
Flask commit and a Click commit are the first two eligible `study` subjects;
their selection reports were committed before image preparation and image
identities before execution. Two subjects from the same maintainer community
are not a mutation-adequacy study set. Before interpreting outcomes, freeze at
least six eligible `study` subjects from at least three maintainer communities,
selected using the same rules. This is still exploratory evidence, not a
representative sample.

## Inclusion and exclusion

Include only subjects that meet all of these conditions:

1. Python 3.11+ and a documented permissive license;
2. a reproducible, local test command that does not need secrets or network
   access at execution time;
3. a change to production Python code that DiffMosaic can parse;
4. explicit permission under the project license to analyse the source;
5. a preserved `mutate-plan` report with at least one candidate under the
   pre-declared candidate limit; and
6. a fixed trusted Docker image for mutation execution.

Exclude generated code, commits that only change documentation or tests,
projects whose tests require credentials or network access, commits with zero
supported mutation sites, projects that require an untracked generated source
file at archive runtime, and any project whose licensing conditions are
unclear. Record exclusions and the reason in a later corpus version rather
than replacing failed candidates silently.

## Procedure

1. Select fixed source commits and run `mutate-plan` with a pre-declared
   candidate limit before image preparation.
2. Record zero-site exclusions or freeze only the eligible subjects and
   validate the manifest in CI.
3. Create a coverage JSON artefact in each eligible project's approved isolated build.
4. Run `analyze` and preserve the JSON output.
5. Build and review the trusted image outside DiffMosaic, record its resolved
   digest in the manifest, then run `mutate-run` with the same command.
6. Preserve every raw JSON report, including timeouts and infrastructure
   errors; do not delete inconvenient observations.
7. Compare DiffMosaic's rank or flags against the no-test-file-changed
   baseline, describing the result as exploratory.

## Metrics and reporting

Report per subject: changed production symbols, changed test files, executed
changed lines when coverage is available, planned candidates, killed and
survived candidates, and inconclusive candidates. Mutation adequacy is
`killed / (killed + survived)` only; it is `null` where there are no conclusive
candidate outcomes.

Publish the frozen manifest, DiffMosaic release SHA, image identities, exact
commands, and machine-readable reports. Before publication, inspect log tails
for credentials or personal data. State threats to validity: small corpus,
project selection bias, limited mutation operators, container differences, and
the fact that test failure is not a direct oracle for real faults.
