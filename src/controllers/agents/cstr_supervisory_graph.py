"""Multi-Agent Supervisory Workflow for CSTR Thermal Safety via LangGraph.

Implements autonomous supervision of chemical plant operations, auditing
the Van Heerden thermal runaway criterion, classifying dynamical regimes,
and dynamically orchestrating classical, neural, and optimal controllers.
"""

from __future__ import annotations

import logging
from typing import Literal, TypedDict

import numpy as np
from langgraph.graph import END, StateGraph

from src.sim_core.cstr_plant import CSTRParameters

logger = logging.getLogger(__name__)

RegimeType = Literal["nominal", "transient", "critical_runaway"]
ControllerPolicy = Literal["pid_simc", "neuro_pid", "nmpc_optimal", "emergency_cooling"]


class CstrSupervisorState(TypedDict):
    """Operational state dictionary circulating across the supervisory graph."""

    time: float
    setpoint: float
    temperature: float
    c_a: float
    t_j: float
    heat_generation_slope: float
    heat_removal_slope: float
    stability_margin: float
    regime: RegimeType
    recommended_controller: ControllerPolicy
    control_action: float
    audit_message: str


def audit_van_heerden_criterion(state: CstrSupervisorState) -> dict[str, float | str]:
    """Computes Van Heerden thermal stability slopes using Arrhenius kinetics.

    Stability Condition:
        dQ_rem/dT > dQ_gen/dT => Stable operation
        dQ_rem/dT <= dQ_gen/dT => Unstable saddle / thermal runaway risk

    Args:
        state: Instantaneous process monitoring state.

    Returns:
        Dictionary with generation slope, removal slope, margin, and audit message.
    """
    p = CSTRParameters()
    T = max(100.0, float(state["temperature"]))
    C_A = max(0.0, float(state["c_a"]))

    # Arrhenius reaction rate
    k = p.k_0 * np.exp(-p.E_over_R / T)

    # Derivative of heat generation with respect to temperature: dQ_gen / dT
    # Q_gen = (-delta_H) * V * k * C_A
    # dQ_gen/dT = (-delta_H) * V * k * C_A * (E_over_R / T^2)
    dQ_gen_dT = (-p.delta_H) * p.V * k * C_A * (p.E_over_R / (T**2))

    # Derivative of heat removal with respect to temperature: dQ_rem / dT
    # Q_rem = q * rho_cp * (T - T_f) + UA * (T - T_j)
    # dQ_rem/dT = q * rho_cp + UA
    dQ_rem_dT = p.q * p.rho_cp + p.UA

    stability_margin = float(dQ_rem_dT - dQ_gen_dT)

    if stability_margin > 1000.0:
        msg = f"Stable: robust margin (+{stability_margin:.1f} cal/(min*K))"
    elif stability_margin > 0.0:
        msg = f"Marginal: positive slope approaching limit (+{stability_margin:.1f})"
    else:
        msg = f"CRITICAL: thermal runaway violation (margin={stability_margin:.1f})"

    logger.debug("Van Heerden audit at T=%.2f K: margin=%.1f", T, stability_margin)
    return {
        "heat_generation_slope": float(dQ_gen_dT),
        "heat_removal_slope": float(dQ_rem_dT),
        "stability_margin": stability_margin,
        "audit_message": msg,
    }


def classify_operating_regime(state: CstrSupervisorState) -> dict[str, RegimeType]:
    """Classifies plant regime into nominal, transient, or runaway hazard.

    Args:
        state: State including Van Heerden stability margin and tracking error.

    Returns:
        Dictionary containing updated 'regime'.
    """
    margin = state["stability_margin"]
    error = abs(state["setpoint"] - state["temperature"])

    if margin <= 0.0 or state["temperature"] > 410.0:
        regime: RegimeType = "critical_runaway"
    elif error > 3.0 or margin < 5000.0:
        regime: RegimeType = "transient"
    else:
        regime: RegimeType = "nominal"

    logger.debug("Operating regime classified as: %s (error=%.2f K)", regime, error)
    return {"regime": regime}


def arbitrate_control_policy(state: CstrSupervisorState) -> dict[str, ControllerPolicy | float]:
    """Arbitrates optimal control authority based on safety regime with bumpless handoff.

    Decision Matrix:
        - critical_runaway -> emergency_cooling (flow = 300.0 L/min)
        - transient -> nmpc_optimal / neuro_pid (with DPC Van Heerden barrier)
        - nominal -> pid_simc (low CPU, high actuator life)

    Args:
        state: Classified supervisory state.

    Returns:
        Dictionary with recommended_controller and control_action override.
    """
    regime = state["regime"]
    prev_action = float(state.get("control_action", 100.0))

    if regime == "critical_runaway":
        policy: ControllerPolicy = "emergency_cooling"
        action = 300.0  # Maximum cooling valve opening
    elif regime == "transient":
        policy: ControllerPolicy = "nmpc_optimal"
        # Smooth bumpless transition from previous control action toward transient target
        target_action = 120.0
        action = float(0.2 * prev_action + 0.8 * target_action) if prev_action != 100.0 else 120.0
    else:
        policy: ControllerPolicy = "pid_simc"
        action = 100.0  # Nominal baseline

    logger.info("Supervisor policy: %s (action=%.1f L/min) under regime=%s", policy, action, regime)
    return {
        "recommended_controller": policy,
        "control_action": action,
    }


def build_cstr_supervisory_graph() -> StateGraph:
    """Builds and compiles the multi-agent supervisory state graph.

    Graph topology:
        [START] -> audit_van_heerden -> classify_regime -> arbitrate_policy -> [END]

    Returns:
        Compiled runnable LangGraph workflow.
    """
    builder = StateGraph(CstrSupervisorState)

    builder.add_node("audit_van_heerden", audit_van_heerden_criterion)
    builder.add_node("classify_regime", classify_operating_regime)
    builder.add_node("arbitrate_policy", arbitrate_control_policy)

    builder.set_entry_point("audit_van_heerden")
    builder.add_edge("audit_van_heerden", "classify_regime")
    builder.add_edge("classify_regime", "arbitrate_policy")
    builder.add_edge("arbitrate_policy", END)

    compiled_graph = builder.compile()
    logger.info("LangGraph CSTR Supervisory Graph successfully compiled")
    return compiled_graph
