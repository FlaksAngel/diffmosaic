"""Create an auditable static screen for a fixed local Git history window."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from diffmosaic import __version__
from diffmosaic.analyzer import analyse_repository
from diffmosaic.diff import GitReadError, read_first_parent_non_merge_revisions
from diffmosaic.mutation import plan_repository_mutations


@dataclass(frozen=True)
class ScreenedRevision:
    """A single commit evaluated by the same static eligibility rule."""

    ordinal: int
    base_commit: str
    head_commit: str
    changed_files: int | None
    changed_production_symbols: int | None
    changed_test_files: int | None
    candidate_count: int | None
    symbol_candidate_count: int | None
    outcome: str
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "base_commit": self.base_commit,
            "head_commit": self.head_commit,
            "changed_files": self.changed_files,
            "changed_production_symbols": self.changed_production_symbols,
            "changed_test_files": self.changed_test_files,
            "candidate_count": self.candidate_count,
            "symbol_candidate_count": self.symbol_candidate_count,
            "outcome": self.outcome,
            "note": self.note,
        }


@dataclass
class StaticScreeningReport:
    """Machine-readable evidence of newest-first, outcome-blind candidate screening."""

    repository: str
    planner_version: str
    operator_set: str
    max_commits: int
    max_candidates: int
    revisions: list[ScreenedRevision] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        eligible = sum(item.outcome == "eligible" for item in self.revisions)
        unavailable = sum(item.outcome == "unavailable" for item in self.revisions)
        return {
            "schema_version": "0.1",
            "selection_rule": {
                "history": "first-parent non-merge commits, newest first",
                "outcome_blind": True,
                "eligibility": "at least one planned diff-local mutation in a changed named Python symbol",
            },
            "repository": self.repository,
            "planner_version": self.planner_version,
            "operator_set": self.operator_set,
            "max_commits": self.max_commits,
            "max_candidates": self.max_candidates,
            "summary": {
                "screened_revisions": len(self.revisions),
                "eligible_revisions": eligible,
                "unavailable_revisions": unavailable,
            },
            "revisions": [item.to_dict() for item in self.revisions],
        }


def screen_repository_history(
    repo: Path,
    *,
    max_commits: int = 120,
    max_candidates: int = 20,
    operator_set: str = "v0.2",
    repository_label: str | None = None,
) -> StaticScreeningReport:
    """Read and assess a bounded history window without executing target code."""

    revisions = read_first_parent_non_merge_revisions(repo, max_commits)
    report = StaticScreeningReport(
        repository=repository_label or repo.name,
        planner_version=__version__,
        operator_set=operator_set,
        max_commits=max_commits,
        max_candidates=max_candidates,
    )
    for ordinal, (head_commit, base_commit) in enumerate(revisions, start=1):
        try:
            analysis = analyse_repository(repo, base_commit, head_commit)
            plan = plan_repository_mutations(
                str(repo),
                base_commit,
                head_commit,
                max_candidates=max_candidates,
                operator_set=operator_set,
            )
        except (GitReadError, OSError, ValueError) as exc:
            report.revisions.append(
                ScreenedRevision(
                    ordinal,
                    base_commit,
                    head_commit,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "unavailable",
                    str(exc),
                )
            )
            continue
        changed_symbols = {
            (item.symbol.path, item.symbol.qualified_name) for item in analysis.changed_symbols
        }
        symbol_candidate_count = sum(
            (candidate.site.path, candidate.site.symbol) in changed_symbols
            for candidate in plan.candidates
            if candidate.site.symbol is not None
        )
        report.revisions.append(
            ScreenedRevision(
                ordinal,
                base_commit,
                head_commit,
                len(analysis.changed_files),
                len(analysis.changed_symbols),
                len(analysis.changed_test_files),
                len(plan.candidates),
                symbol_candidate_count,
                "eligible" if symbol_candidate_count else "excluded_no_supported_mutation_site",
            )
        )
    return report
