"""Unit tests for NMPC closed-loop simulation integration."""

import numpy as np

from src.classical_control.closed_loop import ClosedLoopSimulator
from src.controllers.optimal.nmpc_controller import CstrNmpcController
from src.sim_core.cstr_plant import CSTRPlant
from src.sim_core.integrator import NumericalIntegrator


def test_nmpc_closed_loop_simulation() -> None:
    """Verifies that CstrNmpcController integrates with ClosedLoopSimulator."""
    plant = CSTRPlant()
    integrator = NumericalIntegrator(method="RK45")
    sim = ClosedLoopSimulator(integrator=integrator)
    ss = plant.find_steady_state(q_j=100.0)

    target_t = ss.T - 2.0
    nmpc = CstrNmpcController(horizon_steps=5, t_step_min=0.05, setpoint_temperature_k=target_t)

    res = sim.run(
        plant=plant,
        controller=nmpc,
        initial_state=ss,
        t_span=(0.0, 0.5),
        dt=0.05,
        setpoint_func=lambda t: target_t,
    )

    assert res.metrics.iae > 0.0
    assert np.all(np.isfinite(res.t_pv))
    assert np.all(res.u_applied >= 0.0)
    assert np.all(res.u_applied <= 300.0)


def test_nmpc_reset_behavior() -> None:
    """Verifies that reset properly reinitializes internal controller states."""
    controller = CstrNmpcController(horizon_steps=5, t_step_min=0.1)
    controller.reset(initial_measurement=340.0, initial_u=120.0)

    assert controller.u_bias == 120.0
    assert controller.supports_full_state is True
