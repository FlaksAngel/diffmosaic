from diffmosaic.corpus import validate_corpus_data


def _valid_manifest() -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "study_id": "pilot-study",
        "status": "preliminary",
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
                "base_commit": "a" * 40,
                "head_commit": "b" * 40,
                "python_version": "3.11",
                "test_command": ["python", "-m", "pytest"],
                "docker_image": "sample-tests:1",
                "docker_image_identity": "sha256:" + "c" * 64,
                "mutation_screening": {
                    "planner_version": "0.7.0",
                    "max_candidates": 20,
                    "candidate_count": 1,
                    "outcome": "eligible",
                },
                "selection_rationale": "Small public fixture selected to exercise the pilot manifest contract.",
            }
        ],
    }


def test_valid_manifest_is_accepted_without_accessing_subject_resources() -> None:
    report = validate_corpus_data(_valid_manifest())

    assert report.valid
    assert report.to_dict()["summary"] == {"errors": 0, "warnings": 0}


def test_study_subject_requires_exact_revisions_and_image_identity() -> None:
    manifest = _valid_manifest()
    subject = manifest["subjects"][0]
    assert isinstance(subject, dict)
    subject["head_commit"] = "moving-main"
    subject["docker_image_identity"] = None

    report = validate_corpus_data(manifest)
    codes = {issue.code for issue in report.issues}

    assert not report.valid
    assert "invalid_head_commit" in codes
    assert "incomplete_image_identity" in codes


def test_candidate_can_be_registered_before_a_trusted_image_is_built() -> None:
    manifest = _valid_manifest()
    subject = manifest["subjects"][0]
    assert isinstance(subject, dict)
    subject["role"] = "candidate"
    subject["docker_image"] = None
    subject["docker_image_identity"] = None

    report = validate_corpus_data(manifest)

    assert report.valid


def test_excluded_subject_requires_a_reason_and_zero_site_screening() -> None:
    manifest = _valid_manifest()
    subject = manifest["subjects"][0]
    assert isinstance(subject, dict)
    subject["role"] = "excluded"
    subject["docker_image"] = None
    subject["docker_image_identity"] = None
    subject["mutation_screening"] = {
        "planner_version": "0.7.0",
        "max_candidates": 20,
        "candidate_count": 0,
        "outcome": "excluded_no_supported_mutation_site",
    }

    missing_reason = validate_corpus_data(manifest)
    assert "missing_exclusion_reason" in {issue.code for issue in missing_reason.issues}

    subject["exclusion_reason"] = "No changed comparison or Boolean connector is supported by the planner."
    accepted = validate_corpus_data(manifest)
    assert accepted.valid


def test_missing_study_screening_is_a_validation_error_not_a_crash() -> None:
    manifest = _valid_manifest()
    subject = manifest["subjects"][0]
    assert isinstance(subject, dict)
    subject.pop("mutation_screening")

    report = validate_corpus_data(manifest)

    assert not report.valid
    assert "missing_mutation_screening" in {issue.code for issue in report.issues}
