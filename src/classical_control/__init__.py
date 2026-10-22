"""Classical PID control algorithms, anti-windup architectures, and tuning methods."""

from src.classical_control.closed_loop import ClosedLoopResult, ClosedLoopSimulator
from src.classical_control.foptd import FOPTDModel, identify_foptd
from src.classical_control.pid_controller import AntiWindupMethod, PIDController, PIDGains
from src.classical_control.tuning_analytical import TuningRule, tune_analytical
from src.classical_control.tuning_optimization import (
    OptimizationCriterion,
    calculate_maximum_sensitivity,
    calculate_maximum_sensitivity_foptd,
    tune_by_optimization,
)

__all__ = [
    "PIDController",
    "PIDGains",
    "AntiWindupMethod",
    "ClosedLoopSimulator",
    "ClosedLoopResult",
    "FOPTDModel",
    "identify_foptd",
    "TuningRule",
    "tune_analytical",
    "OptimizationCriterion",
    "calculate_maximum_sensitivity",
    "calculate_maximum_sensitivity_foptd",
    "tune_by_optimization",
]
