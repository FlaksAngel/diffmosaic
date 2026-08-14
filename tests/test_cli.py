import json
import subprocess
from pathlib import Path

from diffmosaic.cli import main


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def test_cli_analyses_real_git_revisions_without_dirtying_repository(tmp_path: Path) -> None:
    repo = tmp_path / "sample-repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@diffmosaic.invalid")
    _git(repo, "config", "user.name", "DiffMosaic tests")

    source = repo / "pricing.py"
    source.write_text(
        "def total(price, discount):\n"
        "    return price - discount\n",
        encoding="utf-8",
    )
    _git(repo, "add", "pricing.py")
    _git(repo, "commit", "-m", "base")

    source.write_text(
        "def total(price, discount):\n"
        "    if discount > price:\n"
        "        raise ValueError('discount exceeds price')\n"
        "    return price - discount\n",
        encoding="utf-8",
    )
    _git(repo, "add", "pricing.py")
    _git(repo, "commit", "-m", "validate discount")

    output = tmp_path / "report.json"
    coverage_json = tmp_path / "coverage.json"
    coverage_json.write_text(
        json.dumps(
            {
                "files": {
                    str(source): {"executed_lines": [1, 2, 4]},
                }
            }
        ),
        encoding="utf-8",
    )
    exit_code = main(
        [
            "analyze",
            "--repo",
            str(repo),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
            "--coverage-json",
            str(coverage_json),
            "--format",
            "json",
            "--output",
            str(output),
        ]
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert data["changed_symbols"][0]["qualified_name"] == "total"
    assert data["changed_symbols"][0]["changed_lines"] == [2, 3]
    assert data["changed_symbols"][0]["coverage"] == {
        "executed_changed_lines": [2],
        "status": "available",
    }
    assert _git(repo, "status", "--short") == ""


def test_cli_creates_mutation_plan_without_dirtying_repository(tmp_path: Path) -> None:
    repo = tmp_path / "sample-repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@diffmosaic.invalid")
    _git(repo, "config", "user.name", "DiffMosaic tests")

    source = repo / "pricing.py"
    source.write_text(
        "def total(price, discount):\n"
        "    return price - discount\n",
        encoding="utf-8",
    )
    _git(repo, "add", "pricing.py")
    _git(repo, "commit", "-m", "base")

    source.write_text(
        "def total(price, discount):\n"
        "    if discount > price:\n"
        "        raise ValueError('discount exceeds price')\n"
        "    return price - discount\n",
        encoding="utf-8",
    )
    _git(repo, "add", "pricing.py")
    _git(repo, "commit", "-m", "validate discount")

    output = tmp_path / "mutation-plan.json"
    exit_code = main(
        [
            "mutate-plan",
            "--repo",
            str(repo),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
            "--output",
            str(output),
        ]
    )

    plan = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert plan["candidate_count"] == 1
    assert plan["candidates"][0]["original_operator"] == ">"
    assert plan["candidates"][0]["replacement_operator"] == ">="
    assert _git(repo, "status", "--short") == ""


def test_cli_refuses_mutation_execution_without_explicit_acknowledgement(tmp_path: Path) -> None:
    output = tmp_path / "experiment.json"

    exit_code = main(
        [
            "mutate-run",
            "--repo",
            str(tmp_path),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
            "--image",
            "trusted-tests:latest",
            "--output",
            str(output),
            "--test-command",
            "python",
            "-m",
            "pytest",
        ]
    )

    assert exit_code == 2
    assert not output.exists()


def test_cli_validates_committed_calibration_manifest(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    output = tmp_path / "corpus-validation.json"

    exit_code = main(
        [
            "corpus-validate",
            "--manifest",
            str(root / "corpus" / "pilot-v0.1.json"),
            "--output",
            str(output),
        ]
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert report["valid"] is True
    assert report["subject_count"] == 4
