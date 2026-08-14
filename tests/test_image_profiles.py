import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_image_profiles_match_executable_subject_commits_and_commands() -> None:
    corpus = json.loads((ROOT / "corpus" / "pilot-v0.1.json").read_text(encoding="utf-8"))
    profiles = json.loads((ROOT / "images" / "profiles-v0.1.json").read_text(encoding="utf-8"))
    profiled_subjects = {
        subject["id"]: subject
        for subject in corpus["subjects"]
        if subject["role"] in {"candidate", "study", "excluded"}
    }

    assert profiles["schema_version"] == "0.1"
    assert profiles["source_manifest"] == "corpus/pilot-v0.1.json"
    assert {profile["subject_id"] for profile in profiles["profiles"]} == set(profiled_subjects)
    for profile in profiles["profiles"]:
        subject = profiled_subjects[profile["subject_id"]]
        assert profile["head_commit"] == subject["head_commit"]
        assert profile["test_command"] == subject["test_command"]
        assert profile["status"] == ("qualified" if subject["docker_image"] else "unbuilt")
        assert profile["uv_group"] in {"tests", "dev"}
        assert isinstance(profile["apt_packages"], list)
        assert all(package.islower() and package.isascii() for package in profile["apt_packages"])
        assert profile["setuptools_scm_pretend_version"] is None or isinstance(
            profile["setuptools_scm_pretend_version"], str
        )


def test_generic_recipe_keeps_dependencies_outside_runner_workspace() -> None:
    recipe = (ROOT / "images" / "Dockerfile.uv-locked").read_text(encoding="utf-8")

    assert "UV_PROJECT_ENVIRONMENT=/opt/diffmosaic-venv" in recipe
    assert "ARG APT_PACKAGES" in recipe
    assert "ARG SETUPTOOLS_SCM_PRETEND_VERSION" in recipe
    assert "ENV SETUPTOOLS_SCM_PRETEND_VERSION" in recipe
    assert "apt-get install --no-install-recommends --yes ${APT_PACKAGES}" in recipe
    assert "uv sync --locked --group" in recipe
    assert "WORKDIR /workspace" in recipe
