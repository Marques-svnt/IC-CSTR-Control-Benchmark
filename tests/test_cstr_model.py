"""ChERD IC-T25/T26: fouling mechanism, b_3 at UA_crit, margins and the reduced-model bound."""

import numpy as np
import pytest

from experiments import exp_06_unstable_saddle_and_fouling as exp06
from src.classical_control.pid_controller import PIDGains


@pytest.fixture(scope="module")
def saddle() -> exp06.OperatingPoint:
    return exp06.find_saddle_point()


@pytest.fixture(scope="module")
def design(saddle: exp06.OperatingPoint) -> exp06.ControllerDesign:
    return exp06.design_controllers(saddle, tau_c_siso=exp06.TAU_C_SISO_SADDLE)


def test_jacket_gain_at_critical_ua(saddle: exp06.OperatingPoint) -> None:
    """T_j = T - Q_load/UA_crit = 305.35 K, b_3 = (T_jf - T_j)/V_j = -0.267 K/L: a factor 5.4."""
    t_j, b3, f_crit = exp06.jacket_gain_at_critical(saddle)
    b3_nominal = float(saddle.plant.linearize(saddle.ss, saddle.q_j)[1][2, 0])
    assert t_j == pytest.approx(305.35, abs=0.01)
    assert b3 == pytest.approx((300.0 - t_j) / saddle.plant.params.V_j, rel=1e-12)
    assert b3 == pytest.approx(-0.267, abs=5e-4)
    assert b3_nominal / b3 == pytest.approx(5.4, abs=0.05)
    assert f_crit == pytest.approx(exp06.critical_ua_fraction(saddle))


@pytest.mark.parametrize("arch", ["siso", "cascade"])
def test_instability_is_a_hopf_crossing_not_static_gain_loss(
    design: exp06.ControllerDesign, saddle: exp06.OperatingPoint, arch: str
) -> None:
    """At the frozen-UA boundary a complex pair sits on the imaginary axis while K_c k > 1."""
    f_crit = exp06.critical_ua_fraction(saddle)
    f_b = exp06.stability_boundary(design, arch, f_crit + 0.01)
    op_b = exp06.find_saddle_point(ua_frac=f_b)
    eig = exp06.closed_loop_eigenvalues(op_b, design, arch)
    lead = eig[np.argmax(eig.real)]
    assert abs(lead.real) < 1e-6
    assert abs(lead.imag) > 0.1
    assert np.any(np.isclose(eig, lead.conjugate()))
    mech = exp06.fouling_mechanism(design, np.array([f_b]))
    assert mech["Kc_k_siso"].iloc[0] > 1.0  # static P-only threshold is still satisfied
    expected = {"siso": 1.57, "cascade": 1.49}[arch]
    assert mech["Kc_k_siso"].iloc[0] == pytest.approx(expected, abs=0.01)


def test_loop_margins_match_analytic_gain_margin() -> None:
    """L = 3/(s+1)^3 has phase -180 deg at w = sqrt(3) with |L| = 3/8, so GM = 8/3."""
    s = 1j * exp06.OMEGAS
    m = exp06.loop_margins(3.0 / (s + 1.0) ** 3)
    assert m["gm_up"] == pytest.approx(8.0 / 3.0, rel=1e-3)
    assert np.isnan(m["gm_down"])
    assert 0.0 < m["pm_deg"] < 90.0


def test_reduced_model_sensitivity_respects_the_delay_bound(
    design: exp06.ControllerDesign, saddle: exp06.OperatingPoint
) -> None:
    """||S||_inf >= exp(p theta) for k e^{-theta s}/(tau_u s - 1) under any stabilizing PI."""
    k, tau_u, theta = exp06.unstable_model(saddle)
    bound = exp06.ms_lower_bound(1.0 / tau_u, theta)
    assert bound == pytest.approx(1.62, abs=0.005)
    assert exp06.reduced_model_ms(k, tau_u, theta, design.siso) >= bound


def test_ms_constrained_siso_pi_exists_on_the_full_model(saddle: exp06.OperatingPoint) -> None:
    """The third-order loop (delay DT/2 only) admits M_s <= 1.6, unlike the reduced model."""
    gains = PIDGains(kp=-16.0, ti=8.0)
    zeros = exp06.FOPTDModel(1, 1, 0)
    d = exp06.ControllerDesign(gains, gains, gains, (0, 0, 0), zeros, zeros, siso_opt=gains)
    assert exp06.closed_loop_abscissa(saddle, d, "siso_opt") < 0.0
    assert exp06.loop_margins(exp06.siso_loop(saddle, gains))["Ms"] < exp06.MS_MAX


def test_scheduled_slave_gain_equals_nominal_at_the_design_point(
    design: exp06.ControllerDesign, saddle: exp06.OperatingPoint
) -> None:
    assert exp06.scheduled_slave(saddle, design).kp == pytest.approx(design.slave.kp)
    fouled = exp06.find_saddle_point(ua_frac=0.6)
    ratio = (design.tj_ref - 300.0) / (fouled.ss.T_j - 300.0)
    assert exp06.scheduled_slave(fouled, design).kp == pytest.approx(design.slave.kp * ratio)
    assert ratio > 1.0  # fouling lowers T_j, so the schedule raises the gain
