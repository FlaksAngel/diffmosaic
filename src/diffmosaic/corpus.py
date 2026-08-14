"""Validate transparent, version-pinned manifests for research subjects.

The corpus manifest is deliberately data-only. It describes revisions and
commands selected for a study; loading or validating it never clones a
repository, pulls an image, or executes a command.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from pathlib import PurePosixPath


_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_PYTHON_VERSION = re.compile(r"^3\.(?:1[1-9]|[2-9][0-9])$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_VALID_STATUS = {"design", "preliminary", "frozen", "retired"}
_VALID_ROLES = {"calibration", "candidate", "study", "excluded"}
_VALID_SCREENING_OUTCOMES = {"eligible", "excluded_no_supported_mutation_site"}
_VALID_OPERATOR_SETS = {"v0.1", "v0.2"}
_VALID_MANUAL_MUTANT_CLASSIFICATIONS = {"equivalent", "duplicate"}
_VALID_MUTATION_OUTCOMES = {"killed", "survived", "timeout", "infrastructure_error"}
_REQUIRED_STUDY_ARTIFACTS = {
    "analysis",
    "priority",
    "coverage",
    "mutation_plan",
    "mutation_results",
}


def _validate_screening_report_reference(
    subject: dict[object, object],
    issues: list[ManifestIssue],
    subject_id: str | None,
    *,
    required: bool,
) -> None:
    """Validate a checksum-pinned static-screening report reference."""

    reference = subject.get("screening_report")
    if reference is None and not required:
        return
    if not isinstance(reference, dict):
        _issue(
            issues,
            "missing_screening_report" if required else "invalid_screening_report",
            "screening_report must reference the outcome-blind static screen.",
            subject_id,
        )
        return
    if not _is_safe_artifact_path(reference.get("path")):
        _issue(
            issues,
            "unsafe_screening_report_path",
            "screening_report path must be a relative POSIX path inside the repository.",
            subject_id,
        )
    if not isinstance(reference.get("sha256"), str) or not _SHA256.fullmatch(reference["sha256"]):
        _issue(
            issues,
            "invalid_screening_report_sha256",
            "screening_report sha256 must be a lowercase 64-character digest.",
            subject_id,
        )
    ordinal = reference.get("ordinal")
    if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 1:
        _issue(
            issues,
            "invalid_screening_report_ordinal",
            "screening_report ordinal must be a positive integer.",
            subject_id,
        )


@dataclass(frozen=True)
class ManifestIssue:
    """One deterministic validation finding, tied to a subject when possible."""

    severity: str
    code: str
    message: str
    subject_id: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "subject_id": self.subject_id,
        }


@dataclass
class CorpusValidationReport:
    """A serialisable result that makes malformed research inputs visible."""

    study_id: str | None
    subject_count: int
    issues: list[ManifestIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def to_dict(self) -> dict[str, object]:
        errors = sum(issue.severity == "error" for issue in self.issues)
        warnings = sum(issue.severity == "warning" for issue in self.issues)
        return {
            "schema_version": "0.1",
            "study_id": self.study_id,
            "subject_count": self.subject_count,
            "valid": self.valid,
            "summary": {"errors": errors, "warnings": warnings},
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _issue(
    issues: list[ManifestIssue],
    code: str,
    message: str,
    subject_id: str | None = None,
) -> None:
    issues.append(ManifestIssue("error", code, message, subject_id))


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_safe_artifact_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and path.name != ""


def _validate_artifact_references(
    subject: dict[object, object],
    issues: list[ManifestIssue],
    subject_id: str | None,
    *,
    required: bool,
) -> None:
    artifacts = subject.get("artifacts")
    if artifacts is None and not required:
        return
    if not isinstance(artifacts, dict):
        _issue(
            issues,
            "missing_study_artifacts" if required else "invalid_artifacts",
            "artifacts must be an object containing local report references.",
            subject_id,
        )
        return

    missing = _REQUIRED_STUDY_ARTIFACTS - set(artifacts)
    if required and missing:
        _issue(
            issues,
            "missing_required_artifacts",
            "A study subject requires: " + ", ".join(sorted(missing)) + ".",
            subject_id,
        )
    for name, reference in artifacts.items():
        if name not in _REQUIRED_STUDY_ARTIFACTS:
            _issue(issues, "unknown_artifact", f"Unknown artifact name: {name}.", subject_id)
            continue
        if not isinstance(reference, dict):
            _issue(issues, "invalid_artifact_reference", f"{name} must be an object.", subject_id)
            continue
        if not _is_safe_artifact_path(reference.get("path")):
            _issue(
                issues,
                "unsafe_artifact_path",
                f"{name} path must be a relative POSIX path inside the repository.",
                subject_id,
            )
        if not isinstance(reference.get("sha256"), str) or not _SHA256.fullmatch(
            reference["sha256"]
        ):
            _issue(
                issues,
                "invalid_artifact_sha256",
                f"{name} sha256 must be a lowercase 64-character digest.",
                subject_id,
            )


def _validate_execution_profile(
    subject: dict[object, object],
    issues: list[ManifestIssue],
    subject_id: str | None,
    *,
    required: bool,
) -> None:
    execution = subject.get("execution")
    if execution is None and not required:
        return
    if not isinstance(execution, dict):
        _issue(
            issues,
            "missing_execution_profile" if required else "invalid_execution_profile",
            "execution must record sandbox limits for a reproducible study subject.",
            subject_id,
        )
        return
    working_directory = execution.get("working_directory")
    if working_directory not in {"/workspace", "/tmp"}:
        _issue(
            issues,
            "invalid_execution_working_directory",
            "execution working_directory must be /workspace or /tmp.",
            subject_id,
        )
    timeout = execution.get("timeout_seconds")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 1800:
        _issue(
            issues,
            "invalid_execution_timeout",
            "execution timeout_seconds must be an integer between 1 and 1800.",
            subject_id,
        )
    memory = execution.get("memory_limit")
    if not _is_nonempty_string(memory):
        _issue(
            issues,
            "invalid_execution_memory_limit",
            "execution memory_limit must be a non-empty Docker limit string.",
            subject_id,
        )
    cpu = execution.get("cpu_limit")
    if (
        not isinstance(cpu, (float, int))
        or isinstance(cpu, bool)
        or not 0 < cpu <= 4
    ):
        _issue(
            issues,
            "invalid_execution_cpu_limit",
            "execution cpu_limit must be a number greater than zero and at most four.",
            subject_id,
        )
    pids = execution.get("pids_limit")
    if not isinstance(pids, int) or isinstance(pids, bool) or not 16 <= pids <= 1024:
        _issue(
            issues,
            "invalid_execution_pids_limit",
            "execution pids_limit must be an integer between 16 and 1024.",
            subject_id,
        )


def _validate_manual_mutant_assessments(
    subject: dict[object, object],
    issues: list[ManifestIssue],
    subject_id: str | None,
) -> None:
    assessments = subject.get("manual_mutant_assessments")
    if assessments is None:
        return
    if not isinstance(assessments, list):
        _issue(
            issues,
            "invalid_manual_mutant_assessments",
            "manual_mutant_assessments must be an array when present.",
            subject_id,
        )
        return
    seen_ids: set[str] = set()
    for assessment in assessments:
        if not isinstance(assessment, dict):
            _issue(
                issues,
                "invalid_manual_mutant_assessment",
                "Each manual mutant assessment must be an object.",
                subject_id,
            )
            continue
        candidate_id = assessment.get("candidate_id")
        if not _is_nonempty_string(candidate_id):
            _issue(
                issues,
                "invalid_manual_mutant_candidate_id",
                "manual mutant assessment requires candidate_id.",
                subject_id,
            )
        elif candidate_id in seen_ids:
            _issue(
                issues,
                "duplicate_manual_mutant_candidate_id",
                "A candidate may have at most one manual assessment.",
                subject_id,
            )
        else:
            seen_ids.add(candidate_id)
        if assessment.get("classification") not in _VALID_MANUAL_MUTANT_CLASSIFICATIONS:
            _issue(
                issues,
                "invalid_manual_mutant_classification",
                "manual mutant classification must be equivalent or duplicate.",
                subject_id,
            )
        rationale = assessment.get("rationale")
        if not isinstance(rationale, str) or len(rationale.strip()) < 20:
            _issue(
                issues,
                "weak_manual_mutant_rationale",
                "manual mutant assessment rationale must contain at least 20 characters.",
                subject_id,
            )


def _validate_subject(
    subject: object,
    issues: list[ManifestIssue],
    known_ids: set[str],
    schema_version: str,
) -> None:
    if not isinstance(subject, dict):
        _issue(issues, "subject_not_object", "Each subject must be a JSON object.")
        return

    subject_id = subject.get("id")
    label = subject_id if isinstance(subject_id, str) else None
    if not isinstance(subject_id, str) or not _IDENTIFIER.fullmatch(subject_id):
        _issue(issues, "invalid_subject_id", "Subject id must use lowercase kebab-case.", label)
    elif subject_id in known_ids:
        _issue(issues, "duplicate_subject_id", "Subject ids must be unique.", subject_id)
    else:
        known_ids.add(subject_id)

    role = subject.get("role")
    if role not in _VALID_ROLES:
        _issue(
            issues,
            "invalid_role",
            "Subject role must be calibration, candidate, study, or excluded.",
            label,
        )

    repository_url = subject.get("repository_url")
    if not isinstance(repository_url, str) or not repository_url.startswith("https://"):
        _issue(issues, "invalid_repository_url", "repository_url must be an HTTPS URL.", label)

    if not _is_nonempty_string(subject.get("license")):
        _issue(issues, "missing_license", "license must be a non-empty SPDX identifier or label.", label)

    for field_name in ("base_commit", "head_commit"):
        value = subject.get(field_name)
        if not isinstance(value, str) or not _COMMIT.fullmatch(value):
            _issue(
                issues,
                f"invalid_{field_name}",
                f"{field_name} must be a lowercase, 40-character Git commit SHA.",
                label,
            )
    if subject.get("base_commit") == subject.get("head_commit"):
        _issue(issues, "identical_revisions", "base_commit and head_commit must differ.", label)

    if not isinstance(subject.get("python_version"), str) or not _PYTHON_VERSION.fullmatch(
        subject["python_version"]
    ):
        _issue(issues, "invalid_python_version", "python_version must be 3.11 or later.", label)

    test_command = subject.get("test_command")
    if not isinstance(test_command, list) or not test_command or not all(
        _is_nonempty_string(item) for item in test_command
    ):
        _issue(
            issues,
            "invalid_test_command",
            "test_command must be a non-empty array of non-empty argument strings.",
            label,
        )

    image = subject.get("docker_image")
    identity = subject.get("docker_image_identity")
    image_pair_is_null = image is None and identity is None
    image_pair_is_valid = _is_nonempty_string(image) and _is_nonempty_string(identity)
    if not (image_pair_is_null or image_pair_is_valid):
        _issue(
            issues,
            "incomplete_image_identity",
            "docker_image and docker_image_identity must both be strings or both be null.",
            label,
        )
    if role == "study" and image_pair_is_null:
        _issue(
            issues,
            "missing_study_image",
            "A study subject requires a pinned Docker image identity before execution.",
            label,
        )

    screening = subject.get("mutation_screening")
    screening_outcome: object = None
    if screening is not None and not isinstance(screening, dict):
        _issue(
            issues,
            "invalid_mutation_screening",
            "mutation_screening must be a JSON object when present.",
            label,
        )
    if role == "study" and not isinstance(screening, dict):
        _issue(
            issues,
            "missing_mutation_screening",
            "A study subject requires a recorded eligible mutation screening.",
            label,
        )
    if isinstance(screening, dict):
        planner_version = screening.get("planner_version")
        if not _is_nonempty_string(planner_version):
            _issue(
                issues,
                "missing_screening_planner_version",
                "mutation_screening must record the planner version.",
                label,
            )
        max_candidates = screening.get("max_candidates")
        candidate_count = screening.get("candidate_count")
        if (
            not isinstance(max_candidates, int)
            or isinstance(max_candidates, bool)
            or max_candidates < 1
        ):
            _issue(
                issues,
                "invalid_screening_candidate_limit",
                "mutation_screening max_candidates must be a positive integer.",
                label,
            )
        if (
            not isinstance(candidate_count, int)
            or isinstance(candidate_count, bool)
            or candidate_count < 0
            or isinstance(max_candidates, int)
            and not isinstance(max_candidates, bool)
            and candidate_count > max_candidates
        ):
            _issue(
                issues,
                "invalid_screening_candidate_count",
                "mutation_screening candidate_count must be between zero and max_candidates.",
                label,
            )
        screening_outcome = screening.get("outcome")
        if screening_outcome not in _VALID_SCREENING_OUTCOMES:
            _issue(
                issues,
                "invalid_screening_outcome",
                "mutation_screening outcome must be eligible or excluded_no_supported_mutation_site.",
                label,
            )
        elif screening_outcome == "eligible" and candidate_count == 0:
            _issue(
                issues,
                "eligible_without_candidates",
                "An eligible screening requires at least one planned candidate.",
                label,
            )
        elif screening_outcome == "excluded_no_supported_mutation_site" and candidate_count != 0:
            _issue(
                issues,
                "excluded_with_candidates",
                "No-site exclusion requires a zero candidate count.",
                label,
            )
    if role == "study" and screening_outcome != "eligible":
        _issue(
            issues,
            "study_not_eligible_for_mutation_analysis",
            "A study subject must have an eligible mutation screening.",
            label,
        )

    if schema_version == "0.2":
        _validate_screening_report_reference(
            subject,
            issues,
            label,
            required=role in {"candidate", "study"},
        )
        _validate_artifact_references(
            subject,
            issues,
            label,
            required=role == "study",
        )
        _validate_execution_profile(
            subject,
            issues,
            label,
            required=role == "study",
        )
        _validate_manual_mutant_assessments(subject, issues, label)

    if role == "excluded" and not _is_nonempty_string(subject.get("exclusion_reason")):
        _issue(
            issues,
            "missing_exclusion_reason",
            "An excluded subject requires a non-empty exclusion_reason.",
            label,
        )

    rationale = subject.get("selection_rationale")
    if not isinstance(rationale, str) or len(rationale.strip()) < 20:
        _issue(
            issues,
            "weak_selection_rationale",
            "selection_rationale must explain inclusion in at least 20 characters.",
            label,
        )


def _validate_study_v0_2_metadata(data: dict[object, object], issues: list[ManifestIssue]) -> None:
    operator_set = data.get("operator_set")
    if operator_set not in _VALID_OPERATOR_SETS:
        _issue(
            issues,
            "invalid_operator_set",
            "operator_set must be one of: " + ", ".join(sorted(_VALID_OPERATOR_SETS)) + ".",
        )

    evaluation = data.get("evaluation")
    if not isinstance(evaluation, dict):
        _issue(issues, "missing_evaluation_config", "evaluation must be a JSON object.")
        return
    threshold = evaluation.get("weak_adequacy_threshold")
    if (
        not isinstance(threshold, (float, int))
        or isinstance(threshold, bool)
        or not 0 <= threshold <= 1
    ):
        _issue(
            issues,
            "invalid_weak_adequacy_threshold",
            "weak_adequacy_threshold must be a number between zero and one.",
        )
    minimum = evaluation.get("minimum_conclusive_candidates")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        _issue(
            issues,
            "invalid_minimum_conclusive_candidates",
            "minimum_conclusive_candidates must be a positive integer.",
        )


def validate_corpus_data(data: object) -> CorpusValidationReport:
    """Validate manifest structure without accessing any referenced resource."""

    issues: list[ManifestIssue] = []
    if not isinstance(data, dict):
        _issue(issues, "manifest_not_object", "The manifest root must be a JSON object.")
        return CorpusValidationReport(None, 0, issues)

    study_id_value = data.get("study_id")
    study_id = study_id_value if isinstance(study_id_value, str) else None
    if not isinstance(study_id_value, str) or not _IDENTIFIER.fullmatch(study_id_value):
        _issue(issues, "invalid_study_id", "study_id must use lowercase kebab-case.")
    schema_version = data.get("schema_version")
    if schema_version not in {"0.1", "0.2"}:
        _issue(issues, "unsupported_schema", "schema_version must be either '0.1' or '0.2'.")
    if data.get("status") not in _VALID_STATUS:
        _issue(issues, "invalid_status", "status must be preliminary, frozen, or retired.")

    criteria = data.get("inclusion_criteria")
    if not isinstance(criteria, list) or len(criteria) < 3 or not all(
        _is_nonempty_string(item) for item in criteria
    ):
        _issue(
            issues,
            "invalid_inclusion_criteria",
            "inclusion_criteria must contain at least three non-empty strings.",
        )

    if schema_version == "0.2":
        _validate_study_v0_2_metadata(data, issues)

    subjects = data.get("subjects")
    allow_empty_design = schema_version == "0.2" and data.get("status") == "design"
    if not isinstance(subjects, list) or (not subjects and not allow_empty_design):
        _issue(
            issues,
            "missing_subjects",
            "subjects must be a non-empty array unless a v0.2 study is in design status.",
        )
        return CorpusValidationReport(study_id, 0, issues)

    known_ids: set[str] = set()
    for subject in subjects:
        _validate_subject(subject, issues, known_ids, schema_version)
    return CorpusValidationReport(study_id, len(subjects), issues)


def _verify_artifact_files(
    manifest_path: Path,
    data: dict[object, object],
    report: CorpusValidationReport,
) -> None:
    """Validate local artifact checksums and immutable revision metadata."""

    if data.get("schema_version") != "0.2":
        return
    subjects = data.get("subjects")
    if not isinstance(subjects, list):
        return

    repository_root = manifest_path.parent.parent.resolve()
    operator_set = data.get("operator_set")
    for subject in subjects:
        if not isinstance(subject, dict):
            continue
        subject_id = subject.get("id") if isinstance(subject.get("id"), str) else None
        _verify_screening_report(
            repository_root,
            subject,
            report.issues,
            subject_id,
            operator_set,
        )
        if subject.get("role") != "study":
            continue
        artifacts = subject.get("artifacts")
        if not isinstance(artifacts, dict):
            continue
        loaded_artifacts: dict[str, dict[object, object]] = {}
        for name in sorted(_REQUIRED_STUDY_ARTIFACTS):
            reference = artifacts.get(name)
            if not isinstance(reference, dict) or not _is_safe_artifact_path(reference.get("path")):
                continue
            artifact_path = (repository_root / str(reference["path"])).resolve()
            if not artifact_path.is_relative_to(repository_root):
                _issue(
                    report.issues,
                    "artifact_path_escapes_repository",
                    f"{name} path resolves outside the repository.",
                    subject_id,
                )

                continue
            try:
                raw = artifact_path.read_bytes()
            except FileNotFoundError:
                _issue(
                    report.issues,
                    "artifact_missing",
                    f"{name} artifact does not exist: {reference['path']}.",
                    subject_id,
                )
                continue
            actual_digest = hashlib.sha256(raw).hexdigest()
            if actual_digest != reference.get("sha256"):
                _issue(
                    report.issues,
                    "artifact_digest_mismatch",
                    f"{name} artifact checksum does not match the manifest.",
                    subject_id,
                )
                continue
            try:
                artifact = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                _issue(
                    report.issues,
                    "artifact_not_json",
                    f"{name} artifact is not valid UTF-8 JSON.",
                    subject_id,
                )
                continue
            if not isinstance(artifact, dict):
                _issue(
                    report.issues,
                    "artifact_not_object",
                    f"{name} artifact must contain a JSON object.",
                    subject_id,
                )
                continue
            loaded_artifacts[name] = artifact
            if name != "coverage":
                for artifact_field, subject_field in (
                    ("base_revision", "base_commit"),
                    ("head_revision", "head_commit"),
                ):
                    if artifact.get(artifact_field) != subject.get(subject_field):
                        _issue(
                            report.issues,
                            "artifact_revision_mismatch",
                            f"{name} {artifact_field} does not match the subject.",
                            subject_id,
                        )
            if name == "mutation_plan" and artifact.get("operator_set_version") != operator_set:
                _issue(
                    report.issues,
                    "artifact_operator_set_mismatch",
                    "mutation_plan operator_set_version does not match the study.",
                    subject_id,
                )
            if name == "mutation_results" and artifact.get("operator_set_version") != operator_set:
                _issue(
                    report.issues,
                    "artifact_operator_set_mismatch",
                    "mutation_results operator_set_version does not match the study.",
                    subject_id,
                )

        _verify_mutation_artifact_consistency(
            subject,
            loaded_artifacts,
            report.issues,
            subject_id,
        )

        assessments = subject.get("manual_mutant_assessments")
        if not isinstance(assessments, list):
            continue
        plan_reference = artifacts.get("mutation_plan")
        result_reference = artifacts.get("mutation_results")
        if not isinstance(plan_reference, dict) or not isinstance(result_reference, dict):
            continue
        plan_path = (repository_root / str(plan_reference.get("path", ""))).resolve()
        result_path = (repository_root / str(result_reference.get("path", ""))).resolve()
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            results = json.loads(result_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if not isinstance(plan, dict) or not isinstance(results, dict):
            continue
        planned_ids = {
            candidate.get("id")
            for candidate in plan.get("candidates", [])
            if isinstance(candidate, dict) and isinstance(candidate.get("id"), str)
        }
        result_outcomes = {
            candidate.get("candidate_id"): candidate.get("outcome")
            for candidate in results.get("candidates", [])
            if isinstance(candidate, dict) and isinstance(candidate.get("candidate_id"), str)
        }
        for assessment in assessments:
            if not isinstance(assessment, dict) or not isinstance(
                assessment.get("candidate_id"), str
            ):
                continue
            candidate_id = assessment["candidate_id"]
            if candidate_id not in planned_ids:
                _issue(
                    report.issues,
                    "manual_mutant_unknown_candidate",
                    "Manual mutant assessment does not reference a planned candidate.",
                    subject_id,
                )
            elif result_outcomes.get(candidate_id) != "survived":
                _issue(
                    report.issues,
                    "manual_mutant_not_survived",
                    "Only a recorded survived candidate may be marked equivalent or duplicate.",
                    subject_id,
                )


def _verify_screening_report(
    repository_root: Path,
    subject: dict[object, object],
    issues: list[ManifestIssue],
    subject_id: str | None,
    operator_set: object,
) -> None:
    """Check that a candidate derives from the exact saved static screen."""

    reference = subject.get("screening_report")
    if not isinstance(reference, dict) or not _is_safe_artifact_path(reference.get("path")):
        return
    path = (repository_root / str(reference["path"])).resolve()
    if not path.is_relative_to(repository_root):
        _issue(
            issues,
            "screening_report_path_escapes_repository",
            "screening_report path resolves outside the repository.",
            subject_id,
        )
        return
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        _issue(
            issues,
            "screening_report_missing",
            f"screening_report does not exist: {reference['path']}.",
            subject_id,
        )
        return
    if hashlib.sha256(raw).hexdigest() != reference.get("sha256"):
        _issue(
            issues,
            "screening_report_digest_mismatch",
            "screening_report checksum does not match the manifest.",
            subject_id,
        )
        return
    try:
        screen = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _issue(
            issues,
            "screening_report_not_json",
            "screening_report is not valid UTF-8 JSON.",
            subject_id,
        )
        return
    if not isinstance(screen, dict):
        _issue(
            issues,
            "screening_report_not_object",
            "screening_report must be a JSON object.",
            subject_id,
        )
        return
    screening = subject.get("mutation_screening")
    if (
        screen.get("repository") != subject.get("repository_url")
        or screen.get("operator_set") != operator_set
        or not isinstance(screening, dict)
        or screen.get("planner_version") != screening.get("planner_version")
    ):
        _issue(
            issues,
            "screening_report_metadata_mismatch",
            "screening_report repository, planner version, or operator set does not match the subject.",
            subject_id,
        )
        return
    ordinal = reference.get("ordinal")
    revisions = screen.get("revisions")
    entry = (
        next(
            (
                item
                for item in revisions
                if isinstance(item, dict) and item.get("ordinal") == ordinal
            ),
            None,
        )
        if isinstance(revisions, list)
        else None
    )
    if (
        not isinstance(entry, dict)
        or entry.get("outcome") != "eligible"
        or entry.get("base_commit") != subject.get("base_commit")
        or entry.get("head_commit") != subject.get("head_commit")
        or entry.get("candidate_count") != screening.get("candidate_count")
        or not isinstance(entry.get("symbol_candidate_count"), int)
        or entry["symbol_candidate_count"] < 1
    ):
        _issue(
            issues,
            "screening_report_candidate_mismatch",
            "screening_report does not contain this eligible candidate with matching revisions.",
            subject_id,
        )


def _verify_mutation_artifact_consistency(
    subject: dict[object, object],
    artifacts: dict[str, dict[object, object]],
    issues: list[ManifestIssue],
    subject_id: str | None,
) -> None:
    """Ensure a frozen mutation result is complete and ran under declared controls."""

    plan = artifacts.get("mutation_plan")
    results = artifacts.get("mutation_results")
    if plan is None or results is None:
        return
    planned = plan.get("candidates")
    recorded = results.get("candidates")
    if not isinstance(planned, list) or not isinstance(recorded, list):
        _issue(
            issues,
            "invalid_mutation_artifact_candidates",
            "Mutation plan and results must both contain candidate arrays.",
            subject_id,
        )
        return

    planned_ids = [
        item.get("id")
        for item in planned
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    recorded_ids = [
        item.get("candidate_id")
        for item in recorded
        if isinstance(item, dict) and isinstance(item.get("candidate_id"), str)
    ]
    if len(planned_ids) != len(planned) or len(set(planned_ids)) != len(planned_ids):
        _issue(
            issues,
            "invalid_mutation_plan_candidates",
            "Mutation plan candidates require unique string ids.",
            subject_id,
        )
    if len(recorded_ids) != len(recorded) or len(set(recorded_ids)) != len(recorded_ids):
        _issue(
            issues,
            "invalid_mutation_result_candidates",
            "Mutation result candidates require unique string ids.",
            subject_id,
        )
    invalid_outcomes = [
        item
        for item in recorded
        if not isinstance(item, dict) or item.get("outcome") not in _VALID_MUTATION_OUTCOMES
    ]
    if invalid_outcomes:
        _issue(
            issues,
            "invalid_mutation_outcome",
            "Mutation result outcomes must be killed, survived, timeout, or infrastructure_error.",
            subject_id,
        )
    if set(planned_ids) != set(recorded_ids):
        _issue(
            issues,
            "mutation_result_candidate_mismatch",
            "Mutation results must contain exactly the planned candidate ids.",
            subject_id,
        )

    screening = subject.get("mutation_screening")
    if isinstance(screening, dict) and screening.get("candidate_count") != len(planned_ids):
        _issue(
            issues,
            "mutation_plan_count_mismatch",
            "mutation_screening candidate_count does not match the saved mutation plan.",
            subject_id,
        )

    baseline = results.get("baseline")
    if not isinstance(baseline, dict) or baseline.get("outcome") != "passed":
        _issue(
            issues,
            "mutation_baseline_not_passed",
            "A frozen study subject requires a recorded passing mutation baseline.",
            subject_id,
        )

    sandbox = results.get("sandbox")
    execution = subject.get("execution")
    expected_command = subject.get("test_command")
    if not isinstance(sandbox, dict) or not isinstance(execution, dict):
        _issue(
            issues,
            "missing_recorded_execution_controls",
            "Mutation results must record the frozen Docker image, command, and limits.",
            subject_id,
        )
        return
    if (
        sandbox.get("image") != subject.get("docker_image")
        or sandbox.get("image_identity") != subject.get("docker_image_identity")
        or sandbox.get("test_command") != expected_command
        or sandbox.get("working_directory") != execution.get("working_directory")
    ):
        _issue(
            issues,
            "mutation_execution_identity_mismatch",
            "Mutation result image, test command, or working directory does not match the frozen subject.",
            subject_id,
        )
    limits = sandbox.get("limits")
    if not isinstance(limits, dict) or any(
        limits.get(key) != execution.get(key)
        for key in ("timeout_seconds", "memory_limit", "cpu_limit", "pids_limit")
    ):
        _issue(
            issues,
            "mutation_execution_limits_mismatch",
            "Mutation result sandbox limits do not match the frozen subject.",
            subject_id,
        )


def validate_corpus_manifest(
    path: Path,
    *,
    verify_artifacts: bool = False,
) -> CorpusValidationReport:
    """Read and validate one local JSON manifest without executing target code."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return CorpusValidationReport(
            None,
            0,
            [ManifestIssue("error", "manifest_missing", f"Manifest does not exist: {path}")],
        )
    except json.JSONDecodeError as exc:
        return CorpusValidationReport(
            None,
            0,
            [
                ManifestIssue(
                    "error",
                    "invalid_json",
                    f"Manifest is not valid JSON (line {exc.lineno}, column {exc.colno}).",
                )
            ],
        )
    report = validate_corpus_data(data)
    if verify_artifacts and report.valid and isinstance(data, dict):
        _verify_artifact_files(path, data, report)
    return report
