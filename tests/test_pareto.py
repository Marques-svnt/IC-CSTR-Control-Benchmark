"""Unit tests for src/evaluation/pareto.py.

Tests cover:
- Pareto dominance detection (is_dominated)
- Front filtering with and without Ms constraint
- Normalization and scalarized objective
- Knee point detection
- Summarize function with degenerate / empty inputs
"""

import math

import pytest

from src.evaluation.pareto import (
    ParetoPoint,
    filter_pareto_front,
    find_knee_point,
    is_dominated,
    normalize_objectives,
    scalarized_objective,
    summarize_pareto_front,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def three_point_front() -> list[ParetoPoint]:
    """Simple 3-point non-dominated front: A dominates nothing; none dominate each other."""
    return [
        ParetoPoint(iae=1.0, tv=100.0, ms=1.2, label="A"),  # best IAE
        ParetoPoint(iae=2.0, tv=50.0, ms=1.3, label="B"),   # balanced
        ParetoPoint(iae=3.0, tv=20.0, ms=1.4, label="C"),   # best TV
    ]


@pytest.fixture()
def dominated_set() -> list[ParetoPoint]:
    """Set with one clearly dominated point (D is worse than B in both objectives)."""
    return [
        ParetoPoint(iae=1.0, tv=100.0, ms=1.2, label="A"),
        ParetoPoint(iae=2.0, tv=50.0, ms=1.3, label="B"),
        ParetoPoint(iae=3.0, tv=20.0, ms=1.4, label="C"),
        ParetoPoint(iae=2.5, tv=60.0, ms=1.5, label="D"),  # dominated by B
    ]


@pytest.fixture()
def infeasible_set(three_point_front: list[ParetoPoint]) -> list[ParetoPoint]:
    """Set with one Ms-infeasible point added."""
    return three_point_front + [
        ParetoPoint(iae=0.5, tv=10.0, ms=2.5, label="Unstable"),  # violates Ms <= 1.6
    ]


# ---------------------------------------------------------------------------
# is_dominated
# ---------------------------------------------------------------------------


class TestIsDominated:
    def test_dominated_point_detected(self, dominated_set: list[ParetoPoint]) -> None:
        """D (iae=2.5, tv=60) is dominated by B (iae=2.0, tv=50)."""
        d = next(p for p in dominated_set if p.label == "D")
        assert is_dominated(d, dominated_set) is True

    def test_pareto_optimal_not_dominated(self, three_point_front: list[ParetoPoint]) -> None:
        """None of the 3 non-dominated points should be flagged as dominated."""
        for point in three_point_front:
            assert is_dominated(point, three_point_front) is False

    def test_single_point_not_dominated(self) -> None:
        """A single-element set has no comparators — cannot be dominated."""
        p = ParetoPoint(iae=1.0, tv=50.0, ms=1.3)
        assert is_dominated(p, [p]) is False

    def test_equal_objectives_not_dominated(self) -> None:
        """Two identical points do not dominate each other (no strict improvement)."""
        p1 = ParetoPoint(iae=1.0, tv=50.0, ms=1.2, label="p1")
        p2 = ParetoPoint(iae=1.0, tv=50.0, ms=1.3, label="p2")
        assert is_dominated(p1, [p1, p2]) is False
        assert is_dominated(p2, [p1, p2]) is False


# ---------------------------------------------------------------------------
# filter_pareto_front
# ---------------------------------------------------------------------------


class TestFilterParetoFront:
    def test_returns_all_when_none_dominated(self, three_point_front: list[ParetoPoint]) -> None:
        front = filter_pareto_front(three_point_front)
        assert len(front) == 3

    def test_removes_dominated_point(self, dominated_set: list[ParetoPoint]) -> None:
        front = filter_pareto_front(dominated_set)
        labels = {p.label for p in front}
        assert "D" not in labels
        assert {"A", "B", "C"} == labels

    def test_sorted_by_tv_ascending(self, three_point_front: list[ParetoPoint]) -> None:
        front = filter_pareto_front(three_point_front)
        tv_values = [p.tv for p in front]
        assert tv_values == sorted(tv_values)

    def test_ms_constraint_excludes_infeasible(self, infeasible_set: list[ParetoPoint]) -> None:
        front = filter_pareto_front(infeasible_set, ms_threshold=1.6)
        assert all(p.ms <= 1.6 for p in front)
        labels = {p.label for p in front}
        assert "Unstable" not in labels

    def test_empty_input_returns_empty(self) -> None:
        assert filter_pareto_front([]) == []

    def test_all_infeasible_returns_empty(self) -> None:
        pts = [ParetoPoint(iae=1.0, tv=10.0, ms=3.0), ParetoPoint(iae=2.0, tv=5.0, ms=2.5)]
        front = filter_pareto_front(pts, ms_threshold=1.6)
        assert front == []


# ---------------------------------------------------------------------------
# normalize_objectives
# ---------------------------------------------------------------------------


class TestNormalizeObjectives:
    def test_normalized_values_in_unit_range(self, three_point_front: list[ParetoPoint]) -> None:
        norms = normalize_objectives(three_point_front)
        for iae_n, tv_n in norms:
            assert 0.0 <= iae_n <= 1.0
            assert 0.0 <= tv_n <= 1.0

    def test_explicit_refs_applied(self) -> None:
        pts = [ParetoPoint(iae=2.0, tv=100.0, ms=1.2)]
        (iae_n, tv_n), = normalize_objectives(pts, iae_ref=4.0, tv_ref=200.0)
        assert math.isclose(iae_n, 0.5, rel_tol=1e-9)
        assert math.isclose(tv_n, 0.5, rel_tol=1e-9)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            normalize_objectives([])

    def test_zero_ref_raises(self) -> None:
        pts = [ParetoPoint(iae=1.0, tv=10.0, ms=1.2)]
        with pytest.raises(ValueError, match="positive"):
            normalize_objectives(pts, iae_ref=0.0, tv_ref=10.0)


# ---------------------------------------------------------------------------
# scalarized_objective
# ---------------------------------------------------------------------------


class TestScalarizedObjective:
    def test_lam_one_pure_iae(self) -> None:
        """lam=1 → only IAE term contributes."""
        cost = scalarized_objective(iae=2.0, tv=100.0, lam=1.0, iae_ref=4.0, tv_ref=200.0)
        assert math.isclose(cost, 0.5, rel_tol=1e-9)

    def test_lam_zero_pure_tv(self) -> None:
        """lam=0 → only TV term contributes."""
        cost = scalarized_objective(iae=2.0, tv=100.0, lam=0.0, iae_ref=4.0, tv_ref=200.0)
        assert math.isclose(cost, 0.5, rel_tol=1e-9)

    def test_balanced_lam(self) -> None:
        cost = scalarized_objective(iae=2.0, tv=100.0, lam=0.5, iae_ref=4.0, tv_ref=200.0)
        assert math.isclose(cost, 0.5, rel_tol=1e-9)

    def test_invalid_lam_raises(self) -> None:
        with pytest.raises(ValueError, match="lam"):
            scalarized_objective(iae=1.0, tv=10.0, lam=1.5, iae_ref=2.0, tv_ref=20.0)


# ---------------------------------------------------------------------------
# find_knee_point
# ---------------------------------------------------------------------------


class TestFindKneePoint:
    def test_returns_none_for_empty(self) -> None:
        assert find_knee_point([]) is None

    def test_single_point_is_knee(self) -> None:
        p = ParetoPoint(iae=1.0, tv=50.0, ms=1.2)
        assert find_knee_point([p]) is p

    def test_knee_is_balanced_not_extreme(self, three_point_front: list[ParetoPoint]) -> None:
        """On a 3-point front, knee should not be an extreme (best IAE or best TV only)."""
        knee = find_knee_point(three_point_front)
        assert knee is not None
        # Knee is the balanced point B (iae=2.0, tv=50), not A (best IAE) or C (best TV)
        assert knee.label == "B"


# ---------------------------------------------------------------------------
# summarize_pareto_front
# ---------------------------------------------------------------------------


class TestSummarizeParetoFront:
    def test_counts_are_correct(self, dominated_set: list[ParetoPoint]) -> None:
        summary = summarize_pareto_front(dominated_set, ms_threshold=1.6)
        assert summary.n_total == 4
        assert summary.n_pareto == 3
        assert summary.n_dominated == 1
        assert summary.n_infeasible == 0

    def test_iae_tv_bounds(self, three_point_front: list[ParetoPoint]) -> None:
        summary = summarize_pareto_front(three_point_front)
        assert math.isclose(summary.iae_min, 1.0)
        assert math.isclose(summary.iae_max, 3.0)
        assert math.isclose(summary.tv_min, 20.0)
        assert math.isclose(summary.tv_max, 100.0)

    def test_infeasible_counted(self, infeasible_set: list[ParetoPoint]) -> None:
        summary = summarize_pareto_front(infeasible_set, ms_threshold=1.6)
        assert summary.n_infeasible == 1
        assert summary.n_total == 4

    def test_all_infeasible_returns_nan(self) -> None:
        pts = [ParetoPoint(iae=1.0, tv=10.0, ms=3.0)]
        summary = summarize_pareto_front(pts, ms_threshold=1.6)
        assert summary.n_pareto == 0
        assert math.isnan(summary.iae_min)
        assert summary.knee_point is None

    def test_knee_point_present(self, three_point_front: list[ParetoPoint]) -> None:
        summary = summarize_pareto_front(three_point_front)
        assert summary.knee_point is not None
