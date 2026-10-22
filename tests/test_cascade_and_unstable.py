"""Tests for the ChERD campaign: open-loop unstable saddle and dynamic jacket fouling."""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from experiments import exp_06_unstable_saddle_and_fouling as exp06
from src.sim_core.cstr_plant import CSTRPlant


@pytest.fixture(scope="module")
def saddle() -> exp06.OperatingPoint:
    return exp06.find_saddle_point()


@pytest.fixture(scope="module")
def saddle_design(saddle: exp06.OperatingPoint) -> exp06.ControllerDesign:
    return exp06.design_controllers(saddle, tau_c_siso=exp06.TAU_C_SISO_SADDLE)


def test_saddle_is_an_equilibrium_with_one_unstable_direction(
    saddle: exp06.OperatingPoint,
) -> None:
    plant, ss, q_j = saddle.plant, saddle.ss, saddle.q_j
    assert ss.T == pytest.approx(exp06.T_SADDLE, abs=1e-6)
    np.testing.assert_allclose(plant.derivatives(0.0, ss.to_array(), q_j), 0.0, atol=1e-8)
    eig = np.linalg.eigvals(plant.linearize(ss, q_j)[0])
    assert np.sum(eig.real > 0.0) == 1
    assert 0.0 < q_j < exp06.LIMITS.u_max


def test_nominal_feed_has_no_unstable_steady_state() -> None:
    """With T_f = 350 K the heat balance has a single, stable root at q_j = 100 L/min."""
    branches = exp06.steady_state_branches(CSTRPlant(), q_j=100.0)
    assert len(branches) == 1
    assert branches[0][1] < 0.0


def test_open_loop_trajectory_leaves_the_saddle(saddle: exp06.OperatingPoint) -> None:
    df = exp06.simulate(saddle, None, arch="open_loop", t_end=15.0, x0_offset_T=0.5)
    assert abs(df["T"].iloc[-1] - saddle.ss.T) > 5.0


def test_simc_bound_is_necessary_for_unstable_model() -> None:
    with pytest.raises(ValueError):
        exp06.simc_unstable_pi(k=-0.5, tau_u=1.0, theta=0.4, tau_c=0.7)


@pytest.mark.parametrize("arch", ["siso", "cascade", "cascade_ff"])
def test_closed_loop_stabilizes_the_saddle(
    saddle: exp06.OperatingPoint, saddle_design: exp06.ControllerDesign, arch: str
) -> None:
    loop = "siso" if arch == "siso" else "cascade"
    abscissa = exp06.closed_loop_abscissa(saddle, saddle_design, loop)
    assert abscissa < 0.0
    df = exp06.simulate(saddle, saddle_design, arch=arch, t_end=40.0, x0_offset_T=0.5)
    assert np.max(np.abs(df["T"] - saddle.ss.T)) < 2.0
    assert abs(df["T"].iloc[-1] - saddle.ss.T) < 0.05


@settings(max_examples=8, deadline=None)
@given(
    kappa=st.floats(min_value=0.05, max_value=2.0),
    ua_min_frac=st.floats(min_value=0.1, max_value=0.9),
)
def test_fouling_solver_is_monotone_and_bounded(kappa: float, ua_min_frac: float) -> None:
    """d(UA)/dt = -kappa r_A (UA - UA_min) never increases UA nor crosses UA_min."""
    nominal = exp06.nominal_point()
    df = exp06.simulate(
        nominal, None, arch="open_loop", t_end=3.0, kappa=kappa, ua_min_frac=ua_min_frac
    )
    ua = df["UA"].to_numpy()
    ua_min = ua_min_frac * nominal.plant.params.UA
    assert np.all(np.diff(ua) <= 1e-9)
    assert np.all(ua >= ua_min - 1e-6)
    assert ua[-1] < ua[0]
    assert np.all(np.isfinite(df[["C_A", "T", "T_j"]].to_numpy()))


def test_fouling_saturation_time_matches_quasi_steady_prediction() -> None:
    """At the stable nominal point T is regulated, r_A stays constant and UA(t) has a closed
    form: the valve must reach u_max close to the time at which UA crosses UA_crit."""
    nominal = exp06.nominal_point()
    design = exp06.design_controllers(nominal)
    t_pred = exp06.predicted_saturation_time(nominal, exp06.KAPPA_FOUL, exp06.UA_MIN_FRAC)
    df = exp06.simulate(
        nominal, design, arch="cascade", t_end=t_pred + 10.0,
        kappa=exp06.KAPPA_FOUL, ua_min_frac=exp06.UA_MIN_FRAC,
    )
    t_sat = exp06.first_time(df, df["q_j"] >= exp06.LIMITS.u_max - 1e-6)
    assert t_sat == pytest.approx(t_pred, rel=0.05)


@pytest.mark.parametrize("arch", ["siso", "cascade"])
def test_fixed_gain_loop_loses_the_saddle_before_the_thermodynamic_limit(
    saddle: exp06.OperatingPoint, saddle_design: exp06.ControllerDesign, arch: str
) -> None:
    """Fouling shrinks the actuator gain (T_jf - T_j)/V_j: the fixed-gain loop loses
    stability at a UA well above UA_crit, and the fouling run ignites before t_pred."""
    f_crit = exp06.critical_ua_fraction(saddle)
    f_stab = exp06.stability_boundary(saddle_design, arch, f_crit + 0.01)
    assert f_crit < f_stab < 1.0
    t_pred = exp06.predicted_saturation_time(saddle, exp06.KAPPA_FOUL, exp06.UA_MIN_FRAC)
    df = exp06.simulate(
        saddle, saddle_design, arch=arch, t_end=t_pred,
        kappa=exp06.KAPPA_FOUL, ua_min_frac=exp06.UA_MIN_FRAC,
    )
    t_run = exp06.first_time(df, df["T"] - saddle.ss.T > exp06.RUNAWAY_BAND)
    assert t_run < t_pred
