from pathlib import Path

from diffmosaic.analyzer import analyse_deltas
from diffmosaic.diff import parse_unified_diff
from diffmosaic.models import AnalysisReport, ChangedSymbol, PythonSymbol
from diffmosaic.priority import prioritise_report
from diffmosaic.reporting import render_priority_markdown


FIXTURES = Path(__file__).parent / "fixtures"


def test_missing_coverage_is_a_low_priority_evidence_gap_when_tests_changed() -> None:
    deltas = parse_unified_diff((FIXTURES / "catalog.diff").read_text(encoding="utf-8"))
    source = (FIXTURES / "catalog.py").read_text(encoding="utf-8")
    analysis = analyse_deltas(
        deltas,
        lambda path: source if path == "catalog.py" else "",
        base_revision="base",
        head_revision="head",
    )

    report = prioritise_report(analysis)

    assert report.items[0].level == "low"
    assert report.items[0].score == 1
    assert [reason.code for reason in report.items[0].reasons] == ["coverage_evidence_unavailable"]
    assert "not a defect prediction" in render_priority_markdown(report)


def test_no_test_file_and_no_executed_changed_line_raise_review_priority() -> None:
    symbol = PythonSymbol("logic.py", "guard", "function", 1, 5)
    analysis = AnalysisReport(
        base_revision="base",
        head_revision="head",
        changed_files=[],
        changed_test_files=[],
        changed_symbols=[
            ChangedSymbol(
                symbol=symbol,
                changed_lines=(2, 3),
                coverage_status="available",
                executed_changed_lines=(),
            )
        ],
        unmapped_changes=[],
    )

    report = prioritise_report(analysis)

    assert report.baseline_no_test_file_changed is True
    assert report.items[0].level == "high"
    assert report.items[0].score == 5
    assert {reason.code for reason in report.items[0].reasons} == {
        "no_changed_line_executed",
        "no_changed_test_file",
    }
