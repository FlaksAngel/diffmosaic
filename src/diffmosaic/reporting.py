"""Serialise DiffMosaic reports without changing analytical conclusions."""

from __future__ import annotations

import json
from pathlib import Path

from diffmosaic.corpus import CorpusValidationReport
from diffmosaic.models import AnalysisReport
from diffmosaic.mutation import MutationPlan
from diffmosaic.priority import PriorityReport
from diffmosaic.runner import MutationExecutionReport
from diffmosaic.screening import StaticScreeningReport
from diffmosaic.study import StudyEvaluationReport


def render_json(report: AnalysisReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def render_markdown(report: AnalysisReport) -> str:
    data = report.to_dict()
    summary = data["summary"]
    lines = [
        "# DiffMosaic report",
        "",
        f"- Base revision: `{report.base_revision}`",
        f"- Head revision: `{report.head_revision}`",
        f"- Changed files: {summary['changed_files']}",
        f"- Changed test files: {summary['changed_test_files']}",
        f"- Changed production symbols: {summary['changed_production_symbols']}",
        f"- Unmapped changed lines: {summary['unmapped_changed_lines']}",
        "",
        "## Changed production symbols",
        "",
    ]

    if report.changed_symbols:
        for item in report.changed_symbols:
            symbol = item.symbol
            changed_lines = ", ".join(str(line) for line in item.changed_lines)
            lines.extend(
                [
                    f"### `{symbol.path}::{symbol.qualified_name}`",
                    "",
                    f"- Kind: {symbol.kind}",
                    f"- Symbol span: {symbol.start_line}-{symbol.end_line}",
                    f"- Changed lines: {changed_lines}",
                    f"- Coverage evidence: {item.coverage_status}",
                    (
                        "- Executed changed lines: "
                        + (", ".join(str(line) for line in item.executed_changed_lines) or "none")
                    ),
                    "",
                ]
            )
    else:
        lines.extend(["No changed production Python symbols were mapped.", ""])

    lines.extend(["## Changed test files", ""])
    if report.changed_test_files:
        lines.extend([*(f"- `{path}`" for path in report.changed_test_files), ""])
    else:
        lines.extend(["No test file paths were changed.", ""])

    lines.extend(["## Unmapped changes", ""])
    if report.unmapped_changes:
        lines.extend(
            [
                *(f"- `{item.path}:{item.line}` — {item.reason}" for item in report.unmapped_changes),
                "",
            ]
        )
    else:
        lines.extend(["No changed new lines were left unmapped.", ""])

    if report.notes:
        lines.extend(["## Notes", "", *(f"- {note}" for note in report.notes), ""])

    return "\n".join(lines)


def write_report(report: AnalysisReport, output: Path, output_format: str) -> None:
    """Write one report file, creating only explicitly requested parent folders."""

    rendered = render_json(report) if output_format == "json" else render_markdown(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def render_mutation_plan_json(plan: MutationPlan) -> str:
    return json.dumps(plan.to_dict(), indent=2, sort_keys=True) + "\n"


def render_mutation_plan_markdown(plan: MutationPlan) -> str:
    lines = [
        "# DiffMosaic mutation plan",
        "",
        f"- Base revision: `{plan.base_revision}`",
        f"- Head revision: `{plan.head_revision}`",
        f"- Operator set: `{plan.operator_set_version}`",
        f"- Candidate count: {len(plan.candidates)}",
        "",
        "This plan does not execute project code. Each item is a candidate for a future isolated runner.",
        "",
        "## Candidates",
        "",
    ]
    if plan.candidates:
        for candidate in plan.candidates:
            site = candidate.site
            lines.extend(
                [
                    f"### `{site.identifier}`",
                    "",
                    f"- Symbol: `{site.symbol or '<module>'}`",
                    f"- Expression: `{site.expression}`",
                    f"- Mutation: `{site.original_operator}` → `{site.replacement_operator}`",
                    "",
                ]
            )
    else:
        lines.extend(["No supported mutation sites were found in changed production code.", ""])

    if plan.notes:
        lines.extend(["## Notes", "", *(f"- {note}" for note in plan.notes), ""])
    return "\n".join(lines)


def write_mutation_plan(plan: MutationPlan, output: Path, output_format: str) -> None:
    rendered = (
        render_mutation_plan_json(plan)
        if output_format == "json"
        else render_mutation_plan_markdown(plan)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def write_mutation_execution(report: MutationExecutionReport, output: Path) -> None:
    """Persist one experiment record; logs remain bounded by the runner."""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_corpus_validation_json(report: CorpusValidationReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def render_corpus_validation_markdown(report: CorpusValidationReport) -> str:
    data = report.to_dict()
    summary = data["summary"]
    lines = [
        "# DiffMosaic corpus validation",
        "",
        f"- Study id: `{data['study_id'] or 'unavailable'}`",
        f"- Subject count: {data['subject_count']}",
        f"- Valid: {'yes' if data['valid'] else 'no'}",
        f"- Errors: {summary['errors']}",
        f"- Warnings: {summary['warnings']}",
        "",
        "## Findings",
        "",
    ]
    issues = data["issues"]
    if issues:
        for issue in issues:
            subject = f" (`{issue['subject_id']}`)" if issue["subject_id"] else ""
            lines.append(f"- [{issue['severity']}] `{issue['code']}`{subject}: {issue['message']}")
        lines.append("")
    else:
        lines.extend(["No validation findings.", ""])
    return "\n".join(lines)


def write_corpus_validation(
    report: CorpusValidationReport,
    output: Path,
    output_format: str,
) -> None:
    rendered = (
        render_corpus_validation_json(report)
        if output_format == "json"
        else render_corpus_validation_markdown(report)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def render_priority_json(report: PriorityReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def render_priority_markdown(report: PriorityReport) -> str:
    data = report.to_dict()
    summary = data["summary"]
    lines = [
        "# DiffMosaic review priorities",
        "",
        "This is a fixed-rule review queue, not a defect prediction.",
        "",
        f"- Base revision: `{data['base_revision']}`",
        f"- Head revision: `{data['head_revision']}`",
        f"- Baseline: no test file changed = {data['baseline']['no_test_file_changed']}",
        f"- High / medium / low: {summary['high_priority']} / {summary['medium_priority']} / {summary['low_priority']}",
        "",
        "## Symbols",
        "",
    ]
    if report.items:
        for item in report.items:
            symbol = item.changed_symbol.symbol
            lines.extend(
                [
                    f"### `{symbol.path}::{symbol.qualified_name}` - {item.level} ({item.score})",
                    "",
                    f"- Changed lines: {', '.join(str(line) for line in item.changed_symbol.changed_lines)}",
                    *(
                        f"- +{reason.weight} `{reason.code}`: {reason.explanation}"
                        for reason in item.reasons
                    ),
                    "",
                ]
            )
    else:
        lines.extend(["No changed production symbols were available for prioritisation.", ""])
    return "\n".join(lines)


def write_priority(report: PriorityReport, output: Path, output_format: str) -> None:
    rendered = render_priority_json(report) if output_format == "json" else render_priority_markdown(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def render_study_evaluation_json(report: StudyEvaluationReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def render_study_evaluation_markdown(report: StudyEvaluationReport) -> str:
    data = report.to_dict()
    summary = data["summary"]
    evaluation = data["evaluation"]
    lines = [
        "# DiffMosaic study evaluation",
        "",
        f"- Study id: `{data['study_id']}`",
        f"- Operator set: `{data['operator_set']}`",
        f"- Weak-evidence threshold: {evaluation['weak_adequacy_threshold']}",
        f"- Minimum conclusive candidates: {evaluation['minimum_conclusive_candidates']}",
        f"- Symbol rows / evaluable / weak: {summary['symbol_rows']} / {summary['evaluable_symbols']} / {summary['weak_test_evidence_symbols']}",
        f"- Mean mutation adequacy: {summary['mean_mutation_adequacy']}",
        f"- DiffMosaic average precision: {summary['diffmosaic_average_precision']}",
        f"- Baseline average precision: {summary['baseline_average_precision']}",
        "",
        "Average precision is tie-aware and is null when no weak-evidence symbol is available.",
        "",
        "## Symbol evidence",
        "",
        "| Subject | Symbol | Score | Coverage | Planned | Excluded | Killed | Survived | Adequacy | Weak evidence |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report.symbols:
        adequacy = "" if item.mutation_adequacy is None else f"{item.mutation_adequacy:.3f}"
        weak = "" if item.weak_test_evidence is None else str(item.weak_test_evidence).lower()
        lines.append(
            "| "
            + " | ".join(
                (
                    item.subject_id,
                    f"`{item.path}::{item.qualified_name}`",
                    str(item.priority_score),
                    item.coverage_status,
                    str(item.planned_candidates),
                    str(item.manually_excluded),
                    str(item.killed),
                    str(item.survived),
                    adequacy,
                    weak,
                )
            )
            + " |"
        )
    if not report.symbols:
        lines.append("| — | — | — | — | — | — | — | — | — | — |")
    if report.notes:
        lines.extend(["", "## Notes", "", *(f"- {note}" for note in report.notes)])
    lines.append("")
    return "\n".join(lines)


def write_study_evaluation(
    report: StudyEvaluationReport,
    output: Path,
    output_format: str,
) -> None:
    rendered = (
        render_study_evaluation_json(report)
        if output_format == "json"
        else render_study_evaluation_markdown(report)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def render_static_screening_json(report: StaticScreeningReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def render_static_screening_markdown(report: StaticScreeningReport) -> str:
    data = report.to_dict()
    summary = data["summary"]
    lines = [
        "# DiffMosaic static screening",
        "",
        "- Rule: first-parent non-merge commits, newest first",
        "- Eligibility: at least one planned diff-local mutation in a changed named Python symbol",
        "- Repository: `" + str(data["repository"]) + "`",
        "- Planner version: `" + str(data["planner_version"]) + "`",
        "- Operator set: `" + str(data["operator_set"]) + "`",
        "- Screened / eligible / unavailable: "
        + f"{summary['screened_revisions']} / {summary['eligible_revisions']} / {summary['unavailable_revisions']}",
        "",
        "| # | Base | Head | Symbols | Tests changed | Planned | Symbol mutants | Outcome |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report.revisions:
        lines.append(
            "| "
            + " | ".join(
                (
                    str(item.ordinal),
                    f"`{item.base_commit[:12]}`",
                    f"`{item.head_commit[:12]}`",
                    "" if item.changed_production_symbols is None else str(item.changed_production_symbols),
                    "" if item.changed_test_files is None else str(item.changed_test_files),
                    "" if item.candidate_count is None else str(item.candidate_count),
                    "" if item.symbol_candidate_count is None else str(item.symbol_candidate_count),
                    item.outcome,
                )
            )
            + " |"
        )
        if item.note:
            lines.append(f"|  |  |  |  |  |  |  | {item.note} |")
    if not report.revisions:
        lines.append("| — | — | — | — | — | — | — | no non-merge commits found |")
    lines.append("")
    return "\n".join(lines)


def write_static_screening(
    report: StaticScreeningReport,
    output: Path,
    output_format: str,
) -> None:
    rendered = (
        render_static_screening_json(report)
        if output_format == "json"
        else render_static_screening_markdown(report)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
