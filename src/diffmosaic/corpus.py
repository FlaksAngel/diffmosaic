"""Validate transparent, version-pinned manifests for research subjects.

The corpus manifest is deliberately data-only. It describes revisions and
commands selected for a study; loading or validating it never clones a
repository, pulls an image, or executes a command.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_PYTHON_VERSION = re.compile(r"^3\.(?:1[1-9]|[2-9][0-9])$")
_VALID_STATUS = {"preliminary", "frozen", "retired"}
_VALID_ROLES = {"calibration", "candidate", "study"}


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


def _validate_subject(
    subject: object,
    issues: list[ManifestIssue],
    known_ids: set[str],
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

    if subject.get("role") not in _VALID_ROLES:
        _issue(
            issues,
            "invalid_role",
            "Subject role must be calibration, candidate, or study.",
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
    if subject.get("role") == "study" and image_pair_is_null:
        _issue(
            issues,
            "missing_study_image",
            "A study subject requires a pinned Docker image identity before execution.",
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
    if data.get("schema_version") != "0.1":
        _issue(issues, "unsupported_schema", "schema_version must be exactly '0.1'.")
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

    subjects = data.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        _issue(issues, "missing_subjects", "subjects must be a non-empty array.")
        return CorpusValidationReport(study_id, 0, issues)

    known_ids: set[str] = set()
    for subject in subjects:
        _validate_subject(subject, issues, known_ids)
    return CorpusValidationReport(study_id, len(subjects), issues)


def validate_corpus_manifest(path: Path) -> CorpusValidationReport:
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
    return validate_corpus_data(data)
