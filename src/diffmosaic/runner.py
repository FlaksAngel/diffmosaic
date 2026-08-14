"""Execute planned mutations in a deliberately restricted Docker sandbox.

The runner is opt-in. DiffMosaic never runs repository code during ordinary
analysis or planning, and this module requires both a supplied container image
and an explicit allow-execution flag in the CLI.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from diffmosaic.mutation import MutationCandidate, MutationPlan


class MutationExecutionError(RuntimeError):
    """Raised when the runner cannot create a controlled mutation experiment."""


def _docker_cli() -> str:
    """Locate Docker without requiring a terminal restart after a user install."""

    if docker_from_path := shutil.which("docker"):
        return docker_from_path
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            user_install = (
                Path(local_app_data)
                / "Programs"
                / "DockerDesktop"
                / "resources"
                / "bin"
                / "docker.exe"
            )
            if user_install.is_file():
                return str(user_install)
    raise MutationExecutionError("Docker CLI is not installed or is not on PATH.")


def _docker_environment(docker_cli: str) -> dict[str, str]:
    """Expose Docker Desktop credential helpers beside a discovered user CLI."""

    environment = os.environ.copy()
    helper_directory = str(Path(docker_cli).parent)
    current_path = environment.get("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    if helper_directory not in path_parts:
        environment["PATH"] = helper_directory + (
            os.pathsep + current_path if current_path else ""
        )
    return environment


@dataclass(frozen=True)
class DockerSandboxConfig:
    """Resource and isolation limits for a single test-suite invocation."""

    image: str
    test_command: tuple[str, ...]
    working_directory: str = "/workspace"
    timeout_seconds: int = 120
    memory_limit: str = "1g"
    cpu_limit: float = 1.0
    pids_limit: int = 256
    max_archive_bytes: int = 50 * 1024 * 1024

    def __post_init__(self) -> None:
        if not self.image.strip():
            raise ValueError("A non-empty Docker image is required.")
        if not self.test_command or any(not argument for argument in self.test_command):
            raise ValueError("A test command is required.")
        if self.working_directory not in {"/workspace", "/tmp"}:
            raise ValueError("working_directory must be /workspace or /tmp.")
        if not 1 <= self.timeout_seconds <= 1800:
            raise ValueError("timeout_seconds must be between 1 and 1800.")
        if not 0 < self.cpu_limit <= 4:
            raise ValueError("cpu_limit must be greater than 0 and at most 4.")
        if not 16 <= self.pids_limit <= 1024:
            raise ValueError("pids_limit must be between 16 and 1024.")
        if self.max_archive_bytes < 1:
            raise ValueError("max_archive_bytes must be positive.")


@dataclass(frozen=True)
class ExecutionResult:
    """One bounded test-suite invocation and its intentionally truncated logs."""

    candidate_id: str | None
    outcome: str
    exit_code: int | None
    duration_seconds: float
    stdout_tail: str
    stderr_tail: str

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "outcome": self.outcome,
            "exit_code": self.exit_code,
            "duration_seconds": round(self.duration_seconds, 3),
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
        }


@dataclass
class MutationExecutionReport:
    """Baseline proof and candidate outcomes for one immutable Git revision."""

    base_revision: str
    head_revision: str
    image: str
    test_command: tuple[str, ...]
    working_directory: str
    image_identity: str
    baseline: ExecutionResult
    planned_candidates: list[MutationCandidate] = field(default_factory=list)
    candidates: list[ExecutionResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    operator_set_version: str = "v0.1"
    timeout_seconds: int = 120
    memory_limit: str = "1g"
    cpu_limit: float = 1.0
    pids_limit: int = 256

    def to_dict(self) -> dict[str, object]:
        killed = sum(item.outcome == "killed" for item in self.candidates)
        survived = sum(item.outcome == "survived" for item in self.candidates)
        executable = killed + survived
        return {
            "schema_version": "0.1",
            "base_revision": self.base_revision,
            "head_revision": self.head_revision,
            "operator_set_version": self.operator_set_version,
            "sandbox": {
                "image": self.image,
                "image_identity": self.image_identity,
                "test_command": list(self.test_command),
                "working_directory": self.working_directory,
                "network": "none",
                "root_filesystem": "read_only",
                "limits": {
                    "timeout_seconds": self.timeout_seconds,
                    "memory_limit": self.memory_limit,
                    "cpu_limit": self.cpu_limit,
                    "pids_limit": self.pids_limit,
                },
            },
            "baseline": self.baseline.to_dict(),
            "planned_candidates": [
                candidate.site.to_dict() for candidate in self.planned_candidates
            ],
            "summary": {
                "candidate_count": len(self.candidates),
                "killed": killed,
                "survived": survived,
                "inconclusive": len(self.candidates) - executable,
                "mutation_adequacy": (killed / executable) if executable else None,
            },
            "candidates": [result.to_dict() for result in self.candidates],
            "notes": self.notes,
        }


def build_docker_command(
    config: DockerSandboxConfig,
    workspace: Path,
    *,
    container_name: str | None = None,
) -> list[str]:
    """Return a command with fixed isolation flags and no host shell expansion."""

    mount = f"type=bind,source={workspace.resolve()},target=/workspace,readonly"
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--ipc",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--pids-limit",
        str(config.pids_limit),
        "--cpus",
        str(config.cpu_limit),
        "--memory",
        config.memory_limit,
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,noexec,size=64m",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "PYTEST_ADDOPTS=-o cache_dir=/tmp/diffmosaic-pytest-cache",
        "--mount",
        mount,
        "--workdir",
        config.working_directory,
    ]
    if container_name:
        command.extend(["--name", container_name])
    return [*command, config.image, *config.test_command]


def classify_container_completion(
    candidate_id: str | None,
    *,
    exit_code: int | None,
    timed_out: bool,
    duration_seconds: float,
    stdout: str = "",
    stderr: str = "",
) -> ExecutionResult:
    """Classify test outcomes without treating Docker failures as killed mutants."""

    if timed_out:
        outcome = "timeout"
    elif exit_code == 125:
        outcome = "infrastructure_error"
    elif candidate_id is None:
        outcome = "passed" if exit_code == 0 else "failed"
    else:
        outcome = "survived" if exit_code == 0 else "killed"
    return ExecutionResult(
        candidate_id=candidate_id,
        outcome=outcome,
        exit_code=exit_code,
        duration_seconds=duration_seconds,
        stdout_tail=stdout[-4000:],
        stderr_tail=stderr[-4000:],
    )


def safe_extract_git_archive(archive_bytes: bytes, destination: Path) -> None:
    """Extract safe archive content and materialise contained symbolic links.

    Git archives can legitimately contain links used by tests, for example to a
    bundled certificate. Links are never created on the host: an in-root link
    target is copied as a regular file or directory instead. Absolute, missing,
    external, and special entries remain invalid.
    """

    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    try:
        archive = tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:")
    except tarfile.TarError as exc:
        raise MutationExecutionError("Git archive could not be read as a tar file.") from exc

    with archive:
        links: list[tarfile.TarInfo] = []
        for member in archive.getmembers():
            target = (root / member.name).resolve()
            if not target.is_relative_to(root):
                raise MutationExecutionError("Git archive contains an unsafe path.")
            if member.issym():
                links.append(member)
                continue
            if not (member.isfile() or member.isdir()):
                raise MutationExecutionError(
                    f"Git archive contains unsupported non-regular entry: {member.name}"
                )
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            source_file = archive.extractfile(member)
            if source_file is None:
                raise MutationExecutionError(f"Git archive member cannot be read: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with source_file, target.open("wb") as destination_file:
                shutil.copyfileobj(source_file, destination_file)

        for member in links:
            link_target = Path(member.linkname)
            if link_target.is_absolute():
                raise MutationExecutionError("Git archive contains an unsafe symbolic link target.")
            target = (root / member.name).resolve()
            source = (target.parent / link_target).resolve()
            if not source.is_relative_to(root) or not source.exists():
                raise MutationExecutionError("Git archive contains an unsafe symbolic link target.")
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_file():
                shutil.copyfile(source, target)
            elif source.is_dir():
                shutil.copytree(source, target)
            else:
                raise MutationExecutionError("Git archive symbolic link target is unsupported.")


def inspect_local_docker_image(image: str) -> str:
    """Verify Docker and return the local image's digest or immutable image ID."""

    try:
        docker_cli = _docker_cli()
        docker_environment = _docker_environment(docker_cli)
        version = subprocess.run(
            [docker_cli, "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
            stdin=subprocess.DEVNULL,
            env=docker_environment,
        )
    except subprocess.TimeoutExpired as exc:
        raise MutationExecutionError("Docker did not respond within 15 seconds.") from exc

    if version.returncode != 0:
        raise MutationExecutionError(
            "Docker daemon is unavailable: " + (version.stderr.strip() or version.stdout.strip())
        )

    try:
        image_check = subprocess.run(
            [
                docker_cli,
                "image",
                "inspect",
                "--format",
                "{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}",
                image,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
            stdin=subprocess.DEVNULL,
            env=docker_environment,
        )
    except subprocess.TimeoutExpired as exc:
        raise MutationExecutionError("Docker image inspection exceeded 15 seconds.") from exc
    if image_check.returncode != 0:
        raise MutationExecutionError(
            "Docker image is not available locally. Pull or build a trusted image first: " + image
        )
    image_identity = image_check.stdout.strip()
    if not image_identity:
        raise MutationExecutionError("Docker did not return an image digest or image ID.")
    return image_identity


def _resolve_git_commit(repo: Path, revision: str) -> str:
    """Resolve a revision to the exact commit used in the experiment record."""

    completed = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", f"{revision}^{{commit}}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        stdin=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        raise MutationExecutionError(
            f"Could not resolve {revision} to a commit: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def _read_git_archive(repo: Path, revision: str, max_archive_bytes: int) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", revision],
        capture_output=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise MutationExecutionError(f"Could not archive {revision}: {detail}")
    if len(completed.stdout) > max_archive_bytes:
        raise MutationExecutionError(
            f"Git archive exceeds the configured {max_archive_bytes} byte safety limit."
        )
    return completed.stdout


def _as_text(output: str | bytes | None) -> str:
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output or ""


def _remove_timed_out_container(container_name: str) -> str:
    """Best-effort cleanup, limited to the random name created for this run."""

    try:
        docker_cli = _docker_cli()
        docker_environment = _docker_environment(docker_cli)
        completed = subprocess.run(
            [docker_cli, "rm", "--force", container_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
            stdin=subprocess.DEVNULL,
            env=docker_environment,
        )
    except (MutationExecutionError, subprocess.TimeoutExpired):
        return "DiffMosaic could not confirm cleanup of the timed-out container."
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        return "DiffMosaic could not confirm cleanup of the timed-out container: " + detail
    return ""


def _run_in_fresh_workspace(
    archive_bytes: bytes,
    candidate: MutationCandidate | None,
    config: DockerSandboxConfig,
) -> ExecutionResult:
    candidate_id = candidate.site.identifier if candidate else None
    container_name = f"diffmosaic-{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory(prefix="diffmosaic-mutation-") as temporary:
        workspace = Path(temporary) / "workspace"
        safe_extract_git_archive(archive_bytes, workspace)
        if candidate is not None:
            target = (workspace / candidate.site.path).resolve()
            if not target.is_relative_to(workspace.resolve()) or not target.is_file():
                raise MutationExecutionError(
                    f"Mutation target is missing from the archived revision: {candidate.site.path}"
                )
            target.write_text(candidate.mutated_source, encoding="utf-8")

        command = build_docker_command(config, workspace, container_name=container_name)
        docker_cli = _docker_cli()
        command[0] = docker_cli
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=config.timeout_seconds + 15,
                check=False,
                stdin=subprocess.DEVNULL,
                env=_docker_environment(docker_cli),
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - started
            cleanup_note = _remove_timed_out_container(container_name)
            return classify_container_completion(
                candidate_id,
                exit_code=None,
                timed_out=True,
                duration_seconds=duration,
                stdout=_as_text(exc.stdout),
                stderr=_as_text(exc.stderr) + cleanup_note,
            )

        return classify_container_completion(
            candidate_id,
            exit_code=completed.returncode,
            timed_out=False,
            duration_seconds=time.monotonic() - started,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def run_mutation_plan(
    repo: Path,
    plan: MutationPlan,
    config: DockerSandboxConfig,
    *,
    expected_image_identity: str | None = None,
) -> MutationExecutionReport:
    """Run a baseline then each candidate against an immutable archived revision."""

    image_identity = inspect_local_docker_image(config.image)
    if expected_image_identity is not None and image_identity != expected_image_identity:
        raise MutationExecutionError(
            "Docker image identity does not match the frozen study subject: "
            f"expected {expected_image_identity}, found {image_identity}."
        )
    base_commit = _resolve_git_commit(repo, plan.base_revision)
    head_commit = _resolve_git_commit(repo, plan.head_revision)
    archive_bytes = _read_git_archive(repo, head_commit, config.max_archive_bytes)
    baseline = _run_in_fresh_workspace(archive_bytes, None, config)
    report = MutationExecutionReport(
        base_revision=base_commit,
        head_revision=head_commit,
        image=config.image,
        test_command=config.test_command,
        working_directory=config.working_directory,
        image_identity=image_identity,
        baseline=baseline,
        planned_candidates=list(plan.candidates),
        notes=list(plan.notes),
        operator_set_version=plan.operator_set_version,
        timeout_seconds=config.timeout_seconds,
        memory_limit=config.memory_limit,
        cpu_limit=config.cpu_limit,
        pids_limit=config.pids_limit,
    )
    if baseline.outcome != "passed":
        report.notes.append("Baseline did not pass; mutation candidates were not executed.")
        return report

    for candidate in plan.candidates:
        report.candidates.append(_run_in_fresh_workspace(archive_bytes, candidate, config))
    return report
