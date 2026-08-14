# DiffMosaic

**DiffMosaic** is an evidence-based test adequacy analyser for Python pull
requests. It does not generate tests. Instead, it turns a pull request diff
into an inspectable report answering a narrower question:

> Which changed Python symbols have little evidence that the test suite checks
> their new behaviour?

Version `0.1.0` is an intentionally small research prototype. It parses a
local Git diff, classifies production and test changes, maps changed lines to
Python symbols through the AST, and emits deterministic JSON or Markdown
reports. It can also read an existing `coverage.py` JSON artefact; it does not
run tests or execute code in the analysed repository.

## Status and scope

- **Supported:** local Git repositories, Python source files, `pytest`-style
  test paths, JSON/Markdown reports.
- **Not yet supported:** remote GitHub API access, test execution, mutation
  testing, GitHub Actions integration, or automatic test generation.

Keeping the first version narrow makes every claim and experiment auditable.

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

## Research direction

The project will evaluate whether transparent diff and test signals can rank
pull requests with weak behavioural test evidence better than simple baselines,
such as "no test file changed". The experimental protocol, data schema, and
limitations are kept in [`docs/`](docs/).

## Development

```powershell
python -m pytest
python -m diffmosaic --help
```

Contributions and discussion are welcome once the research protocol is frozen.
Please do not add LLM-backed test generation to the core analyser: the central
claim is about inspectable evidence, not generated suggestions.

## License

[MIT](LICENSE)
