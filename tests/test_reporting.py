from pathlib import Path

from diffmosaic.analyzer import analyse_deltas
from diffmosaic.diff import parse_unified_diff
from diffmosaic.reporting import render_json, render_markdown


FIXTURES = Path(__file__).parent / "fixtures"


def _report():
    deltas = parse_unified_diff((FIXTURES / "catalog.diff").read_text(encoding="utf-8"))
    source = (FIXTURES / "catalog.py").read_text(encoding="utf-8")
    return analyse_deltas(
        deltas,
        lambda path: source if path == "catalog.py" else "",
        base_revision="base",
        head_revision="head",
    )


def test_json_report_contains_revisions_and_symbol() -> None:
    rendered = render_json(_report())

    assert '"base_revision": "base"' in rendered
    assert '"qualified_name": "calculate_total"' in rendered


def test_markdown_report_explains_mapped_and_unmapped_changes() -> None:
    rendered = render_markdown(_report())

    assert "`catalog.py::calculate_total`" in rendered
    assert "`catalog.py:10` — outside_named_python_symbol" in rendered
    assert "Coverage evidence: not_provided" in rendered
