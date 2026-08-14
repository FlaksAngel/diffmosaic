"""Serialise DiffMosaic reports without changing analytical conclusions."""

from __future__ import annotations

import json
from pathlib import Path

from diffmosaic.models import AnalysisReport
from diffmosaic.mutation import MutationPlan
from diffmosaic.runner import MutationExecutionReport


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
