"""Command-line interface for DiffMosaic."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from diffmosaic.analyzer import analyse_repository
from diffmosaic.corpus import validate_corpus_manifest
from diffmosaic.coverage import CoverageDataError
from diffmosaic.diff import GitReadError
from diffmosaic.mutation import available_operator_sets, plan_repository_mutations
from diffmosaic.priority import prioritise_report
from diffmosaic.runner import DockerSandboxConfig, MutationExecutionError, run_mutation_plan
from diffmosaic.screening import screen_repository_history
from diffmosaic.reporting import (
    render_json,
    render_corpus_validation_json,
    render_corpus_validation_markdown,
    render_markdown,
    render_mutation_plan_json,
    render_mutation_plan_markdown,
    render_priority_json,
    render_priority_markdown,
    render_study_evaluation_json,
    render_study_evaluation_markdown,
    write_mutation_plan,
    write_mutation_execution,
    write_corpus_validation,
    write_priority,
    write_report,
    write_study_evaluation,
    render_static_screening_json,
    render_static_screening_markdown,
    write_static_screening,
)
from diffmosaic.study import StudyDataError, evaluate_study, frozen_study_subject


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

    prioritise = subparsers.add_parser(
        "prioritize",
        help="rank changed symbols for review using fixed evidence-gap rules",
    )
    prioritise.add_argument("--repo", type=Path, required=True, help="path to a local Git repository")
    prioritise.add_argument("--base", required=True, help="base Git revision, for example origin/main")
    prioritise.add_argument("--head", required=True, help="head Git revision, for example HEAD")
    prioritise.add_argument(
        "--coverage-json",
        type=Path,
        help="optional coverage.py JSON created beforehand in a trusted environment",
    )
    prioritise.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="priority-report format (default: json)",
    )
    prioritise.add_argument("--output", type=Path, help="write priorities to this path instead of stdout")

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
        "--operator-set",
        choices=available_operator_sets(),
        default="v0.1",
        help="versioned mutation-operator set (default: v0.1)",
    )
    mutation.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="plan format (default: json)",
    )
    mutation.add_argument("--output", type=Path, help="write plan to this path instead of stdout")

    screen = subparsers.add_parser(
        "screen",
        help="screen a bounded local commit history without executing target code",
    )
    screen.add_argument("--repo", type=Path, required=True, help="path to a local Git repository")
    screen.add_argument(
        "--repository-label",
        help="public label for the report; defaults to the local directory name",
    )
    screen.add_argument("--max-commits", type=int, default=120, help="newest-first commit limit")
    screen.add_argument("--max-candidates", type=int, default=20, help="per-commit mutation limit")
    screen.add_argument(
        "--operator-set",
        choices=available_operator_sets(),
        default="v0.2",
        help="versioned mutation-operator set (default: v0.2)",
    )
    screen.add_argument("--format", choices=("json", "markdown"), default="json")
    screen.add_argument("--output", type=Path, help="write screening report to this path")

    corpus = subparsers.add_parser(
        "corpus-validate",
        help="validate a data-only, version-pinned pilot corpus manifest",
    )
    corpus.add_argument("--manifest", type=Path, required=True, help="path to a local corpus JSON")
    corpus.add_argument(
        "--verify-artifacts",
        action="store_true",
        help="also verify local v0.2 artifact paths, checksums, and revision metadata",
    )
    corpus.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="validation format (default: json)",
    )
    corpus.add_argument("--output", type=Path, help="write validation to this path instead of stdout")

    evaluate = subparsers.add_parser(
        "evaluate",
        help="aggregate a frozen v0.2 study into symbol-level evidence metrics",
    )
    evaluate.add_argument("--manifest", type=Path, required=True, help="path to a frozen v0.2 corpus JSON")
    evaluate.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="evaluation-report format (default: json)",
    )
    evaluate.add_argument("--output", type=Path, help="write evaluation to this path instead of stdout")

    execute = subparsers.add_parser(
        "mutate-run",
        help="run planned mutations in an explicitly enabled Docker sandbox",
    )
    execute.add_argument("--repo", type=Path, required=True, help="path to a local Git repository")
    execute.add_argument("--base", required=True, help="base Git revision, for example origin/main")
    execute.add_argument("--head", required=True, help="head Git revision, for example HEAD")
    execute.add_argument("--image", required=True, help="trusted Docker image already available locally")
    execute.add_argument("--output", type=Path, required=True, help="write experiment JSON here")
    execute.add_argument("--max-candidates", type=int, default=20)
    execute.add_argument(
        "--operator-set",
        choices=available_operator_sets(),
        default="v0.1",
        help="versioned mutation-operator set (default: v0.1)",
    )
    execute.add_argument("--timeout-seconds", type=int, default=120)
    execute.add_argument("--memory-limit", default="1g")
    execute.add_argument("--cpu-limit", type=float, default=1.0)
    execute.add_argument("--pids-limit", type=int, default=256)
    execute.add_argument(
        "--workdir",
        choices=("/workspace", "/tmp"),
        default="/workspace",
        help="container working directory; /tmp preserves the read-only source mount",
    )
    execute.add_argument(
        "--allow-execution",
        action="store_true",
        help="required acknowledgement: this runs the supplied test command in Docker",
    )
    execute.add_argument(
        "--test-command",
        nargs=argparse.REMAINDER,
        required=True,
        help="test command arguments; this option must be last",
    )

    reproduce = subparsers.add_parser(
        "reproduce",
        help="re-run one frozen v0.2 study subject in its recorded Docker sandbox",
    )
    reproduce.add_argument("--manifest", type=Path, required=True, help="path to a v0.2 corpus JSON")
    reproduce.add_argument("--subject", required=True, help="study subject id from the manifest")
    reproduce.add_argument("--repo", type=Path, required=True, help="local clone containing the frozen commits")
    reproduce.add_argument("--output", type=Path, required=True, help="write reproduced experiment JSON here")
    reproduce.add_argument(
        "--allow-execution",
        action="store_true",
        help="required acknowledgement: this runs the frozen test command in Docker",
    )
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

    if args.command == "prioritize":
        try:
            analysis = analyse_repository(args.repo, args.base, args.head, args.coverage_json)
        except (CoverageDataError, GitReadError, OSError) as exc:
            print(f"diffmosaic: {exc}", file=sys.stderr)
            return 1

        report = prioritise_report(analysis)
        if args.output:
            write_priority(report, args.output, args.format)
        else:
            rendered = (
                render_priority_json(report)
                if args.format == "json"
                else render_priority_markdown(report)
            )
            print(rendered, end="")
        return 0

    if args.command == "mutate-plan":
        try:
            plan = plan_repository_mutations(
                str(args.repo),
                args.base,
                args.head,
                max_candidates=args.max_candidates,
                operator_set=args.operator_set,
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

    if args.command == "screen":
        try:
            report = screen_repository_history(
                args.repo,
                max_commits=args.max_commits,
                max_candidates=args.max_candidates,
                operator_set=args.operator_set,
                repository_label=args.repository_label,
            )
        except (GitReadError, OSError, ValueError) as exc:
            print(f"diffmosaic: {exc}", file=sys.stderr)
            return 1
        if args.output:
            write_static_screening(report, args.output, args.format)
        else:
            rendered = (
                render_static_screening_json(report)
                if args.format == "json"
                else render_static_screening_markdown(report)
            )
            print(rendered, end="")
        return 0

    if args.command == "corpus-validate":
        report = validate_corpus_manifest(args.manifest, verify_artifacts=args.verify_artifacts)
        if args.output:
            write_corpus_validation(report, args.output, args.format)
        else:
            rendered = (
                render_corpus_validation_json(report)
                if args.format == "json"
                else render_corpus_validation_markdown(report)
            )
            print(rendered, end="")
        return 0 if report.valid else 1

    if args.command == "evaluate":
        try:
            report = evaluate_study(args.manifest)
        except (StudyDataError, OSError, ValueError) as exc:
            print(f"diffmosaic: {exc}", file=sys.stderr)
            return 1
        if args.output:
            write_study_evaluation(report, args.output, args.format)
        else:
            rendered = (
                render_study_evaluation_json(report)
                if args.format == "json"
                else render_study_evaluation_markdown(report)
            )
            print(rendered, end="")
        return 0

    if args.command == "mutate-run":
        if not args.allow_execution:
            print(
                "diffmosaic: mutation execution is disabled; pass --allow-execution after reviewing the protocol.",
                file=sys.stderr,
            )
            return 2
        try:
            plan = plan_repository_mutations(
                str(args.repo),
                args.base,
                args.head,
                max_candidates=args.max_candidates,
                operator_set=args.operator_set,
            )
            config = DockerSandboxConfig(
                image=args.image,
                test_command=tuple(args.test_command),
                working_directory=args.workdir,
                timeout_seconds=args.timeout_seconds,
                memory_limit=args.memory_limit,
                cpu_limit=args.cpu_limit,
                pids_limit=args.pids_limit,
            )
            report = run_mutation_plan(args.repo, plan, config)
        except (GitReadError, MutationExecutionError, OSError, ValueError) as exc:
            print(f"diffmosaic: {exc}", file=sys.stderr)
            return 1

        write_mutation_execution(report, args.output)
        return 0

    if args.command == "reproduce":
        if not args.allow_execution:
            print(
                "diffmosaic: reproduction is disabled; pass --allow-execution after reviewing the protocol.",
                file=sys.stderr,
            )
            return 2
        try:
            subject = frozen_study_subject(args.manifest, args.subject)
            plan = plan_repository_mutations(
                str(args.repo),
                subject.base_revision,
                subject.head_revision,
                max_candidates=subject.max_candidates,
                operator_set=subject.operator_set,
            )
            planned_candidate_ids = tuple(candidate.site.identifier for candidate in plan.candidates)
            if planned_candidate_ids != subject.planned_candidate_ids:
                raise StudyDataError(
                    "The current planner does not reproduce the frozen mutation candidate ids. "
                    "Use the recorded DiffMosaic version and repository revisions."
                )
            config = DockerSandboxConfig(
                image=subject.docker_image,
                test_command=subject.test_command,
                working_directory=subject.working_directory,
                timeout_seconds=subject.timeout_seconds,
                memory_limit=subject.memory_limit,
                cpu_limit=subject.cpu_limit,
                pids_limit=subject.pids_limit,
            )
            report = run_mutation_plan(
                args.repo,
                plan,
                config,
                expected_image_identity=subject.docker_image_identity,
            )
        except (GitReadError, MutationExecutionError, OSError, StudyDataError, ValueError) as exc:
            print(f"diffmosaic: {exc}", file=sys.stderr)
            return 1
        report.notes.append(f"Reproduced frozen study subject: {subject.subject_id}.")
        write_mutation_execution(report, args.output)
        return 0

    return 2
