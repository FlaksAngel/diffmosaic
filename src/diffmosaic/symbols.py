"""Map changed source lines to Python symbols using the standard-library AST."""

from __future__ import annotations

import ast

from diffmosaic.models import PythonSymbol


class SourceParseError(ValueError):
    """Raised when the head revision cannot be parsed as Python source."""


class _SymbolCollector(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.scope: list[str] = []
        self.symbols: list[PythonSymbol] = []

    def _add_and_visit(self, node: ast.AST, name: str, kind: str) -> None:
        start_line = getattr(node, "lineno", None)
        end_line = getattr(node, "end_lineno", None)
        if start_line is not None and end_line is not None:
            qualified_name = ".".join([*self.scope, name])
            self.symbols.append(
                PythonSymbol(
                    path=self.path,
                    qualified_name=qualified_name,
                    kind=kind,
                    start_line=start_line,
                    end_line=end_line,
                )
            )
        self.scope.append(name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._add_and_visit(node, node.name, "class")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._add_and_visit(node, node.name, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._add_and_visit(node, node.name, "async_function")


def collect_python_symbols(path: str, source: str) -> list[PythonSymbol]:
    """Collect named Python symbols with exact source spans."""

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        raise SourceParseError(f"Could not parse {path}: {exc.msg} (line {exc.lineno})") from exc

    collector = _SymbolCollector(path)
    collector.visit(tree)
    return sorted(
        collector.symbols,
        key=lambda symbol: (symbol.start_line, symbol.end_line, symbol.qualified_name),
    )


def symbol_for_line(symbols: list[PythonSymbol], line: int) -> PythonSymbol | None:
    """Return the most specific symbol containing a one-based source line."""

    candidates = [symbol for symbol in symbols if symbol.contains(line)]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda symbol: (symbol.end_line - symbol.start_line, symbol.start_line),
    )
