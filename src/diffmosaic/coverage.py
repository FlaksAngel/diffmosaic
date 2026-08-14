"""Read coverage.py JSON artefacts without executing a target project."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CoverageDataError(ValueError):
    """Raised when a coverage JSON artefact is missing or malformed."""


def _normalise_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


@dataclass(frozen=True)
class CoverageMatch:
    """Coverage lines resolved for one repository-relative source path."""

    status: str
    executed_lines: frozenset[int] = frozenset()
    matched_path: str | None = None


@dataclass(frozen=True)
class CoverageData:
    """The minimal, stable portion of a coverage.py JSON report we use."""

    executed_lines_by_path: dict[str, frozenset[int]]

    def match(self, source_path: str) -> CoverageMatch:
        """Resolve a repository-relative path while refusing ambiguous suffixes."""

        expected = _normalise_path(source_path)
        direct = self.executed_lines_by_path.get(expected)
        if direct is not None:
            return CoverageMatch("available", direct, expected)

        candidates = [
            path
            for path in self.executed_lines_by_path
            if path.endswith(f"/{expected}")
        ]
        if len(candidates) == 1:
            matched_path = candidates[0]
            return CoverageMatch(
                "available",
                self.executed_lines_by_path[matched_path],
                matched_path,
            )
        if len(candidates) > 1:
            return CoverageMatch("ambiguous")
        return CoverageMatch("missing")


def _read_executed_lines(path: str, raw_file_data: Any) -> frozenset[int]:
    if not isinstance(raw_file_data, dict):
        raise CoverageDataError(f"Coverage entry for {path!r} must be an object.")
    raw_lines = raw_file_data.get("executed_lines")
    if not isinstance(raw_lines, list) or not all(
        isinstance(line, int) and line >= 0 for line in raw_lines
    ):
        raise CoverageDataError(
            f"Coverage entry for {path!r} must contain a list of non-negative integer executed_lines."
        )
    return frozenset(raw_lines)


def load_coverage_json(path: Path) -> CoverageData:
    """Load a previously generated coverage.py JSON report.

    This function only reads data. Running a test command belongs to a future
    isolated execution component and is intentionally outside this module.
    """

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CoverageDataError(f"Coverage JSON does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CoverageDataError(f"Coverage JSON is not valid JSON: {path}") from exc

    if not isinstance(raw, dict) or not isinstance(raw.get("files"), dict):
        raise CoverageDataError("Coverage JSON must contain a top-level 'files' object.")

    return CoverageData(
        {
            _normalise_path(str(file_path)): _read_executed_lines(str(file_path), file_data)
            for file_path, file_data in raw["files"].items()
        }
    )
