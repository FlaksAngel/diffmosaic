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
   same output, excluding no timestamp or machine-specific paths.

## Planned modules

- `diff.py` — parses unified Git diffs and reads source revisions.
- `symbols.py` — maps source locations to Python functions and methods.
- `analyzer.py` — assembles raw evidence into a domain report.
- `reporting.py` — serialises a report without business logic.
- `coverage.py` — validates and reads pre-generated execution evidence.
- `mutation.py` — planned: isolated diff-local mutation runs.
