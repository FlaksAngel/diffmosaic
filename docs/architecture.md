# Architecture

## Pipeline

```text
Git diff (base..head)
        |
        v
Unified diff parser ------> test-path classification
        |
        v
Changed new lines -----> Python AST symbol mapping
        |
        +------------> optional coverage.json reader (no code execution)
        |
        +------------> mutation planner (no file writes or execution)
        |
        +------------> opt-in Docker runner (temporary git archive only)
        |                 |-- baseline must pass
        |                 `-- bounded JSON experiment record
        |
        +------------> offline corpus-manifest validator (no fetch or execution)
        |
        v
Analysis report -----> JSON / Markdown
```

## Design principles

1. **Evidence before scores.** Raw changed lines and mappings remain in every
   report. Future scores must be reconstructible from raw evidence.
2. **No silent omission.** Deleted lines and changes outside a Python symbol
   are reported as unmapped.
3. **No repository mutation.** Analysis uses `git diff` and `git show` only.
4. **Deterministic output.** Identical revisions and configuration produce the
   same output, excluding timestamps and machine-specific paths.
5. **Declared research inputs.** Corpus subjects, commit IDs, test commands
   and image identities are versioned as data before their outcomes are read.

## Components

- `diff.py` parses unified Git diffs and reads source revisions.
- `symbols.py` maps source locations to Python functions and methods.
- `analyzer.py` assembles raw evidence into a domain report.
- `reporting.py` serialises reports without business logic.
- `coverage.py` validates and reads pre-generated execution evidence.
- `mutation.py` finds and syntactically validates bounded diff-local mutation
  candidates.
- `runner.py` is an opt-in Docker runner over a clean `git archive`; it never
  runs a project unless the caller supplies a prebuilt image and acknowledgement.
- `corpus.py` validates a local version-pinned registry and never fetches,
  installs, or executes the projects it describes.
