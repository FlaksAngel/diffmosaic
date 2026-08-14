"""Read Git diffs without modifying the analysed repository."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from diffmosaic.models import FileDelta, Hunk

_HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)


class GitReadError(RuntimeError):
    """Raised when a read-only Git command cannot be completed."""


def _normalise_path(value: str) -> str | None:
    value = value.strip()
    if value == "/dev/null":
        return None
    if value.startswith("a/") or value.startswith("b/"):
        return value[2:]
    return value


def parse_unified_diff(diff_text: str) -> list[FileDelta]:
    """Parse the file and hunk metadata from a zero- or normal-context diff.

    The parser deliberately does not interpret changed source text. AST parsing
    always uses the exact file content from the head revision instead.
    """

    deltas: list[FileDelta] = []
    current: FileDelta | None = None
    current_hunk: Hunk | None = None
    old_line = 0
    new_line = 0

    def finish_current() -> None:
        nonlocal current
        if current is not None:
            deltas.append(current)
            current = None

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("diff --git "):
            finish_current()
            current_hunk = None
            parts = raw_line.split(maxsplit=3)
            if len(parts) == 4:
                current = FileDelta(
                    old_path=_normalise_path(parts[2]),
                    new_path=_normalise_path(parts[3]),
                )
            continue

        if current is None:
            continue

        if current_hunk is None and raw_line.startswith("--- "):
            current.old_path = _normalise_path(raw_line[4:])
            continue

        if current_hunk is None and raw_line.startswith("+++ "):
            current.new_path = _normalise_path(raw_line[4:])
            continue

        match = _HUNK_RE.match(raw_line)
        if match:
            current_hunk = Hunk(
                old_start=int(match.group("old_start")),
                old_count=int(match.group("old_count") or 1),
                new_start=int(match.group("new_start")),
                new_count=int(match.group("new_count") or 1),
            )
            current.hunks.append(current_hunk)
            old_line = current_hunk.old_start
            new_line = current_hunk.new_start
            continue

        if current_hunk is None or raw_line.startswith("\\ No newline"):
            continue

        if raw_line.startswith("+"):
            current_hunk.added_new_lines.append(new_line)
            new_line += 1
        elif raw_line.startswith("-"):
            current_hunk.removed_old_lines.append(old_line)
            old_line += 1
        elif raw_line.startswith(" "):
            old_line += 1
            new_line += 1

    finish_current()
    return deltas


def _run_git(repo: Path, *args: str) -> str:
    command = ["git", "-C", str(repo), *args]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise GitReadError(f"Git command failed: {' '.join(command)}\n{detail}")
    return completed.stdout


def read_diff(repo: Path, base_revision: str, head_revision: str) -> str:
    """Return a unified diff, using no external diff driver and no writes."""

    return _run_git(
        repo,
        "diff",
        "--no-ext-diff",
        "--unified=0",
        base_revision,
        head_revision,
        "--",
    )


def read_file_at_revision(repo: Path, revision: str, path: str) -> str:
    """Return one UTF-8 source file from a Git revision."""

    return _run_git(repo, "show", f"{revision}:{path}")


def read_first_parent_non_merge_revisions(repo: Path, max_count: int) -> list[tuple[str, str]]:
    """Return newest-first `(commit, parent)` pairs without mutating a repository."""

    if max_count < 1:
        raise ValueError("max_count must be at least 1.")
    raw = _run_git(
        repo,
        "log",
        "--first-parent",
        "--no-merges",
        f"--max-count={max_count}",
        "--format=%H %P",
    )
    revisions: list[tuple[str, str]] = []
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) == 2:
            revisions.append((parts[0], parts[1]))
    return revisions
