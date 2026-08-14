import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_unbuilt_image_profiles_match_candidate_commits_and_commands() -> None:
    corpus = json.loads((ROOT / "corpus" / "pilot-v0.1.json").read_text(encoding="utf-8"))
    profiles = json.loads((ROOT / "images" / "profiles-v0.1.json").read_text(encoding="utf-8"))
    candidates = {
        subject["id"]: subject for subject in corpus["subjects"] if subject["role"] == "candidate"
    }

    assert profiles["schema_version"] == "0.1"
    assert profiles["source_manifest"] == "corpus/pilot-v0.1.json"
    assert {profile["subject_id"] for profile in profiles["profiles"]} == set(candidates)
    for profile in profiles["profiles"]:
        subject = candidates[profile["subject_id"]]
        assert profile["head_commit"] == subject["head_commit"]
        assert profile["test_command"] == subject["test_command"]
        assert profile["status"] == "unbuilt"
        assert profile["uv_group"] in {"tests", "dev"}


def test_generic_recipe_keeps_dependencies_outside_runner_workspace() -> None:
    recipe = (ROOT / "images" / "Dockerfile.uv-locked").read_text(encoding="utf-8")

    assert "UV_PROJECT_ENVIRONMENT=/opt/diffmosaic-venv" in recipe
    assert "uv sync --locked --group" in recipe
    assert "WORKDIR /workspace" in recipe
