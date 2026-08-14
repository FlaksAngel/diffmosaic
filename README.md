# DiffMosaic

[English](README.md) | [Русская версия](README.ru.md)

**DiffMosaic** is an evidence-based test adequacy analyser for Python pull
requests. It does not generate tests. Instead, it turns a pull request diff
into an inspectable report answering a narrower question:

> Which changed Python symbols have little evidence that the test suite checks
> their new behaviour?

Version `0.10.0` is an intentionally small research prototype. It parses a
local Git diff, classifies production and test changes, maps changed lines to
Python symbols through the AST, and emits deterministic JSON or Markdown
reports. It can also read an existing `coverage.py` JSON artefact; it does not
run tests or execute code in the analysed repository during analysis or
mutation planning. A separate opt-in Docker runner can execute pre-planned
mutations under documented controls. Its working directory is also recorded:
the default read-only `/workspace`, or the limited `/tmp` tmpfs for a reviewed
test that needs a temporary relative file.

## Status and scope

- **Supported:** local Git repositories, Python source files, `pytest`-style
  test paths, JSON/Markdown reports, safe planning of diff-local mutations,
  controlled Docker execution, and validation of version-pinned corpus data.
- **Not yet supported:** remote GitHub API access, automatic project setup,
  GitHub Actions integration for target projects, or automatic test generation.

Keeping the first version narrow makes every claim and experiment auditable.

## Review prioritisation

`prioritize` applies fixed, documented evidence-gap rules to changed symbols.
It produces a review queue, not a defect prediction: every score is a sum of
visible reasons, and missing coverage remains an unknown rather than a failed
test result.

```powershell
diffmosaic prioritize `
  --repo C:\path\to\python-project `
  --base origin/main `
  --head HEAD `
  --coverage-json C:\path\to\coverage.json `
  --format markdown
```

The exact rules, limitations and evaluation plan are in the
[review-prioritisation protocol](docs/review-prioritisation.md).

## Quick start

DiffMosaic requires Python 3.11 or later and Git.

```powershell
git clone <your-fork-or-repository-url> diffmosaic
cd diffmosaic
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

Analyse two revisions in a local repository:

```powershell
diffmosaic analyze `
  --repo C:\path\to\python-project `
  --base origin/main `
  --head HEAD `
  --format markdown `
  --output report.md
```

The command never changes the analysed repository. It runs `git diff` and
`git show` only.

To add execution evidence, generate `coverage.json` yourself in a trusted,
isolated checkout of the target project, then pass it to DiffMosaic:

```powershell
# Run this only in a repository whose tests you trust.
coverage run -m pytest
coverage json -o coverage.json

diffmosaic analyze --repo C:\path\to\python-project --base origin/main --head HEAD `
  --coverage-json C:\path\to\coverage.json --format markdown
```

If a coverage path cannot be matched unambiguously, DiffMosaic reports that
fact and does not invent coverage evidence.

## Example report

```text
Changed production symbols: 2
Changed test files: 1
Unmapped changed lines: 1

catalog.py::calculate_total (function, lines 4-11)
  Changed lines: 7, 8
```

An unmapped line is not silently discarded: module-level statements, deleted
code, or syntax that cannot be associated with a symbol are reported
explicitly.

## Mutation planning

DiffMosaic can identify small operator mutations only where production Python
code changed. Its legacy `v0.1` operator set supports comparison boundaries and
Boolean connectors. The versioned `v0.2` set additionally supports identity,
membership and `+/-` mutations; record the selected set with every experiment.

```powershell
diffmosaic mutate-plan `
  --repo C:\path\to\python-project `
  --base origin/main `
  --head HEAD `
  --operator-set v0.2 `
  --format markdown
```

The command only reads Git revisions and prints a plan. It does **not** run
tests, write mutant files, or execute target-project code. Candidate execution
uses a separate Docker command with explicit isolation controls.

## Controlled mutation execution

`mutate-run` is opt-in and is intended only for repositories whose tests and
container image you trust. Before every candidate it creates a clean temporary
worktree from `git archive <head>`, never from the source checkout. Docker runs
with no network, a read-only root filesystem, dropped capabilities, a bounded
process count, CPU/memory limits, and a temporary workspace that is deleted
after the run.

The source archive is always mounted read-only at `/workspace`. `--workdir`
defaults to that directory. Use `--workdir /tmp` only for a reviewed command
that names its tests through absolute `/workspace/...` paths and needs a
relative temporary file; the choice is persisted in the JSON report.

Prepare a **trusted, prebuilt** Docker image yourself; DiffMosaic never builds
an image or executes a repository Dockerfile. Then place `--test-command` last:

```powershell
diffmosaic mutate-run `
  --repo C:\path\to\trusted-python-project `
  --base origin/main `
  --head HEAD `
  --image trusted-project-tests:latest `
  --output mutation-results.json `
  --workdir /workspace `
  --allow-execution `
  --test-command python -m pytest
```

The baseline test run must pass before candidates run. Results are classified
as `killed`, `survived`, `timeout`, or `infrastructure_error`; only killed and
survived candidates contribute to mutation adequacy. Read the full
[execution protocol](docs/mutation-execution-protocol.md) before using it.

## Pilot corpus

Research subjects are registered as data, not discovered implicitly at runtime.
The current manifest separates one local calibration subject, two executed
third-party feasibility observations, and recorded exclusions. It is not yet a
representative study and must not be used to make general effectiveness claims.
Validate it locally without cloning or executing any project:

```powershell
diffmosaic corpus-validate --manifest corpus/pilot-v0.1.json --format markdown
```

The [pilot-study protocol](docs/pilot-study-protocol.md) specifies selection
rules, exclusions, metrics and reporting limits. A [Russian documentation
index](docs/ru/README.md) is available for product users.

The next protocol, [study v0.2](docs/study-v0.2-protocol.md), defines a frozen
symbol-level evaluation with artifact checksums, explicit operator sets and an
opt-in reproduction command. Its committed manifest is in `preliminary`
status with checksum-pinned sampled subjects and two complete attrs study
records; it contains no aggregate claim yet.

Candidate images have their own reviewed, lock-file-based recipes in
[`images/`](images/). DiffMosaic does not build them; see the
[image-provisioning protocol](docs/image-provisioning-protocol.md).

## Research direction

The project will evaluate whether transparent diff and test signals can rank
pull requests with weak behavioural test evidence better than simple baselines,
such as "no test file changed". The experimental protocol, data schema, and
limitations are kept in [`docs/`](docs/).

For a frozen v0.2 corpus, validate every local artifact before generating an
aggregate table:

```powershell
diffmosaic corpus-validate --manifest corpus\study-v0.2.json --verify-artifacts --format markdown
diffmosaic evaluate --manifest corpus\study-v0.2.json --format markdown --output study-results.md
```

`evaluate` deliberately rejects the preliminary manifest. First use `screen`
to record an outcome-blind history window; only a later frozen corpus with all
execution artifacts can be aggregated.

## Development

```powershell
python -m pytest
python -m diffmosaic --help
```

Contributions and discussion are welcome once the research protocol is frozen.

## License

[MIT](LICENSE)
