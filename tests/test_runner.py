import io
import tarfile
from pathlib import Path

import pytest

from diffmosaic.runner import (
    DockerSandboxConfig,
    ExecutionResult,
    MutationExecutionError,
    MutationExecutionReport,
    _docker_cli,
    _docker_environment,
    build_docker_command,
    classify_container_completion,
    safe_extract_git_archive,
    run_mutation_plan,
)
from diffmosaic.mutation import MutationPlan


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
    assert "PYTEST_ADDOPTS=-o cache_dir=/tmp/diffmosaic-pytest-cache" in command
    assert "type=bind,source=" in command[command.index("--mount") + 1]
    assert command[command.index("--mount") + 1].endswith(",target=/workspace,readonly")
    assert command[command.index("--workdir") + 1] == "/workspace"
    assert command[-4:] == ["trusted-tests:latest", "python", "-m", "pytest"]

    named_command = build_docker_command(
        config,
        tmp_path / "workspace",
        container_name="diffmosaic-test-container",
    )
    assert named_command[named_command.index("--name") + 1] == "diffmosaic-test-container"


def test_sandbox_allows_a_tmp_working_directory_without_making_source_writable(
    tmp_path: Path,
) -> None:
    config = DockerSandboxConfig(
        image="trusted-tests:latest",
        test_command=("python", "-m", "pytest", "/workspace/tests/test_config.py"),
        working_directory="/tmp",
    )

    command = build_docker_command(config, tmp_path / "workspace")

    assert command[command.index("--workdir") + 1] == "/tmp"
    assert command[command.index("--mount") + 1].endswith(",target=/workspace,readonly")


def test_sandbox_rejects_an_unreviewed_working_directory() -> None:
    with pytest.raises(ValueError, match="/workspace or /tmp"):
        DockerSandboxConfig(
            image="trusted-tests:latest",
            test_command=("python", "-m", "pytest"),
            working_directory="/var/tmp",
        )


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


def test_safe_extract_materialises_an_in_root_symbolic_link(tmp_path: Path) -> None:
    archive_buffer = io.BytesIO()
    with tarfile.open(fileobj=archive_buffer, mode="w") as archive:
        source = tarfile.TarInfo("source.txt")
        source.size = 7
        archive.addfile(source, io.BytesIO(b"trusted"))
        link = tarfile.TarInfo("unsafe-link")
        link.type = tarfile.SYMTYPE
        link.linkname = "source.txt"
        archive.addfile(link)

    workspace = tmp_path / "workspace"
    safe_extract_git_archive(archive_buffer.getvalue(), workspace)

    assert (workspace / "unsafe-link").read_text(encoding="utf-8") == "trusted"


def test_safe_extract_rejects_an_external_symbolic_link(tmp_path: Path) -> None:
    archive_buffer = io.BytesIO()
    with tarfile.open(fileobj=archive_buffer, mode="w") as archive:
        link = tarfile.TarInfo("unsafe-link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        archive.addfile(link)

    with pytest.raises(MutationExecutionError, match="unsafe symbolic link"):
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
        working_directory="/workspace",
        baseline=baseline,
        candidates=[candidate],
    )

    data = report.to_dict()

    assert data["sandbox"]["image_identity"].startswith("trusted-tests@sha256:")
    assert data["sandbox"]["working_directory"] == "/workspace"
    assert data["sandbox"]["limits"] == {
        "timeout_seconds": 120,
        "memory_limit": "1g",
        "cpu_limit": 1.0,
        "pids_limit": 256,
    }
    assert data["summary"]["mutation_adequacy"] == 1.0
    assert data["operator_set_version"] == "v0.1"


def test_expected_image_identity_is_checked_before_any_archive_or_test_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("diffmosaic.runner.inspect_local_docker_image", lambda image: "unexpected-image")
    plan = MutationPlan(base_revision="base", head_revision="head")
    config = DockerSandboxConfig(image="trusted-tests:latest", test_command=("python", "-m", "pytest"))

    with pytest.raises(MutationExecutionError, match="does not match"):
        run_mutation_plan(
            tmp_path,
            plan,
            config,
            expected_image_identity="frozen-image",
        )


def test_docker_cli_uses_user_install_path_when_path_is_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker = tmp_path / "Programs" / "DockerDesktop" / "resources" / "bin" / "docker.exe"
    docker.parent.mkdir(parents=True)
    docker.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr("diffmosaic.runner.shutil.which", lambda name: None)
    monkeypatch.setattr("diffmosaic.runner.os.name", "nt")
    monkeypatch.setattr("diffmosaic.runner.os.environ", {"LOCALAPPDATA": str(tmp_path)})

    executable = _docker_cli()

    assert executable == str(docker)


def test_docker_environment_exposes_the_cli_directory_for_credential_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", "C:\\existing")

    environment = _docker_environment("C:\\Docker Desktop\\resources\\bin\\docker.exe")

    assert environment["PATH"].startswith("C:\\Docker Desktop\\resources\\bin")
