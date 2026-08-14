# Review-prioritisation protocol

`prioritize` converts an existing DiffMosaic analysis report into a small
review queue. It is deliberately a fixed-rule method, not a trained model and
not a prediction that a change contains a defect.

## Rules

The score for each changed production symbol is the sum of visible evidence-gap
rules:

| Code | Weight | Condition | Meaning |
| --- | ---: | --- | --- |
| `no_changed_line_executed` | 3 | Coverage is available, but none of the symbol's changed lines is recorded as executed | Strong reason to inspect test evidence |
| `partial_changed_line_execution` | 1 | Coverage is available, but only some changed lines are recorded as executed | Weak reason to inspect the remaining lines |
| `coverage_evidence_unavailable` | 1 | No coverage, unmatched coverage, or ambiguous coverage | Evidence is incomplete, not negative |
| `no_changed_test_file` | 2 | No diff path matches the conservative test-path heuristic | Repository-level baseline signal only |

Scores of 4+ are `high`, 2-3 are `medium`, and 0-1 are `low`. Ties are broken
deterministically by path, source location and qualified name.

## Interpretation limits

The test-path rule does not prove that no test changed: a project can store
tests outside common pytest locations. Similarly, coverage records execution,
not assertions. A low score does not prove adequacy, and a high score does not
prove a defect. The command exists to make reviewer attention allocation
repeatable and auditable.

## Evaluation plan

Compare this queue to the baseline `no_test_file_changed` using frozen corpus
subjects. Report per-subject ranks and the full JSON explanations, not just an
aggregate score. Any future changes to weights or rules require a new protocol
version and a separate evaluation; tuning after inspecting pilot outcomes must
be disclosed.
