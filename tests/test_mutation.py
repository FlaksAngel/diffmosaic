from pathlib import Path

import pytest

from diffmosaic.diff import parse_unified_diff
from diffmosaic.mutation import (
    build_mutation_candidate,
    collect_mutation_sites,
    plan_mutations_from_deltas,
)


SOURCE = """def validate_discount(discount, subtotal):
    if discount > subtotal and subtotal != 0:
        raise ValueError("invalid discount")
    return subtotal - discount


def unchanged(value):
    return value == 0
"""


def test_collect_mutation_sites_limits_candidates_to_changed_expression() -> None:
    sites = collect_mutation_sites("pricing.py", SOURCE, {2})

    assert [(site.kind, site.original_operator, site.replacement_operator) for site in sites] == [
        ("boolean_operator", "and", "or"),
        ("comparison_operator", ">", ">="),
        ("comparison_operator", "!=", "=="),
    ]
    assert all(site.symbol == "validate_discount" for site in sites)


def test_mutation_candidate_is_syntactically_valid_and_changes_one_operator() -> None:
    site = next(
        site
        for site in collect_mutation_sites("pricing.py", SOURCE, {2})
        if site.original_operator == ">"
    )

    candidate = build_mutation_candidate(SOURCE, site)

    assert "discount >= subtotal" in candidate.mutated_source
    assert "subtotal != 0" in candidate.mutated_source
    compile(candidate.mutated_source, "pricing.py", "exec")


def test_unchanged_expression_does_not_create_mutation_site() -> None:
    sites = collect_mutation_sites("pricing.py", SOURCE, {5})

    assert sites == []


def test_plan_mutations_from_deltas_respects_candidate_limit() -> None:
    diff = """diff --git a/pricing.py b/pricing.py
index 1111111..2222222 100644
--- a/pricing.py
+++ b/pricing.py
@@ -1,0 +2 @@
+    if discount > subtotal and subtotal != 0:
"""
    deltas = parse_unified_diff(diff)

    plan = plan_mutations_from_deltas(
        deltas,
        lambda path: SOURCE,
        base_revision="base",
        head_revision="head",
        max_candidates=2,
    )

    assert len(plan.candidates) == 2
    assert plan.notes == ["Candidate limit (2) reached."]


def test_plan_mutations_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        plan_mutations_from_deltas(
            [],
            lambda path: SOURCE,
            base_revision="base",
            head_revision="head",
            max_candidates=0,
        )
