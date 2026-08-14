import json
import subprocess
from pathlib import Path

from diffmosaic.cli import main
from diffmosaic.screening import screen_repository_history


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _repository_with_two_screened_commits(tmp_path: Path) -> Path:
    repo = tmp_path / "screened-repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@diffmosaic.invalid")
    _git(repo, "config", "user.name", "DiffMosaic tests")
    (repo / "logic.py").write_text("def valid(value):\n    return value > 0\n", encoding="utf-8")
    _git(repo, "add", "logic.py")
    _git(repo, "commit", "-m", "base")
    (repo / "README.md").write_text("documentation\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "docs")
    (repo / "logic.py").write_text(
        "def valid(value):\n    if value > 10:\n        return False\n    return value > 0\n",
        encoding="utf-8",
    )
    _git(repo, "add", "logic.py")
    _git(repo, "commit", "-m", "add boundary")
    return repo


def test_screening_records_every_revision_newest_first_without_dirtying_repository(
    tmp_path: Path,
) -> None:
    repo = _repository_with_two_screened_commits(tmp_path)

    report = screen_repository_history(
        repo,
        max_commits=2,
        operator_set="v0.2",
        repository_label="https://example.test/screened-repo",
    )

    assert [item.ordinal for item in report.revisions] == [1, 2]
    assert report.revisions[0].outcome == "eligible"
    assert report.revisions[0].candidate_count == 1
    assert report.revisions[0].symbol_candidate_count == 1
    assert report.revisions[1].outcome == "excluded_no_supported_mutation_site"
    assert report.repository == "https://example.test/screened-repo"
    assert str(repo.resolve()) not in str(report.to_dict())
    assert _git(repo, "status", "--short") == ""


def test_cli_writes_machine_readable_static_screening(tmp_path: Path) -> None:
    repo = _repository_with_two_screened_commits(tmp_path)
    output = tmp_path / "screening.json"

    exit_code = main(["screen", "--repo", str(repo), "--max-commits", "2", "--output", str(output)])

    data = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert data["selection_rule"]["outcome_blind"] is True
    assert data["summary"]["eligible_revisions"] == 1
