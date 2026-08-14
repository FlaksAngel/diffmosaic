from pathlib import Path

from diffmosaic.analyzer import analyse_deltas, is_test_path
from diffmosaic.coverage import load_coverage_json
from diffmosaic.diff import parse_unified_diff


FIXTURES = Path(__file__).parent / "fixtures"


def test_is_test_path_recognises_common_pytest_locations() -> None:
    assert is_test_path("tests/test_catalog.py")
    assert is_test_path("src/catalog_test.py")
    assert is_test_path("test_utils.py")
    assert not is_test_path("src/catalog.py")


def test_analyse_deltas_maps_changed_lines_to_python_symbol() -> None:
    deltas = parse_unified_diff((FIXTURES / "catalog.diff").read_text(encoding="utf-8"))
    source = (FIXTURES / "catalog.py").read_text(encoding="utf-8")

    report = analyse_deltas(
        deltas,
        lambda path: source if path == "catalog.py" else "",
        base_revision="base",
        head_revision="head",
    )

    assert report.changed_test_files == ["tests/test_catalog.py"]
    assert len(report.changed_symbols) == 1
    symbol = report.changed_symbols[0]
    assert symbol.symbol.qualified_name == "calculate_total"
    assert symbol.changed_lines == (5, 6)
    assert [(item.path, item.line) for item in report.unmapped_changes] == [
        ("catalog.py", 10),
    ]


def test_analyse_deltas_attaches_coverage_evidence() -> None:
    deltas = parse_unified_diff((FIXTURES / "catalog.diff").read_text(encoding="utf-8"))
    source = (FIXTURES / "catalog.py").read_text(encoding="utf-8")

    report = analyse_deltas(
        deltas,
        lambda path: source if path == "catalog.py" else "",
        base_revision="base",
        head_revision="head",
        coverage_data=load_coverage_json(FIXTURES / "coverage.json"),
    )

    symbol = report.changed_symbols[0]
    assert symbol.coverage_status == "available"
    assert symbol.executed_changed_lines == (5,)
