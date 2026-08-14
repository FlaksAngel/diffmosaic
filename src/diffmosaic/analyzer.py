"""Combine diff metadata and AST locations into an explainable analysis report."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from diffmosaic.coverage import CoverageData, load_coverage_json
from diffmosaic.diff import GitReadError, parse_unified_diff, read_diff, read_file_at_revision
from diffmosaic.models import (
    AnalysisReport,
    ChangedSymbol,
    FileDelta,
    PythonSymbol,
    UnmappedChange,
)
from diffmosaic.symbols import SourceParseError, collect_python_symbols, symbol_for_line

SourceLoader = Callable[[str], str]


def is_test_path(path: str) -> bool:
    """Use conservative pytest-style path heuristics without inspecting source."""

    normalised = path.replace("\\", "/").lower()
    pieces = normalised.split("/")
    filename = pieces[-1]
    return (
        "tests" in pieces
        or "test" in pieces
        or filename.startswith("test_")
        or filename.endswith("_test.py")
    )


def _is_production_python(delta: FileDelta) -> bool:
    return bool(
        delta.new_path
        and delta.new_path.endswith(".py")
        and not is_test_path(delta.new_path)
    )


def analyse_deltas(
    deltas: list[FileDelta],
    source_loader: SourceLoader,
    *,
    base_revision: str,
    head_revision: str,
    coverage_data: CoverageData | None = None,
) -> AnalysisReport:
    """Analyse parsed deltas with a supplied head-source loader.

    This pure-ish boundary keeps the core analyser easy to test and allows a
    future dataset runner to provide files from an archive rather than Git.
    """

    test_files = sorted(
        delta.display_path
        for delta in deltas
        if is_test_path(delta.display_path)
    )
    mapped: dict[PythonSymbol, set[int]] = defaultdict(set)
    unmapped: list[UnmappedChange] = []
    notes: list[str] = []

    for delta in deltas:
        if not _is_production_python(delta):
            continue

        assert delta.new_path is not None
        if not delta.changed_new_lines:
            notes.append(
                f"{delta.display_path}: deletion-only change; no head-revision lines to map."
            )
            continue

        try:
            source = source_loader(delta.new_path)
            symbols = collect_python_symbols(delta.new_path, source)
        except (GitReadError, SourceParseError) as exc:
            notes.append(str(exc))
            for line in delta.changed_new_lines:
                unmapped.append(
                    UnmappedChange(delta.display_path, line, "source_unavailable_or_invalid")
                )
            continue

        for line in delta.changed_new_lines:
            symbol = symbol_for_line(symbols, line)
            if symbol is None:
                unmapped.append(
                    UnmappedChange(delta.display_path, line, "outside_named_python_symbol")
                )
            else:
                mapped[symbol].add(line)

    changed_symbols: list[ChangedSymbol] = []
    for symbol, lines in mapped.items():
        changed_lines = tuple(sorted(lines))
        coverage_status = "not_provided"
        executed_changed_lines: tuple[int, ...] = ()
        if coverage_data is not None:
            match = coverage_data.match(symbol.path)
            coverage_status = match.status
            executed_changed_lines = tuple(
                line for line in changed_lines if line in match.executed_lines
            )
            if match.status == "ambiguous":
                notes.append(
                    f"{symbol.path}: coverage path matching was ambiguous; no evidence used."
                )
        changed_symbols.append(
            ChangedSymbol(
                symbol=symbol,
                changed_lines=changed_lines,
                coverage_status=coverage_status,
                executed_changed_lines=executed_changed_lines,
            )
        )
    changed_symbols.sort(
        key=lambda item: (
            item.symbol.path,
            item.symbol.start_line,
            item.symbol.qualified_name,
        )
    )
    unmapped.sort(key=lambda item: (item.path, item.line, item.reason))

    return AnalysisReport(
        base_revision=base_revision,
        head_revision=head_revision,
        changed_files=deltas,
        changed_test_files=test_files,
        changed_symbols=changed_symbols,
        unmapped_changes=unmapped,
        notes=notes,
    )


def analyse_repository(
    repo: Path,
    base_revision: str,
    head_revision: str,
    coverage_json: Path | None = None,
) -> AnalysisReport:
    """Analyse two revisions of a local repository without changing it."""

    diff_text = read_diff(repo, base_revision, head_revision)
    deltas = parse_unified_diff(diff_text)
    coverage_data = load_coverage_json(coverage_json) if coverage_json else None
    return analyse_deltas(
        deltas,
        lambda path: read_file_at_revision(repo, head_revision, path),
        base_revision=base_revision,
        head_revision=head_revision,
        coverage_data=coverage_data,
    )
