# Research log

This log records decisions that affect DiffMosaic's design or experimental
protocol. Entries should be factual: what was decided, why, and which evidence
or experiment motivated the decision.

## 2026-08-14 — Project bootstrap

- **Decision:** start with local, Python-only diff analysis rather than test
  generation or a remote GitHub bot.
- **Reason:** this produces an inspectable baseline needed before introducing
  coverage, mutation testing, or any predictive scoring.
- **Next evidence needed:** evaluate symbol mapping on fixture projects and a
  small, manually inspected pilot corpus.
