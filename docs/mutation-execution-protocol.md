# Mutation execution protocol

## Purpose

DiffMosaic treats a mutation result as evidence about a particular revision,
test command, container image, and resource limit. It is not a claim that a
test suite is universally complete.

## Preconditions

Before invoking `mutate-run`, the operator must confirm all of the following:

1. They are authorised to execute the selected repository's tests.
2. The selected Git revision contains no secrets required by the tests.
3. The Docker image is trusted, already present locally, and contains the
   dependencies required for the selected test command.
4. The test command is understood and placed after `--test-command` as raw
   arguments, not passed through a host shell.

DiffMosaic does not build images, pull images, execute Dockerfiles, install
dependencies, or use the working tree as a sandbox input.

## Isolation model

For the head revision, DiffMosaic creates an in-memory `git archive`, safely
extracts regular files into a temporary directory, writes one mutated source
file only in that directory, then invokes Docker with these controls:

- `--network none`;
- `--read-only` root filesystem;
- `--cap-drop ALL` and `no-new-privileges`;
- configurable CPU, memory, PID and wall-clock limits;
- a `noexec`, `nosuid`, `nodev` temporary filesystem;
- a read-only temporary bind-mounted `/workspace` deleted after each invocation.

The original repository is never modified. The test process may write only to
the constrained `/tmp` filesystem; DiffMosaic disables Python bytecode writes.
For pytest commands it also redirects the pytest cache to `/tmp`, so projects
that treat cache-write warnings as errors remain compatible with the read-only
workspace.
Projects whose tests require a writable source tree are outside this runner's
current scope. Each invocation receives a random Docker container name; if the
host-side timeout expires, DiffMosaic force-removes that named container before
returning the `timeout` result.

## Baseline and outcomes

The exact command runs once against the unmodified archived head revision.
If it does not pass, DiffMosaic records `failed`, `timeout`, or
`infrastructure_error` and skips all candidate mutations.

For a passing baseline:

| Outcome | Meaning |
| --- | --- |
| `killed` | The candidate made the test command return non-zero. |
| `survived` | The candidate made the test command return zero. |
| `timeout` | The container invocation exceeded the configured time. |
| `infrastructure_error` | Docker itself failed before the test outcome was meaningful. |

Only `killed` and `survived` are used to calculate mutation adequacy. Timeouts
and infrastructure errors remain in the JSON record but are not silently
treated as either successful or failed tests.

## Reproducibility record

The resulting JSON records the resolved source commit SHAs, Docker image digest
(or local image ID), test command, mutation-site metadata and outcomes. Keep it
together with the DiffMosaic version and dataset inclusion rules. Never publish
test logs without reviewing them for secrets or personal data.
