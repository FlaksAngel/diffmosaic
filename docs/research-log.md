# Research log

This log records decisions that affect DiffMosaic's design or experimental
protocol. Entries should be factual: what was decided, why, and which evidence
or experiment motivated the decision.

## 2026-08-14 - Project bootstrap

- **Decision:** start with local, Python-only diff analysis rather than test
  generation or a remote GitHub bot.
- **Reason:** this produces an inspectable baseline needed before introducing
  coverage, mutation testing, or any predictive scoring.
- **Next evidence needed:** evaluate symbol mapping on fixture projects and a
  small, manually inspected pilot corpus.

## 2026-08-14 - Mutation planning before mutation execution

- **Decision:** implement an AST-based mutation planner before any test runner.
- **Reason:** an inspectable, bounded candidate set is required to validate
  which source changes would be tested. It also avoids silently executing code
  from repositories being studied.
- **Initial operators:** comparison boundaries (`==`, `!=`, `<`, `<=`, `>`,
  `>=`) and Boolean connectors (`and`, `or`) whose AST spans overlap changed
  production lines.
- **Constraint:** candidates are syntactically validated in memory but are not
  written or executed in this iteration.

## 2026-08-14 - Isolated execution protocol

- **Decision:** mutation execution uses a local, pre-pulled Docker image and a
  fresh temporary `git archive` for every baseline or candidate invocation.
- **Controls:** no network, read-only container root filesystem, no Linux
  capabilities, no-new-privileges, bounded CPU/memory/PIDs, finite timeout,
  no automatic image builds, and a bounded log tail.
- **Validity control:** candidates are skipped unless the baseline test command
  passes in the identical sandbox configuration.
- **Limitation:** Docker controls reduce risk but do not make arbitrary code
  trustworthy; users must still analyse only repositories and images they are
  authorised to execute.

## 2026-08-14 - Corpus before claims

Decision: record study subjects in a version-pinned, data-only manifest and
validate it offline before any experiment is interpreted.

Rationale:

- moving branch names and undocumented test images make later reproduction
  impossible;
- calibration data from DiffMosaic itself is useful for exercising the data
  path but must never be presented as independent evidence;
- selection and exclusion rules should be fixed before examining outcomes to
  reduce convenient post-hoc choices.
