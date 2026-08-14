import io
import tarfile
from pathlib import Path

import pytest

from diffmosaic.runner import (
    DockerSandboxConfig,
    ExecutionResult,
    MutationExecutionError,
    MutationExecutionReport,
    build_docker_command,
    classify_container_completion,
    safe_extract_git_archive,
)


def test_docker_command_contains_fixed_isolation_controls(tmp_path: Path) -> None:
    config = DockerSandboxConfig(
        image="trusted-tests:latest",
        test_command=("python", "-m", "pytest"),
    )

    command = build_docker_command(config, tmp_path / "workspace")

    assert command[:3] == ["docker", "run", "--rm"]
    assert ["--network", "none"] == command[3:5]
    assert ["--ipc", "none"] == command[5:7]
    assert "--read-only" in command
    assert command[command.index("--cap-drop") + 1] == "ALL"
    assert "no-new-privileges:true" in command
    assert "type=bind,source=" in command[command.index("--mount") + 1]
    assert command[command.index("--mount") + 1].endswith(",target=/workspace,readonly")
    assert command[-4:] == ["trusted-tests:latest", "python", "-m", "pytest"]

    named_command = build_docker_command(
        config,
        tmp_path / "workspace",
        container_name="diffmosaic-test-container",
    )
    assert named_command[named_command.index("--name") + 1] == "diffmosaic-test-container"


def test_classification_keeps_container_failure_distinct_from_killed_mutant() -> None:
    killed = classify_container_completion(
        "candidate", exit_code=1, timed_out=False, duration_seconds=0.1
    )
    infrastructure = classify_container_completion(
        "candidate", exit_code=125, timed_out=False, duration_seconds=0.1
    )
    timeout = classify_container_completion(
        "candidate", exit_code=None, timed_out=True, duration_seconds=120
    )

    assert killed.outcome == "killed"
    assert infrastructure.outcome == "infrastructure_error"
    assert timeout.outcome == "timeout"


def test_safe_extract_rejects_symbolic_links(tmp_path: Path) -> None:
    archive_buffer = io.BytesIO()
    with tarfile.open(fileobj=archive_buffer, mode="w") as archive:
        link = tarfile.TarInfo("unsafe-link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        archive.addfile(link)

    with pytest.raises(MutationExecutionError, match="non-regular"):
        safe_extract_git_archive(archive_buffer.getvalue(), tmp_path / "workspace")


def test_sandbox_config_rejects_unbounded_timeout() -> None:
    with pytest.raises(ValueError, match="between 1 and 1800"):
        DockerSandboxConfig(
            image="trusted-tests:latest",
            test_command=("python", "-m", "pytest"),
            timeout_seconds=1801,
        )


def test_execution_report_records_identity_and_mutation_metadata() -> None:
    baseline = ExecutionResult(None, "passed", 0, 0.1, "", "")
    candidate = ExecutionResult("pricing.py:2:4:comparison_operator:>-to->=", "killed", 1, 0.1, "", "")
    report = MutationExecutionReport(
        base_revision="a" * 40,
        head_revision="b" * 40,
        image="trusted-tests:latest",
        image_identity="trusted-tests@sha256:" + "c" * 64,
        test_command=("python", "-m", "pytest"),
        baseline=baseline,
        candidates=[candidate],
    )

    data = report.to_dict()

    assert data["sandbox"]["image_identity"].startswith("trusted-tests@sha256:")
    assert data["summary"]["mutation_adequacy"] == 1.0
