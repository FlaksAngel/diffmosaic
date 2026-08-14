"""Small, serialisable domain models used by DiffMosaic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Hunk:
    """A single unified diff hunk.

    Line numbers use the source file's one-based coordinate system. A count of
    zero is valid for pure insertions or deletions.
    """

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    added_new_lines: list[int] = field(default_factory=list)
    removed_old_lines: list[int] = field(default_factory=list)

    @property
    def new_lines(self) -> tuple[int, ...]:
        """Return only added lines, excluding unchanged diff context."""

        return tuple(self.added_new_lines)


@dataclass
class FileDelta:
    """Changed paths and hunks for one file in a unified diff."""

    old_path: str | None
    new_path: str | None
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def display_path(self) -> str:
        return self.new_path or self.old_path or "<unknown>"

    @property
    def changed_new_lines(self) -> tuple[int, ...]:
        return tuple(
            line
            for hunk in self.hunks
            for line in hunk.new_lines
        )

    @property
    def changed_old_lines(self) -> int:
        return sum(len(hunk.removed_old_lines) for hunk in self.hunks)

    @property
    def changed_new_line_count(self) -> int:
        return sum(len(hunk.added_new_lines) for hunk in self.hunks)


@dataclass(frozen=True)
class PythonSymbol:
    """A function, async function, class, or method found by the Python AST."""

    path: str
    qualified_name: str
    kind: str
    start_line: int
    end_line: int

    def contains(self, line: int) -> bool:
        return self.start_line <= line <= self.end_line


@dataclass(frozen=True)
class ChangedSymbol:
    """A Python symbol touched by one or more changed new lines."""

    symbol: PythonSymbol
    changed_lines: tuple[int, ...]
    coverage_status: str = "not_provided"
    executed_changed_lines: tuple[int, ...] = ()


@dataclass(frozen=True)
class UnmappedChange:
    """A changed source line which could not be mapped to a Python symbol."""

    path: str
    line: int
    reason: str


@dataclass
class AnalysisReport:
    """Raw, explainable output of the version 0.1 analysis pipeline."""

    base_revision: str
    head_revision: str
    changed_files: list[FileDelta]
    changed_test_files: list[str]
    changed_symbols: list[ChangedSymbol]
    unmapped_changes: list[UnmappedChange]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "0.1",
            "base_revision": self.base_revision,
            "head_revision": self.head_revision,
            "summary": {
                "changed_files": len(self.changed_files),
                "changed_test_files": len(self.changed_test_files),
                "changed_production_symbols": len(self.changed_symbols),
                "unmapped_changed_lines": len(self.unmapped_changes),
            },
            "changed_files": [
                {
                    "old_path": delta.old_path,
                    "new_path": delta.new_path,
                    "changed_new_lines": list(delta.changed_new_lines),
                    "changed_old_line_count": delta.changed_old_lines,
                }
                for delta in self.changed_files
            ],
            "changed_test_files": self.changed_test_files,
            "changed_symbols": [
                {
                    "path": item.symbol.path,
                    "qualified_name": item.symbol.qualified_name,
                    "kind": item.symbol.kind,
                    "start_line": item.symbol.start_line,
                    "end_line": item.symbol.end_line,
                    "changed_lines": list(item.changed_lines),
                    "coverage": {
                        "status": item.coverage_status,
                        "executed_changed_lines": list(item.executed_changed_lines),
                    },
                }
                for item in self.changed_symbols
            ],
            "unmapped_changes": [
                {"path": item.path, "line": item.line, "reason": item.reason}
                for item in self.unmapped_changes
            ],
            "notes": self.notes,
        }
