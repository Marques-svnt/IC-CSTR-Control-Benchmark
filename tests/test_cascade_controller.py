"""Testes unitários para o controlador em cascata do reator CSTR."""

import pytest

from src.classical_control.cascade_controller import CascadePIDController, CascadePIDGains
from src.classical_control.pid_controller import PIDGains
from src.sim_core.actuators import ActuatorLimits


@pytest.fixture
def cascade_controller() -> CascadePIDController:
    """Fixture fornecendo instância sintonizada do controlador em cascata."""
    master_gains = PIDGains(kp=2.5, ti=1.2, td=0.1, n_filter=10.0)
    slave_gains = PIDGains(kp=-5.0, ti=0.3, td=0.0)
    gains = CascadePIDGains(
        master_gains=master_gains,
        slave_gains=slave_gains,
        t_j_min=300.0,
        t_j_max=380.0,
    )
    limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)
    return CascadePIDController(
        gains=gains,
        actuator_limits=limits,
        u_bias=100.0,
        t_j_bias=348.33,
    )


def test_cascade_nominal_equilibrium(cascade_controller: CascadePIDController) -> None:
    """Verifica se o controlador mantém saída nominal em equilíbrio estático."""
    t_sp = 396.65
    t_pv = 396.65
    tj_pv = 348.33
    dt = 0.02

    q_j, diag = cascade_controller.compute(t_sp=t_sp, t_pv=t_pv, tj_pv=tj_pv, dt=dt)
    assert pytest.approx(q_j, abs=1e-1) == 100.0
    assert pytest.approx(diag["tj_sp"], abs=1e-1) == 348.33


def test_cascade_cooling_response(cascade_controller: CascadePIDController) -> None:
    """Verifica se uma elevação de temperatura provoca aumento no fluxo de refrigerante."""
    t_sp = 396.65
    t_pv = 400.0  # Reator muito quente
    tj_pv = 348.33
    dt = 0.02

    q_j, diag = cascade_controller.compute(t_sp=t_sp, t_pv=t_pv, tj_pv=tj_pv, dt=dt)
    # Reator quente -> T_j,sp deve cair
    assert diag["tj_sp"] < 348.33
    # Com T_j,sp menor que T_j atual, válvula deve abrir (q_j > 100.0)
    assert q_j > 100.0


def test_cascade_actuator_limits(cascade_controller: CascadePIDController) -> None:
    """Verifica se a saída respeita estritamente a saturação da válvula."""
    t_sp = 350.0  # Demanda extrema de resfriamento
    t_pv = 450.0
    tj_pv = 400.0
    dt = 10.0

    q_j, _ = cascade_controller.compute(t_sp=t_sp, t_pv=t_pv, tj_pv=tj_pv, dt=dt)
    assert q_j <= 300.0
    assert q_j >= 0.0
