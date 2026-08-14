import json
from pathlib import Path


def test_v0_2_profiles_cover_every_preliminary_selected_subject_transparently() -> None:
    root = Path(__file__).parents[1]
    manifest = json.loads((root / "corpus" / "study-v0.2.json").read_text(encoding="utf-8"))
    profiles = json.loads((root / "images" / "profiles-v0.2.json").read_text(encoding="utf-8"))

    selected_subjects = {
        subject["id"]: subject
        for subject in manifest["subjects"]
        if subject["role"] in {"candidate", "study", "excluded"}
    }
    by_subject = {profile["subject_id"]: profile for profile in profiles["profiles"]}

    assert profiles["source_manifest"] == "corpus/study-v0.2.json"
    assert set(by_subject) == set(selected_subjects)
    for subject_id, subject in selected_subjects.items():
        profile = by_subject[subject_id]
        assert profile["head_commit"] == subject["head_commit"]
        if profile["status"] in {"unbuilt", "built", "qualified"}:
            assert (root / profile["dockerfile"]).is_file()
            assert profile["test_command"] == subject["test_command"]
            assert profile.get("working_directory", "/workspace") == subject.get(
                "execution", {}
            ).get("working_directory", "/workspace")
            if profile["status"] in {"built", "qualified"}:
                assert "@sha256:" in profile["image_identity"]
            version = profile.get("setuptools_scm_pretend_version")
            assert version is None or isinstance(version, str)
        else:
            assert profile["status"] == "deferred"
            assert len(profile["deferred_reason"]) >= 20
