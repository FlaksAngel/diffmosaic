from diffmosaic.symbols import collect_python_symbols, symbol_for_line


SOURCE = """class Cart:
    def total(self, items):
        return sum(items)

    async def refresh(self):
        return None


def helper():
    return 1
"""


def test_collect_python_symbols_includes_qualified_methods() -> None:
    symbols = collect_python_symbols("cart.py", SOURCE)

    assert [(symbol.qualified_name, symbol.kind) for symbol in symbols] == [
        ("Cart", "class"),
        ("Cart.total", "function"),
        ("Cart.refresh", "async_function"),
        ("helper", "function"),
    ]


def test_symbol_for_line_prefers_innermost_symbol() -> None:
    symbols = collect_python_symbols("cart.py", SOURCE)

    assert symbol_for_line(symbols, 3).qualified_name == "Cart.total"  # type: ignore[union-attr]
    assert symbol_for_line(symbols, 1).qualified_name == "Cart"  # type: ignore[union-attr]
    assert symbol_for_line(symbols, 8) is None
