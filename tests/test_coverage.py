import json
from pathlib import Path

import pytest

from diffmosaic.coverage import CoverageDataError, load_coverage_json


FIXTURES = Path(__file__).parent / "fixtures"


def test_load_coverage_json_matches_direct_and_absolute_paths() -> None:
    coverage = load_coverage_json(FIXTURES / "coverage.json")

    direct = coverage.match("catalog.py")
    absolute = coverage.match("nested/catalog.py")

    assert direct.status == "available"
    assert direct.executed_lines == frozenset({1, 4, 5, 7, 10, 13})
    assert absolute.status == "missing"


def test_coverage_path_suffix_match_and_ambiguity(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(
        json.dumps(
            {
                "files": {
                    "C:/work/project/src/pricing.py": {"executed_lines": [4]},
                    "D:/another/src/pricing.py": {"executed_lines": [7]},
                }
            }
        ),
        encoding="utf-8",
    )
    coverage = load_coverage_json(report)

    assert coverage.match("src/pricing.py").status == "ambiguous"
    assert coverage.match("project/src/pricing.py").status == "available"


def test_load_coverage_json_rejects_missing_executed_lines(tmp_path: Path) -> None:
    report = tmp_path / "broken.json"
    report.write_text('{"files": {"pricing.py": {}}}', encoding="utf-8")

    with pytest.raises(CoverageDataError, match="executed_lines"):
        load_coverage_json(report)


def test_load_coverage_json_accepts_a_file_with_no_executed_lines(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(
        json.dumps({"files": {"tests/not_collected.py": {"executed_lines": []}}}),
        encoding="utf-8",
    )

    coverage = load_coverage_json(report)

    assert coverage.match("tests/not_collected.py").executed_lines == frozenset()


def test_load_coverage_json_accepts_coverage_pys_empty_file_sentinel(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(
        json.dumps({"files": {"tests/__init__.py": {"executed_lines": [0]}}}),
        encoding="utf-8",
    )

    coverage = load_coverage_json(report)

    assert coverage.match("tests/__init__.py").executed_lines == frozenset({0})
