"""Transparent review prioritisation from observed test-evidence gaps.

This module does not predict defects or test quality. It merely applies a
small, published set of deterministic rules so a reviewer can decide where to
look first and can reconstruct every ranking from the analysis report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from diffmosaic.models import AnalysisReport, ChangedSymbol


@dataclass(frozen=True)
class PriorityReason:
    """One visible contribution to an item's review score."""

    code: str
    weight: int
    explanation: str

    def to_dict(self) -> dict[str, str | int]:
        return {"code": self.code, "weight": self.weight, "explanation": self.explanation}


@dataclass(frozen=True)
class PriorityItem:
    """A changed symbol with a deterministic review-priority explanation."""

    changed_symbol: ChangedSymbol
    score: int
    level: str
    reasons: tuple[PriorityReason, ...]

    def to_dict(self) -> dict[str, object]:
        item = self.changed_symbol
        return {
            "path": item.symbol.path,
            "qualified_name": item.symbol.qualified_name,
            "kind": item.symbol.kind,
            "changed_lines": list(item.changed_lines),
            "coverage": {
                "status": item.coverage_status,
                "executed_changed_lines": list(item.executed_changed_lines),
            },
            "review_score": self.score,
            "review_level": self.level,
            "reasons": [reason.to_dict() for reason in self.reasons],
        }


@dataclass
class PriorityReport:
    """A ranked, non-predictive view over one static analysis report."""

    base_revision: str
    head_revision: str
    baseline_no_test_file_changed: bool
    items: list[PriorityItem] = field(default_factory=list)
    unmapped_change_count: int = 0

    def to_dict(self) -> dict[str, object]:
        levels = {level: sum(item.level == level for item in self.items) for level in ("high", "medium", "low")}
        return {
            "schema_version": "0.1",
            "method": "fixed-rule review prioritisation; not a defect prediction",
            "base_revision": self.base_revision,
            "head_revision": self.head_revision,
            "baseline": {"no_test_file_changed": self.baseline_no_test_file_changed},
            "summary": {
                "changed_production_symbols": len(self.items),
                "high_priority": levels["high"],
                "medium_priority": levels["medium"],
                "low_priority": levels["low"],
                "unmapped_changed_lines": self.unmapped_change_count,
            },
            "items": [item.to_dict() for item in self.items],
            "limitations": [
                "A score prioritises review; it does not estimate defect probability.",
                "Test-path changes are a repository-level heuristic and are not linked to a symbol.",
                "Missing or ambiguous coverage is absence of evidence, not evidence that code was untested.",
            ],
        }


def _coverage_reasons(item: ChangedSymbol) -> list[PriorityReason]:
    if item.coverage_status == "available":
        executed = len(item.executed_changed_lines)
        changed = len(item.changed_lines)
        if executed == 0:
            return [
                PriorityReason(
                    "no_changed_line_executed",
                    3,
                    "Coverage was supplied, but it records none of this symbol's changed lines as executed.",
                )
            ]
        if executed < changed:
            return [
                PriorityReason(
                    "partial_changed_line_execution",
                    1,
                    "Coverage was supplied, but it records only some changed lines as executed.",
                )
            ]
        return []

    explanation = {
        "not_provided": "No coverage artefact was supplied for this analysis.",
        "unmatched": "Coverage was supplied but no unambiguous file match was found.",
        "ambiguous": "Coverage was supplied but its file path matched ambiguously.",
    }.get(item.coverage_status, "Coverage evidence is unavailable for this symbol.")
    return [PriorityReason("coverage_evidence_unavailable", 1, explanation)]


def _level_for(score: int) -> str:
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def prioritise_report(report: AnalysisReport) -> PriorityReport:
    """Rank changed symbols using fixed evidence-gap rules only."""

    no_test_file_changed = not report.changed_test_files
    items: list[PriorityItem] = []
    for changed_symbol in report.changed_symbols:
        reasons = _coverage_reasons(changed_symbol)
        if no_test_file_changed:
            reasons.append(
                PriorityReason(
                    "no_changed_test_file",
                    2,
                    "No changed path matched the conservative pytest-style test-path heuristic.",
                )
            )
        score = sum(reason.weight for reason in reasons)
        items.append(
            PriorityItem(
                changed_symbol=changed_symbol,
                score=score,
                level=_level_for(score),
                reasons=tuple(reasons),
            )
        )
    items.sort(
        key=lambda item: (
            -item.score,
            item.changed_symbol.symbol.path,
            item.changed_symbol.symbol.start_line,
            item.changed_symbol.symbol.qualified_name,
        )
    )
    return PriorityReport(
        base_revision=report.base_revision,
        head_revision=report.head_revision,
        baseline_no_test_file_changed=no_test_file_changed,
        items=items,
        unmapped_change_count=len(report.unmapped_changes),
    )
