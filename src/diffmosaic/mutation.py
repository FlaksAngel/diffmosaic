"""Plan small, diff-local Python mutations without executing target code.

DiffMosaic uses mutation testing as behavioural evidence, not as a claim that a
surviving mutant proves a bug. This module deliberately stops at planning and
source generation. The separately isolated runner consumes these candidates
only after an explicit command-line acknowledgement.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass, field

from diffmosaic.analyzer import is_test_path
from diffmosaic.diff import GitReadError, parse_unified_diff, read_diff, read_file_at_revision
from diffmosaic.models import FileDelta
from diffmosaic.symbols import SourceParseError, collect_python_symbols, symbol_for_line

SourceLoader = Callable[[str], str]

_COMPARISON_REPLACEMENTS: dict[type[ast.cmpop], tuple[type[ast.cmpop], str, str]] = {
    ast.Eq: (ast.NotEq, "==", "!="),
    ast.NotEq: (ast.Eq, "!=", "=="),
    ast.Lt: (ast.LtE, "<", "<="),
    ast.LtE: (ast.Lt, "<=", "<"),
    ast.Gt: (ast.GtE, ">", ">="),
    ast.GtE: (ast.Gt, ">=", ">"),
    ast.Is: (ast.IsNot, "is", "is not"),
    ast.IsNot: (ast.Is, "is not", "is"),
    ast.In: (ast.NotIn, "in", "not in"),
    ast.NotIn: (ast.In, "not in", "in"),
}

_BOOLEAN_REPLACEMENTS: dict[type[ast.boolop], tuple[type[ast.boolop], str, str]] = {
    ast.And: (ast.Or, "and", "or"),
    ast.Or: (ast.And, "or", "and"),
}

_BINARY_REPLACEMENTS: dict[type[ast.operator], tuple[type[ast.operator], str, str]] = {
    ast.Add: (ast.Sub, "+", "-"),
    ast.Sub: (ast.Add, "-", "+"),
}

_OPERATOR_SET_COMPARISONS: dict[str, frozenset[type[ast.cmpop]]] = {
    "v0.1": frozenset({ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE}),
    "v0.2": frozenset(_COMPARISON_REPLACEMENTS),
}
_OPERATOR_SET_BINARY: dict[str, frozenset[type[ast.operator]]] = {
    "v0.1": frozenset(),
    "v0.2": frozenset(_BINARY_REPLACEMENTS),
}
_SUPPORTED_OPERATOR_SETS = tuple(_OPERATOR_SET_COMPARISONS)


def available_operator_sets() -> tuple[str, ...]:
    """Return supported, versioned mutation-operator set identifiers."""

    return _SUPPORTED_OPERATOR_SETS


def _require_operator_set(operator_set: str) -> None:
    if operator_set not in _SUPPORTED_OPERATOR_SETS:
        choices = ", ".join(_SUPPORTED_OPERATOR_SETS)
        raise ValueError(f"operator_set must be one of: {choices}.")


@dataclass(frozen=True)
class MutationSite:
    """A single mutation operator located in changed source lines."""

    path: str
    kind: str
    line: int
    column: int
    end_line: int
    end_column: int
    original_operator: str
    replacement_operator: str
    expression: str
    symbol: str | None

    @property
    def identifier(self) -> str:
        return (
            f"{self.path}:{self.line}:{self.column}:"
            f"{self.kind}:{self.original_operator}-to-{self.replacement_operator}"
        )

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "id": self.identifier,
            "path": self.path,
            "kind": self.kind,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "original_operator": self.original_operator,
            "replacement_operator": self.replacement_operator,
            "expression": self.expression,
            "symbol": self.symbol,
        }


@dataclass(frozen=True)
class MutationCandidate:
    """A mutation site and its syntactically validated source candidate."""

    site: MutationSite
    mutated_source: str


@dataclass
class MutationPlan:
    """A deterministic set of candidates that is safe to inspect or archive."""

    base_revision: str
    head_revision: str
    candidates: list[MutationCandidate] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    operator_set_version: str = "v0.1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "0.1",
            "base_revision": self.base_revision,
            "head_revision": self.head_revision,
            "operator_set_version": self.operator_set_version,
            "candidate_count": len(self.candidates),
            "candidates": [candidate.site.to_dict() for candidate in self.candidates],
            "notes": self.notes,
        }


def _overlaps_changed_lines(node: ast.AST, changed_lines: set[int]) -> bool:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", start)
    return start is not None and end is not None and any(
        start <= line <= end for line in changed_lines
    )


def _node_coordinates(node: ast.AST) -> tuple[int, int, int, int]:
    line = getattr(node, "lineno", 0)
    column = getattr(node, "col_offset", 0)
    end_line = getattr(node, "end_lineno", line)
    end_column = getattr(node, "end_col_offset", column)
    return line, column, end_line, end_column


class _SiteCollector(ast.NodeVisitor):
    def __init__(
        self,
        path: str,
        source: str,
        changed_lines: set[int],
        operator_set: str,
    ) -> None:
        self.path = path
        self.source = source
        self.changed_lines = changed_lines
        self.operator_set = operator_set
        self.sites: list[MutationSite] = []
        self.symbols = collect_python_symbols(path, source)

    def _symbol_name(self, node: ast.AST) -> str | None:
        line, _, _, _ = _node_coordinates(node)
        symbol = symbol_for_line(self.symbols, line)
        return symbol.qualified_name if symbol else None

    def _add_site(
        self,
        node: ast.AST,
        *,
        kind: str,
        original_operator: str,
        replacement_operator: str,
    ) -> None:
        line, column, end_line, end_column = _node_coordinates(node)
        expression = ast.get_source_segment(self.source, node) or ast.unparse(node)
        self.sites.append(
            MutationSite(
                path=self.path,
                kind=kind,
                line=line,
                column=column,
                end_line=end_line,
                end_column=end_column,
                original_operator=original_operator,
                replacement_operator=replacement_operator,
                expression=expression,
                symbol=self._symbol_name(node),
            )
        )

    def visit_Compare(self, node: ast.Compare) -> None:  # noqa: N802
        if (
            len(node.ops) == 1
            and _overlaps_changed_lines(node, self.changed_lines)
            and type(node.ops[0]) in _OPERATOR_SET_COMPARISONS[self.operator_set]
        ):
            _, original, replacement = _COMPARISON_REPLACEMENTS[type(node.ops[0])]
            self._add_site(
                node,
                kind="comparison_operator",
                original_operator=original,
                replacement_operator=replacement,
            )
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:  # noqa: N802
        if (
            _overlaps_changed_lines(node, self.changed_lines)
            and type(node.op) in _BOOLEAN_REPLACEMENTS
        ):
            _, original, replacement = _BOOLEAN_REPLACEMENTS[type(node.op)]
            self._add_site(
                node,
                kind="boolean_operator",
                original_operator=original,
                replacement_operator=replacement,
            )
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:  # noqa: N802
        if (
            _overlaps_changed_lines(node, self.changed_lines)
            and type(node.op) in _OPERATOR_SET_BINARY[self.operator_set]
        ):
            _, original, replacement = _BINARY_REPLACEMENTS[type(node.op)]
            self._add_site(
                node,
                kind="binary_operator",
                original_operator=original,
                replacement_operator=replacement,
            )
        self.generic_visit(node)


def collect_mutation_sites(
    path: str,
    source: str,
    changed_lines: set[int],
    *,
    operator_set: str = "v0.1",
) -> list[MutationSite]:
    """Find supported mutation sites whose AST span overlaps a changed line."""

    _require_operator_set(operator_set)

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        raise SourceParseError(f"Could not parse {path}: {exc.msg} (line {exc.lineno})") from exc

    collector = _SiteCollector(path, source, changed_lines, operator_set)
    collector.visit(tree)
    return sorted(
        collector.sites,
        key=lambda site: (site.path, site.line, site.column, site.kind, site.replacement_operator),
    )


def _same_site(node: ast.AST, site: MutationSite) -> bool:
    line, column, end_line, end_column = _node_coordinates(node)
    return (line, column, end_line, end_column) == (
        site.line,
        site.column,
        site.end_line,
        site.end_column,
    )


class _SingleMutationTransformer(ast.NodeTransformer):
    def __init__(self, site: MutationSite) -> None:
        self.site = site
        self.changed = False

    def visit_Compare(self, node: ast.Compare) -> ast.AST:  # noqa: N802
        self.generic_visit(node)
        if (
            not self.changed
            and self.site.kind == "comparison_operator"
            and _same_site(node, self.site)
            and len(node.ops) == 1
            and type(node.ops[0]) in _COMPARISON_REPLACEMENTS
        ):
            replacement, original, _ = _COMPARISON_REPLACEMENTS[type(node.ops[0])]
            if original == self.site.original_operator:
                node.ops[0] = replacement()
                self.changed = True
        return node

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:  # noqa: N802
        self.generic_visit(node)
        if (
            not self.changed
            and self.site.kind == "boolean_operator"
            and _same_site(node, self.site)
            and type(node.op) in _BOOLEAN_REPLACEMENTS
        ):
            replacement, original, _ = _BOOLEAN_REPLACEMENTS[type(node.op)]
            if original == self.site.original_operator:
                node.op = replacement()
                self.changed = True
        return node

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:  # noqa: N802
        self.generic_visit(node)
        if (
            not self.changed
            and self.site.kind == "binary_operator"
            and _same_site(node, self.site)
            and type(node.op) in _BINARY_REPLACEMENTS
        ):
            replacement, original, _ = _BINARY_REPLACEMENTS[type(node.op)]
            if original == self.site.original_operator:
                node.op = replacement()
                self.changed = True
        return node


def build_mutation_candidate(source: str, site: MutationSite) -> MutationCandidate:
    """Create one syntactically valid source candidate without writing a file."""

    tree = ast.parse(source, filename=site.path)
    transformer = _SingleMutationTransformer(site)
    mutated_tree = transformer.visit(tree)
    ast.fix_missing_locations(mutated_tree)
    if not transformer.changed:
        raise ValueError(f"Could not apply mutation site {site.identifier}.")

    mutated_source = ast.unparse(mutated_tree) + "\n"
    compile(mutated_source, site.path, "exec")
    return MutationCandidate(site=site, mutated_source=mutated_source)


def plan_mutations_from_deltas(
    deltas: list[FileDelta],
    source_loader: SourceLoader,
    *,
    base_revision: str,
    head_revision: str,
    max_candidates: int = 20,
    operator_set: str = "v0.1",
) -> MutationPlan:
    """Build a bounded, deterministic mutation plan for changed Python code."""

    if max_candidates < 1:
        raise ValueError("max_candidates must be at least 1.")
    _require_operator_set(operator_set)

    candidates: list[MutationCandidate] = []
    notes: list[str] = []
    for delta in deltas:
        if (
            not delta.new_path
            or not delta.new_path.endswith(".py")
            or is_test_path(delta.new_path)
            or not delta.changed_new_lines
        ):
            continue

        try:
            source = source_loader(delta.new_path)
            sites = collect_mutation_sites(
                delta.new_path,
                source,
                set(delta.changed_new_lines),
                operator_set=operator_set,
            )
        except (GitReadError, SourceParseError) as exc:
            notes.append(str(exc))
            continue

        for site in sites:
            if len(candidates) >= max_candidates:
                notes.append(f"Candidate limit ({max_candidates}) reached.")
                return MutationPlan(
                    base_revision,
                    head_revision,
                    candidates,
                    notes,
                    operator_set,
                )
            candidates.append(build_mutation_candidate(source, site))

    return MutationPlan(base_revision, head_revision, candidates, notes, operator_set)


def plan_repository_mutations(
    repo_path: str,
    base_revision: str,
    head_revision: str,
    *,
    max_candidates: int = 20,
    operator_set: str = "v0.1",
) -> MutationPlan:
    """Create a mutation plan from two local Git revisions without execution."""

    from pathlib import Path

    repo = Path(repo_path)
    deltas = parse_unified_diff(read_diff(repo, base_revision, head_revision))
    return plan_mutations_from_deltas(
        deltas,
        lambda path: read_file_at_revision(repo, head_revision, path),
        base_revision=base_revision,
        head_revision=head_revision,
        max_candidates=max_candidates,
        operator_set=operator_set,
    )
