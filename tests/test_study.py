import hashlib
import json
from pathlib import Path

import pytest

from diffmosaic.cli import main
from diffmosaic.corpus import validate_corpus_manifest
from diffmosaic.study import StudyDataError, SymbolEvaluation, StudyEvaluationReport, evaluate_study, frozen_study_subject


BASE = "a" * 40
HEAD = "b" * 40
IMAGE_IDENTITY = "example-tests@sha256:" + "c" * 64


def _mutation_results(candidates: list[dict[str, object]]) -> dict[str, object]:
    return {
        "base_revision": BASE,
        "head_revision": HEAD,
        "operator_set_version": "v0.2",
        "sandbox": {
            "image": "example-tests:1",
            "image_identity": IMAGE_IDENTITY,
            "test_command": ["python", "-m", "pytest"],
            "working_directory": "/workspace",
            "limits": {
                "timeout_seconds": 120,
                "memory_limit": "1g",
                "cpu_limit": 1.0,
                "pids_limit": 256,
            },
        },
        "baseline": {"outcome": "passed"},
        "candidates": candidates,
    }


def _write_json(root: Path, relative_path: str, data: dict[str, object]) -> dict[str, str]:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "path": relative_path,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }


def _frozen_manifest(tmp_path: Path) -> Path:
    screening_report = _write_json(
        tmp_path,
        "experiments/study-v0.2/screening.json",
        {
            "repository": "https://example.test/sample-project",
            "planner_version": "0.10.0",
            "operator_set": "v0.2",
            "revisions": [
                {
                    "ordinal": 1,
                    "base_commit": BASE,
                    "head_commit": HEAD,
                    "candidate_count": 2,
                    "symbol_candidate_count": 2,
                    "outcome": "eligible",
                }
            ],
        },
    )
    artifacts = {
        "analysis": _write_json(
            tmp_path,
            "experiments/study-v0.2/analysis.json",
            {
                "base_revision": BASE,
                "head_revision": HEAD,
                "changed_symbols": [
                    {"path": "pkg/logic.py", "qualified_name": "validate"}
                ],
            },
        ),
        "priority": _write_json(
            tmp_path,
            "experiments/study-v0.2/priority.json",
            {
                "base_revision": BASE,
                "head_revision": HEAD,
                "baseline": {"no_test_file_changed": True},
                "items": [
                    {
                        "path": "pkg/logic.py",
                        "qualified_name": "validate",
                        "review_score": 5,
                        "review_level": "high",
                        "coverage": {"status": "available"},
                    }
                ],
            },
        ),
        "coverage": _write_json(
            tmp_path,
            "experiments/study-v0.2/coverage.json",
            {"files": {"pkg/logic.py": {"executed_lines": [2, 3]}}},
        ),
        "mutation_plan": _write_json(
            tmp_path,
            "experiments/study-v0.2/mutation-plan.json",
            {
                "base_revision": BASE,
                "head_revision": HEAD,
                "operator_set_version": "v0.2",
                "candidates": [
                    {"id": "pkg/logic.py:2:4:comparison_operator:>-to->=", "path": "pkg/logic.py", "symbol": "validate"},
                    {"id": "pkg/logic.py:3:4:binary_operator:+-to--", "path": "pkg/logic.py", "symbol": "validate"},
                ],
            },
        ),
        "mutation_results": _write_json(
            tmp_path,
            "experiments/study-v0.2/mutation-results.json",
            _mutation_results(
                [
                    {
                        "candidate_id": "pkg/logic.py:2:4:comparison_operator:>-to->=",
                        "outcome": "killed",
                    },
                    {
                        "candidate_id": "pkg/logic.py:3:4:binary_operator:+-to--",
                        "outcome": "survived",
                    },
                ]
            ),
        ),
    }
    manifest = {
        "schema_version": "0.2",
        "study_id": "study-v0-2-fixture",
        "status": "frozen",
        "operator_set": "v0.2",
        "evaluation": {
            "weak_adequacy_threshold": 0.8,
            "minimum_conclusive_candidates": 1,
        },
        "inclusion_criteria": [
            "A public repository has a clear permissive license.",
            "The head commit changes production Python code.",
            "The test command is reproducible without secrets or network access.",
        ],
        "subjects": [
            {
                "id": "sample-project",
                "role": "study",
                "repository_url": "https://example.test/sample-project",
                "license": "MIT",
                "base_commit": BASE,
                "head_commit": HEAD,
                "python_version": "3.11",
                "test_command": ["python", "-m", "pytest"],
                "docker_image": "example-tests:1",
                "docker_image_identity": IMAGE_IDENTITY,
                "mutation_screening": {
                    "planner_version": "0.10.0",
                    "max_candidates": 20,
                    "candidate_count": 2,
                    "outcome": "eligible",
                },
                "execution": {
                    "working_directory": "/workspace",
                    "timeout_seconds": 120,
                    "memory_limit": "1g",
                    "cpu_limit": 1.0,
                    "pids_limit": 256,
                },
                "screening_report": {**screening_report, "ordinal": 1},
                "artifacts": artifacts,
                "selection_rationale": "Public fixture selected to verify frozen study artifact aggregation.",
            }
        ],
    }
    manifest_path = tmp_path / "corpus" / "study-v0.2.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _replace_artifact_and_digest(
    manifest_path: Path,
    artifact_name: str,
    relative_path: str,
    data: dict[str, object],
) -> None:
    root = manifest_path.parent.parent
    target = root / relative_path
    target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["subjects"][0]["artifacts"][artifact_name]["sha256"] = hashlib.sha256(
        target.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def test_v0_2_artifacts_are_verified_and_evaluated_per_symbol(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)

    validation = validate_corpus_manifest(manifest_path, verify_artifacts=True)
    report = evaluate_study(manifest_path)

    assert validation.valid
    assert len(report.symbols) == 1
    row = report.symbols[0]
    assert (row.killed, row.survived, row.inconclusive) == (1, 1, 0)
    assert row.mutation_adequacy == 0.5
    assert row.weak_test_evidence is True
    assert report.to_dict()["summary"]["diffmosaic_average_precision"] == 1.0


def test_artifact_digest_mismatch_fails_before_evaluation(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)
    priority_path = tmp_path / "experiments" / "study-v0.2" / "priority.json"
    priority_path.write_text("{}\n", encoding="utf-8")

    validation = validate_corpus_manifest(manifest_path, verify_artifacts=True)

    assert not validation.valid
    assert "artifact_digest_mismatch" in {issue.code for issue in validation.issues}


def test_screening_report_must_match_the_subject_revisions(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["subjects"][0]["screening_report"]["ordinal"] = 2
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    validation = validate_corpus_manifest(manifest_path, verify_artifacts=True)

    assert not validation.valid
    assert "screening_report_candidate_mismatch" in {issue.code for issue in validation.issues}


def test_artifact_revision_mismatch_is_rejected_even_with_a_matching_digest(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)
    _replace_artifact_and_digest(
        manifest_path,
        "analysis",
        "experiments/study-v0.2/analysis.json",
        {
            "base_revision": "d" * 40,
            "head_revision": HEAD,
            "changed_symbols": [{"path": "pkg/logic.py", "qualified_name": "validate"}],
        },
    )

    validation = validate_corpus_manifest(manifest_path, verify_artifacts=True)

    assert not validation.valid
    assert "artifact_revision_mismatch" in {issue.code for issue in validation.issues}


def test_no_conclusive_mutants_produce_no_adequacy_label(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)
    _replace_artifact_and_digest(
        manifest_path,
        "mutation_results",
        "experiments/study-v0.2/mutation-results.json",
        _mutation_results(
            [
                {
                    "candidate_id": "pkg/logic.py:2:4:comparison_operator:>-to->=",
                    "outcome": "timeout",
                },
                {
                    "candidate_id": "pkg/logic.py:3:4:binary_operator:+-to--",
                    "outcome": "infrastructure_error",
                },
            ]
        ),
    )

    report = evaluate_study(manifest_path)

    assert report.symbols[0].mutation_adequacy is None
    assert report.symbols[0].weak_test_evidence is None
    assert report.to_dict()["summary"]["evaluable_symbols"] == 0


def test_equivalent_survived_mutant_is_visible_but_excluded_from_adequacy(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["subjects"][0]["manual_mutant_assessments"] = [
        {
            "candidate_id": "pkg/logic.py:3:4:binary_operator:+-to--",
            "classification": "equivalent",
            "rationale": "The changed arithmetic expression is equivalent for the allowed domain.",
        }
    ]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    validation = validate_corpus_manifest(manifest_path, verify_artifacts=True)
    report = evaluate_study(manifest_path)

    assert validation.valid
    assert report.symbols[0].manually_excluded == 1
    assert report.symbols[0].planned_candidates == 1
    assert report.symbols[0].mutation_adequacy == 1.0
    assert report.symbols[0].weak_test_evidence is False


def test_manual_assessment_cannot_hide_a_killed_mutant(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["subjects"][0]["manual_mutant_assessments"] = [
        {
            "candidate_id": "pkg/logic.py:2:4:comparison_operator:>-to->=",
            "classification": "duplicate",
            "rationale": "This rationale is deliberately long enough to pass the structural check.",
        }
    ]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    validation = validate_corpus_manifest(manifest_path, verify_artifacts=True)

    assert not validation.valid
    assert "manual_mutant_not_survived" in {issue.code for issue in validation.issues}


def test_mutation_result_must_cover_exactly_the_saved_plan(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)
    _replace_artifact_and_digest(
        manifest_path,
        "mutation_results",
        "experiments/study-v0.2/mutation-results.json",
        _mutation_results(
            [
                {
                    "candidate_id": "pkg/logic.py:2:4:comparison_operator:>-to->=",
                    "outcome": "killed",
                }
            ]
        ),
    )

    validation = validate_corpus_manifest(manifest_path, verify_artifacts=True)

    assert not validation.valid
    assert "mutation_result_candidate_mismatch" in {issue.code for issue in validation.issues}


def test_study_evaluator_rejects_a_manifest_that_is_not_frozen(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "preliminary"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(StudyDataError, match="frozen"):
        evaluate_study(manifest_path)


def test_average_precision_is_tie_aware() -> None:
    positive = SymbolEvaluation(
        "subject-a", "pkg/a.py", "one", 3, "high", True, "available", 1, 0, 0, 1, 0, 0.0, True
    )
    negative = SymbolEvaluation(
        "subject-b", "pkg/b.py", "two", 3, "high", True, "available", 1, 0, 1, 0, 0, 1.0, False
    )

    average_precision = StudyEvaluationReport._average_precision(
        [positive, negative], use_baseline=False
    )

    assert average_precision == pytest.approx(0.75)


def test_frozen_subject_and_cli_evaluate_use_manifest_contract(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)
    output = tmp_path / "evaluation.json"

    subject = frozen_study_subject(manifest_path, "sample-project")
    exit_code = main(["evaluate", "--manifest", str(manifest_path), "--output", str(output)])

    assert subject.operator_set == "v0.2"
    assert subject.planner_version == "0.10.0"
    assert len(subject.planned_candidate_ids) == 2
    assert subject.max_candidates == 20
    assert subject.test_command == ("python", "-m", "pytest")
    assert subject.working_directory == "/workspace"
    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["summary"]["symbol_rows"] == 1


def test_reproduce_refuses_execution_without_explicit_acknowledgement(tmp_path: Path) -> None:
    output = tmp_path / "reproduced.json"

    exit_code = main(
        [
            "reproduce",
            "--manifest",
            str(tmp_path / "missing.json"),
            "--subject",
            "sample-project",
            "--repo",
            str(tmp_path),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 2
    assert not output.exists()


def test_frozen_subject_requires_its_recorded_planner_version(tmp_path: Path) -> None:
    manifest_path = _frozen_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["subjects"][0]["mutation_screening"]["planner_version"] = "0.9.0"
    screen_path = tmp_path / "experiments" / "study-v0.2" / "screening.json"
    screen = json.loads(screen_path.read_text(encoding="utf-8"))
    screen["planner_version"] = "0.9.0"
    screen_path.write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")
    manifest["subjects"][0]["screening_report"]["sha256"] = hashlib.sha256(
        screen_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(StudyDataError, match="requires planner version"):
        frozen_study_subject(manifest_path, "sample-project")
