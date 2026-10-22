"""Unit tests for Neuro-PID adaptive controller."""

import numpy as np

from src.classical_control.closed_loop import ClosedLoopSimulator
from src.classical_control.pid_controller import PIDGains
from src.controllers.neural.neuro_pid_controller import NeuroPidController
from src.sim_core.cstr_plant import CSTRPlant
from src.sim_core.integrator import NumericalIntegrator


def test_neuro_pid_gain_bounds_and_step() -> None:
    """Verifies that NeuroPidController modulates gains within strict bounds."""
    base_gains = PIDGains(kp=-30.0, ti=0.45, td=0.03, n_filter=10.0)
    controller = NeuroPidController(
        base_gains=base_gains,
        adaptation_scale=0.30,
        u_bias=100.0,
    )

    u, diag = controller.compute(
        setpoint=342.16,
        measurement=344.16,
        dt=0.05,
        full_state=np.array([0.1345, 344.16, 330.43]),
    )

    assert isinstance(u, float)
    assert 0.0 <= u <= 300.0
    # Gain bounds: base_kp * (1 +/- scale) -> -30.0 * [0.7, 1.3] = [-39.0, -21.0]
    assert -40.0 <= controller.current_kp <= -20.0
    assert "adaptive_kp" in diag
    assert "adaptive_ti" in diag
    assert "adaptive_td" in diag


def test_neuro_pid_closed_loop_simulation() -> None:
    """Tests full closed loop trajectory with NeuroPidController and CSTRPlant."""
    plant = CSTRPlant()
    integrator = NumericalIntegrator(method="RK45")
    sim = ClosedLoopSimulator(integrator=integrator)
    ss = plant.find_steady_state(q_j=100.0)

    base_gains = PIDGains(kp=-35.0, ti=0.40, td=0.02, n_filter=10.0)
    controller = NeuroPidController(
        base_gains=base_gains,
        adaptation_scale=0.25,
        u_bias=100.0,
    )

    target_t = ss.T - 2.0
    res = sim.run(
        plant=plant,
        controller=controller,
        initial_state=ss,
        t_span=(0.0, 1.0),
        dt=0.05,
        setpoint_func=lambda t: target_t,
    )

    assert res.metrics.iae > 0.0
    assert np.all(np.isfinite(res.t_pv))
    assert np.all(res.u_applied >= 0.0)
    assert np.all(res.u_applied <= 300.0)
