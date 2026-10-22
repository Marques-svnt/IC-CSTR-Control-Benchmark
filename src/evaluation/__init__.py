"""Evaluation metrics and multi-objective analysis for control system benchmarking."""

from src.evaluation.metrics import ControlPerformanceMetrics, evaluate_performance
from src.evaluation.pareto import (
    ParetoFrontierSummary,
    ParetoPoint,
    filter_pareto_front,
    find_knee_point,
    normalize_objectives,
    scalarized_objective,
    summarize_pareto_front,
)

__all__ = [
    # metrics
    "ControlPerformanceMetrics",
    "evaluate_performance",
    # pareto
    "ParetoPoint",
    "ParetoFrontierSummary",
    "filter_pareto_front",
    "find_knee_point",
    "normalize_objectives",
    "scalarized_objective",
    "summarize_pareto_front",
]
