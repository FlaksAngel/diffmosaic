"""Command-line interface for the first DiffMosaic prototype."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from diffmosaic.analyzer import analyse_repository
from diffmosaic.coverage import CoverageDataError
from diffmosaic.diff import GitReadError
from diffmosaic.mutation import plan_repository_mutations
from diffmosaic.reporting import (
    render_json,
    render_markdown,
    render_mutation_plan_json,
    render_mutation_plan_markdown,
    write_mutation_plan,
    write_report,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="diffmosaic",
        description="Inspect changed Python symbols in a local Git diff.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyse = subparsers.add_parser(
        "analyze",
        help="analyse two revisions without changing the repository",
    )
    analyse.add_argument("--repo", type=Path, required=True, help="path to a local Git repository")
    analyse.add_argument("--base", required=True, help="base Git revision, for example origin/main")
    analyse.add_argument("--head", required=True, help="head Git revision, for example HEAD")
    analyse.add_argument(
        "--coverage-json",
        type=Path,
        help="optional coverage.py JSON created beforehand in a trusted environment",
    )
    analyse.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="report format (default: json)",
    )
    analyse.add_argument("--output", type=Path, help="write report to this path instead of stdout")

    mutation = subparsers.add_parser(
        "mutate-plan",
        help="plan diff-local mutations without executing project code",
    )
    mutation.add_argument("--repo", type=Path, required=True, help="path to a local Git repository")
    mutation.add_argument("--base", required=True, help="base Git revision, for example origin/main")
    mutation.add_argument("--head", required=True, help="head Git revision, for example HEAD")
    mutation.add_argument(
        "--max-candidates",
        type=int,
        default=20,
        help="maximum deterministic candidate count (default: 20)",
    )
    mutation.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="plan format (default: json)",
    )
    mutation.add_argument("--output", type=Path, help="write plan to this path instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "analyze":
        try:
            report = analyse_repository(args.repo, args.base, args.head, args.coverage_json)
        except (CoverageDataError, GitReadError, OSError) as exc:
            print(f"diffmosaic: {exc}", file=sys.stderr)
            return 1

        if args.output:
            write_report(report, args.output, args.format)
        else:
            rendered = render_json(report) if args.format == "json" else render_markdown(report)
            print(rendered, end="")
        return 0

    if args.command == "mutate-plan":
        try:
            plan = plan_repository_mutations(
                str(args.repo),
                args.base,
                args.head,
                max_candidates=args.max_candidates,
            )
        except (GitReadError, OSError, ValueError) as exc:
            print(f"diffmosaic: {exc}", file=sys.stderr)
            return 1

        if args.output:
            write_mutation_plan(plan, args.output, args.format)
        else:
            rendered = (
                render_mutation_plan_json(plan)
                if args.format == "json"
                else render_mutation_plan_markdown(plan)
            )
            print(rendered, end="")
        return 0

    return 2
