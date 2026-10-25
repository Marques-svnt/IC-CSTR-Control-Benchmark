"""Second test plant (v9, C1): heat exchanger with a well-mixed shell and a two-cell tube."""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.sim_core.heat_exchanger import HeatExchanger


@pytest.fixture(scope="module")
def hx() -> HeatExchanger:
    return HeatExchanger()


def test_nominal_steady_state_and_stability(hx: HeatExchanger) -> None:
    """Values stated in the round-9 brief: T2 ~ 355.9 K, three real negative eigenvalues."""
    x = hx.steady_state(100.0)
    assert np.allclose(hx.derivatives(x, 100.0), 0.0, atol=1e-9)
    assert x[1] == pytest.approx(355.9, abs=0.05)
    eig = np.sort(np.linalg.eigvals(hx.jacobian(x, 100.0)).real)
    assert eig == pytest.approx([-6.29, -3.96, -1.66], abs=0.01)


def test_full_cooling_is_below_the_step_setpoints(hx: HeatExchanger) -> None:
    """At the upper valve stop T2 ~ 331.3 K, below 355.9 - 5 K: the latch of Prop. 1 is possible."""
    assert hx.steady_state(300.0)[1] == pytest.approx(331.3, abs=0.05)


@settings(max_examples=20, deadline=None)
@given(q=st.floats(min_value=10.0, max_value=290.0))
def test_reverse_acting_static_gain(q: float) -> None:
    """More coolant always lowers the outlet temperature (negative static gain)."""
    hx = HeatExchanger()
    assert hx.steady_state(q + 1.0)[1] < hx.steady_state(q)[1]


def test_rk4_step_holds_the_equilibrium(hx: HeatExchanger) -> None:
    """One sample at constant input leaves a steady state unchanged."""
    x = hx.steady_state(150.0)
    assert np.allclose(hx.step(x, 150.0, 0.02), x, atol=1e-9)
