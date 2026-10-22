"""Unit tests for LangGraph CSTR supervisory workflow."""

from src.controllers.agents.cstr_supervisory_graph import (
    CstrSupervisorState,
    build_cstr_supervisory_graph,
)


def test_supervisory_graph_nominal_regime() -> None:
    """Verifies that supervisor detects stable nominal regime and selects SIMC."""
    graph = build_cstr_supervisory_graph()

    initial_state: CstrSupervisorState = {
        "time": 0.0,
        "setpoint": 344.16,
        "temperature": 344.16,
        "c_a": 0.1345,
        "t_j": 330.43,
        "heat_generation_slope": 0.0,
        "heat_removal_slope": 0.0,
        "stability_margin": 0.0,
        "regime": "nominal",
        "recommended_controller": "pid_simc",
        "control_action": 100.0,
        "audit_message": "",
    }

    result = graph.invoke(initial_state)

    assert result["regime"] == "nominal"
    assert result["recommended_controller"] == "pid_simc"
    assert result["stability_margin"] > 0.0
    assert "Stable" in result["audit_message"]


def test_supervisory_graph_critical_runaway_emergency() -> None:
    """Verifies that supervisor detects imminent runaway and triggers emergency cooling."""
    graph = build_cstr_supervisory_graph()

    hazard_state: CstrSupervisorState = {
        "time": 1.5,
        "setpoint": 350.0,
        "temperature": 415.0,  # Critical overheating
        "c_a": 0.30,
        "t_j": 380.0,
        "heat_generation_slope": 0.0,
        "heat_removal_slope": 0.0,
        "stability_margin": 0.0,
        "regime": "nominal",
        "recommended_controller": "pid_simc",
        "control_action": 100.0,
        "audit_message": "",
    }

    result = graph.invoke(hazard_state)

    assert result["regime"] == "critical_runaway"
    assert result["recommended_controller"] == "emergency_cooling"
    assert result["control_action"] == 300.0
