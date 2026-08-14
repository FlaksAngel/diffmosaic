"""Aggregate immutable study artifacts into symbol-level research evidence.

The evaluator never executes a repository. It only reads a frozen v0.2 corpus
manifest and local JSON artifacts whose checksums have already been verified by
``corpus-validate --verify-artifacts``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from diffmosaic import __version__
from diffmosaic.corpus import validate_corpus_manifest


class StudyDataError(ValueError):
    """Raised when a study cannot be evaluated from complete frozen artifacts."""


@dataclass(frozen=True)
class FrozenStudySubject:
    """Execution-relevant fields from one validated v0.2 study subject."""

    subject_id: str
    base_revision: str
    head_revision: str
    operator_set: str
    docker_image: str
    docker_image_identity: str
    test_command: tuple[str, ...]
    working_directory: str
    planner_version: str
    planned_candidate_ids: tuple[str, ...]
    max_candidates: int
    timeout_seconds: int
    memory_limit: str
    cpu_limit: float
    pids_limit: int


@dataclass(frozen=True)
class SymbolEvaluation:
    """One changed symbol paired with its recorded diff-local mutation outcomes."""

    subject_id: str
    path: str
    qualified_name: str
    priority_score: int
    priority_level: str
    baseline_no_test_file_changed: bool
    coverage_status: str
    planned_candidates: int
    manually_excluded: int
    killed: int
    survived: int
    inconclusive: int
    mutation_adequacy: float | None
    weak_test_evidence: bool | None

    def to_dict(self) -> dict[str, object]:
        return {
            "subject_id": self.subject_id,
            "path": self.path,
            "qualified_name": self.qualified_name,
            "priority_score": self.priority_score,
            "priority_level": self.priority_level,
            "baseline_no_test_file_changed": self.baseline_no_test_file_changed,
            "coverage_status": self.coverage_status,
            "planned_candidates": self.planned_candidates,
            "manually_excluded": self.manually_excluded,
            "killed": self.killed,
            "survived": self.survived,
            "inconclusive": self.inconclusive,
            "mutation_adequacy": self.mutation_adequacy,
            "weak_test_evidence": self.weak_test_evidence,
        }


@dataclass
class StudyEvaluationReport:
    """Deterministic aggregate metrics and the rows from which they were derived."""

    study_id: str
    operator_set: str
    weak_adequacy_threshold: float
    minimum_conclusive_candidates: int
    symbols: list[SymbolEvaluation] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def _evaluable_symbols(self) -> list[SymbolEvaluation]:
        return [item for item in self.symbols if item.weak_test_evidence is not None]

    @staticmethod
    def _average_precision(items: list[SymbolEvaluation], *, use_baseline: bool) -> float | None:
        """Return tie-aware expected AP without letting ids order equal scores."""

        if not items:
            return None
        positives = sum(item.weak_test_evidence is True for item in items)
        if positives == 0:
            return None
        if use_baseline:
            score = lambda item: int(item.baseline_no_test_file_changed)
        else:
            score = lambda item: item.priority_score
        ranked = sorted(items, key=lambda item: -score(item))

        precision_sum = 0.0
        seen_items = 0
        seen_positives = 0
        index = 0
        while index < len(ranked):
            tie_score = score(ranked[index])
            group: list[SymbolEvaluation] = []
            while index < len(ranked) and score(ranked[index]) == tie_score:
                group.append(ranked[index])
                index += 1
            group_size = len(group)
            group_positives = sum(item.weak_test_evidence is True for item in group)
            for position in range(1, group_size + 1):
                probability_positive = group_positives / group_size
                expected_before = (
                    seen_positives
                    if group_size == 1
                    else seen_positives + (position - 1) * (group_positives - 1) / (group_size - 1)
                )
                precision_sum += probability_positive * (expected_before + 1) / (seen_items + position)
            seen_items += group_size
            seen_positives += group_positives
        return precision_sum / positives

    def to_dict(self) -> dict[str, object]:
        evaluable = self._evaluable_symbols()
        weak = sum(item.weak_test_evidence is True for item in evaluable)
        adequacies = [item.mutation_adequacy for item in evaluable if item.mutation_adequacy is not None]
        return {
            "schema_version": "0.1",
            "study_id": self.study_id,
            "operator_set": self.operator_set,
            "evaluation": {
                "weak_adequacy_threshold": self.weak_adequacy_threshold,
                "minimum_conclusive_candidates": self.minimum_conclusive_candidates,
            },
            "summary": {
                "symbol_rows": len(self.symbols),
                "evaluable_symbols": len(evaluable),
                "weak_test_evidence_symbols": weak,
                "mean_mutation_adequacy": sum(adequacies) / len(adequacies) if adequacies else None,
                "diffmosaic_average_precision": self._average_precision(
                    evaluable, use_baseline=False
                ),
                "baseline_average_precision": self._average_precision(evaluable, use_baseline=True),
            },
            "symbols": [item.to_dict() for item in self.symbols],
            "notes": self.notes,
        }


def _read_json(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StudyDataError(f"Required file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StudyDataError(f"Required file is not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise StudyDataError(f"Required JSON root must be an object: {path}")
    return data


def load_study_manifest(
    manifest_path: Path,
    *,
    verify_artifacts: bool,
    require_frozen: bool = False,
) -> dict[str, object]:
    """Load one valid v0.2 manifest, optionally checking every artifact digest."""

    validation = validate_corpus_manifest(manifest_path, verify_artifacts=verify_artifacts)
    if not validation.valid:
        details = "; ".join(issue.message for issue in validation.issues)
        raise StudyDataError(f"Study manifest is not valid: {details}")
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != "0.2":
        raise StudyDataError("evaluate and reproduce require a schema_version '0.2' manifest.")
    if require_frozen and manifest.get("status") != "frozen":
        raise StudyDataError("evaluate and reproduce require a frozen study manifest.")
    return manifest


def frozen_study_subject(manifest_path: Path, subject_id: str) -> FrozenStudySubject:
    """Return a single study subject without cloning or executing anything."""

    manifest = load_study_manifest(
        manifest_path,
        verify_artifacts=True,
        require_frozen=True,
    )
    subjects = manifest.get("subjects")
    if not isinstance(subjects, list):
        raise StudyDataError("Study manifest does not contain subjects.")
    subject = next(
        (
            item
            for item in subjects
            if isinstance(item, dict) and item.get("id") == subject_id
        ),
        None,
    )
    if subject is None:
        raise StudyDataError(f"Study subject does not exist: {subject_id}")
    if subject.get("role") != "study":
        raise StudyDataError(f"Only role=study subjects can be reproduced: {subject_id}")
    command = subject.get("test_command")
    if not isinstance(command, list) or not all(isinstance(value, str) for value in command):
        raise StudyDataError(f"Study subject has an invalid test command: {subject_id}")
    required_fields = (
        "base_commit",
        "head_commit",
        "docker_image",
        "docker_image_identity",
    )
    if not all(isinstance(subject.get(field), str) for field in required_fields):
        raise StudyDataError(f"Study subject has incomplete frozen execution data: {subject_id}")
    screening = subject.get("mutation_screening")
    execution = subject.get("execution")
    if not isinstance(screening, dict) or not isinstance(screening.get("max_candidates"), int):
        raise StudyDataError(f"Study subject has no valid mutation screening: {subject_id}")
    if not isinstance(execution, dict):
        raise StudyDataError(f"Study subject has no valid execution profile: {subject_id}")
    planner_version = screening.get("planner_version")
    if planner_version != __version__:
        raise StudyDataError(
            f"Study subject requires planner version {planner_version}; running {__version__}."
        )
    artifacts = subject.get("artifacts")
    if not isinstance(artifacts, dict):
        raise StudyDataError(f"Study subject has no valid artifact references: {subject_id}")
    plan = _read_json(_artifact_path(manifest_path, artifacts.get("mutation_plan")))
    candidates = plan.get("candidates")
    if not isinstance(candidates, list):
        raise StudyDataError(f"Study subject has no valid saved mutation plan: {subject_id}")
    candidate_ids = tuple(
        candidate.get("id")
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("id"), str)
    )
    if len(candidate_ids) != len(candidates) or len(set(candidate_ids)) != len(candidate_ids):
        raise StudyDataError(f"Study subject has invalid saved mutation candidate ids: {subject_id}")
    operator_set = manifest.get("operator_set")
    if not isinstance(operator_set, str):
        raise StudyDataError("Study manifest has no valid operator_set.")
    return FrozenStudySubject(
        subject_id=subject_id,
        base_revision=str(subject["base_commit"]),
        head_revision=str(subject["head_commit"]),
        operator_set=operator_set,
        docker_image=str(subject["docker_image"]),
        docker_image_identity=str(subject["docker_image_identity"]),
        test_command=tuple(command),
        working_directory=str(execution["working_directory"]),
        planner_version=planner_version,
        planned_candidate_ids=candidate_ids,
        max_candidates=int(screening["max_candidates"]),
        timeout_seconds=int(execution["timeout_seconds"]),
        memory_limit=str(execution["memory_limit"]),
        cpu_limit=float(execution["cpu_limit"]),
        pids_limit=int(execution["pids_limit"]),
    )


def _artifact_path(manifest_path: Path, reference: object) -> Path:
    if not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
        raise StudyDataError("Study artifact reference is incomplete.")
    root = manifest_path.parent.parent.resolve()
    path = (root / reference["path"]).resolve()
    if not path.is_relative_to(root):
        raise StudyDataError("Study artifact path escapes the repository.")
    return path


def _symbol_key(path: object, qualified_name: object) -> tuple[str, str] | None:
    if isinstance(path, str) and isinstance(qualified_name, str):
        return path, qualified_name
    return None


def evaluate_study(manifest_path: Path) -> StudyEvaluationReport:
    """Build symbol-level evidence and ranking metrics from frozen v0.2 inputs."""

    manifest = load_study_manifest(
        manifest_path,
        verify_artifacts=True,
        require_frozen=True,
    )
    study_id = manifest.get("study_id")
    operator_set = manifest.get("operator_set")
    evaluation = manifest.get("evaluation")
    subjects = manifest.get("subjects")
    if (
        not isinstance(study_id, str)
        or not isinstance(operator_set, str)
        or not isinstance(evaluation, dict)
        or not isinstance(subjects, list)
    ):
        raise StudyDataError("Validated study manifest is internally inconsistent.")
    threshold = float(evaluation["weak_adequacy_threshold"])
    minimum_conclusive = int(evaluation["minimum_conclusive_candidates"])
    report = StudyEvaluationReport(
        study_id=study_id,
        operator_set=operator_set,
        weak_adequacy_threshold=threshold,
        minimum_conclusive_candidates=minimum_conclusive,
    )

    for subject in subjects:
        if not isinstance(subject, dict) or subject.get("role") != "study":
            continue
        subject_id = subject.get("id")
        artifacts = subject.get("artifacts")
        if not isinstance(subject_id, str) or not isinstance(artifacts, dict):
            raise StudyDataError("Validated study subject is internally inconsistent.")
        analysis = _read_json(_artifact_path(manifest_path, artifacts.get("analysis")))
        priority = _read_json(_artifact_path(manifest_path, artifacts.get("priority")))
        plan = _read_json(_artifact_path(manifest_path, artifacts.get("mutation_plan")))
        results = _read_json(_artifact_path(manifest_path, artifacts.get("mutation_results")))
        if plan.get("operator_set_version") != operator_set:
            raise StudyDataError(f"{subject_id}: mutation plan uses a different operator set.")
        if results.get("operator_set_version") != operator_set:
            raise StudyDataError(f"{subject_id}: mutation results use a different operator set.")

        analysis_symbols = {
            key
            for item in analysis.get("changed_symbols", [])
            if isinstance(item, dict)
            if (key := _symbol_key(item.get("path"), item.get("qualified_name"))) is not None
        }
        priority_by_symbol = {
            key: item
            for item in priority.get("items", [])
            if isinstance(item, dict)
            if (key := _symbol_key(item.get("path"), item.get("qualified_name"))) is not None
        }
        baseline = priority.get("baseline")
        if not isinstance(baseline, dict) or not isinstance(
            baseline.get("no_test_file_changed"), bool
        ):
            raise StudyDataError(f"{subject_id}: priority artifact has no valid baseline.")

        planned_by_symbol: dict[tuple[str, str], list[dict[str, object]]] = {}
        for candidate in plan.get("candidates", []):
            if not isinstance(candidate, dict):
                continue
            key = _symbol_key(candidate.get("path"), candidate.get("symbol"))
            if key is not None:
                planned_by_symbol.setdefault(key, []).append(candidate)
        results_by_id = {
            item.get("candidate_id"): item
            for item in results.get("candidates", [])
            if isinstance(item, dict) and isinstance(item.get("candidate_id"), str)
        }
        manually_excluded_ids = {
            item.get("candidate_id")
            for item in subject.get("manual_mutant_assessments", [])
            if isinstance(item, dict) and isinstance(item.get("candidate_id"), str)
        }

        for key, planned in planned_by_symbol.items():
            if key not in analysis_symbols:
                raise StudyDataError(f"{subject_id}: mutation plan references an unknown analysis symbol.")
            priority_item = priority_by_symbol.get(key)
            if priority_item is None:
                raise StudyDataError(f"{subject_id}: priority artifact omits a mutated symbol.")
            excluded = [candidate for candidate in planned if candidate.get("id") in manually_excluded_ids]
            included = [candidate for candidate in planned if candidate.get("id") not in manually_excluded_ids]
            outcomes = [
                results_by_id.get(candidate.get("id"))
                for candidate in included
                if isinstance(candidate.get("id"), str)
            ]
            killed = sum(isinstance(item, dict) and item.get("outcome") == "killed" for item in outcomes)
            survived = sum(
                isinstance(item, dict) and item.get("outcome") == "survived" for item in outcomes
            )
            conclusive = killed + survived
            adequacy = killed / conclusive if conclusive else None
            weak = (
                adequacy < threshold
                if adequacy is not None and conclusive >= minimum_conclusive
                else None
            )
            coverage = priority_item.get("coverage")
            report.symbols.append(
                SymbolEvaluation(
                    subject_id=subject_id,
                    path=key[0],
                    qualified_name=key[1],
                    priority_score=int(priority_item.get("review_score", 0)),
                    priority_level=str(priority_item.get("review_level", "unknown")),
                    baseline_no_test_file_changed=baseline["no_test_file_changed"],
                    coverage_status=(
                        str(coverage.get("status", "unknown"))
                        if isinstance(coverage, dict)
                        else "unknown"
                    ),
                    planned_candidates=len(included),
                    manually_excluded=len(excluded),
                    killed=killed,
                    survived=survived,
                    inconclusive=len(included) - conclusive,
                    mutation_adequacy=adequacy,
                    weak_test_evidence=weak,
                )
            )

    report.symbols.sort(
        key=lambda item: (-item.priority_score, item.subject_id, item.path, item.qualified_name)
    )
    if not report.symbols:
        report.notes.append("No study symbols with planned diff-local mutations were available.")
    elif not report._evaluable_symbols():
        report.notes.append("No symbol reached the predeclared conclusive-candidate minimum.")
    elif not any(item.weak_test_evidence for item in report._evaluable_symbols()):
        report.notes.append("No weak-evidence symbol was observed; ranking comparison is not informative.")
    return report
