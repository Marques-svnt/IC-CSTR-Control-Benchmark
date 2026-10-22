"""Pytest configuration and shared fixtures for CSTR simulation testing."""

import pytest

from src.sim_core.actuators import ActuatorLimits, ValveActuator
from src.sim_core.cstr_plant import CSTRParameters, CSTRPlant, CSTRState
from src.sim_core.integrator import NumericalIntegrator


@pytest.fixture
def default_params() -> CSTRParameters:
    """Provides standard literature CSTR benchmark parameters."""
    return CSTRParameters()


@pytest.fixture
def plant(default_params: CSTRParameters) -> CSTRPlant:
    """Instantiates standard benchmark CSTR plant."""
    return CSTRPlant(params=default_params)


@pytest.fixture
def nominal_steady_state(plant: CSTRPlant) -> tuple[CSTRState, float]:
    """Calculates nominal steady state at q_j = 100.0 L/min."""
    q_j_ss = 100.0
    ss = plant.find_steady_state(q_j=q_j_ss)
    return ss, q_j_ss


@pytest.fixture
def integrator() -> NumericalIntegrator:
    """Provides default numerical integrator instance."""
    return NumericalIntegrator(method="RK45")


@pytest.fixture
def default_valve() -> ValveActuator:
    """Provides valve actuator with standard physical limits."""
    limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=100.0)
    return ValveActuator(limits=limits, initial_position=100.0)
