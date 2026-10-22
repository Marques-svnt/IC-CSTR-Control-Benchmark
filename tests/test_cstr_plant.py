"""Unit and integration tests for CSTR plant model and actuator dynamics."""

import numpy as np
import pytest

from src.sim_core.actuators import ActuatorLimits, ValveActuator
from src.sim_core.cstr_plant import CSTRPlant, CSTRState
from src.sim_core.integrator import NumericalIntegrator


class TestCSTRPlantPhysics:
    """Validates physical and mathematical consistency of the CSTR model."""

    def test_steady_state_residual_is_zero(
        self, plant: CSTRPlant, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        """Confirms that at steady state, all state derivatives evaluate to zero."""
        ss, q_j_ss = nominal_steady_state
        residuals = plant.derivatives(0.0, ss.to_array(), q_j_ss)

        # Numerical residual threshold
        np.testing.assert_allclose(residuals, 0.0, atol=1e-5)

    def test_steady_state_values_are_physical(
        self, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        """Checks that steady-state concentrations and temperatures are strictly physical."""
        ss, _ = nominal_steady_state
        assert 0.0 < ss.C_A <= 1.0  # Consumed reactant fraction
        assert 273.15 < ss.T < 450.0  # Realistic temperature in Kelvin
        assert 273.15 < ss.T_j < ss.T  # Jacket is cooling the reactor

    def test_reaction_rate_monotonicity_and_positivity(self, plant: CSTRPlant) -> None:
        """Ensures reaction rate is non-negative and increases with temperature."""
        c_a = 0.5
        r1 = plant.reaction_rate(c_a, 320.0)
        r2 = plant.reaction_rate(c_a, 350.0)
        r3 = plant.reaction_rate(c_a, 380.0)

        assert r1 > 0.0
        assert r2 > r1
        assert r3 > r2

    def test_linearization_jacobians(
        self, plant: CSTRPlant, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        """Verifies Jacobian shapes and local stability at operating point."""
        ss, q_j_ss = nominal_steady_state
        A, B = plant.linearize(ss, q_j_ss)

        assert A.shape == (3, 3)
        assert B.shape == (3, 1)

        # Eigenvalues of continuous system A
        eigvals = np.linalg.eigvals(A)
        # Check system is Hurwitz (all real parts negative) around nominal point
        assert np.all(np.real(eigvals) < 0.0)

    def test_disturbances_affect_derivatives(self, plant: CSTRPlant) -> None:
        """Overriding feed temperature or concentration must alter state derivatives."""
        nominal_state = np.array([0.08, 345.0, 340.0])
        q_j = 100.0

        deriv_nom = plant.derivatives(0.0, nominal_state, q_j)
        deriv_hot = plant.derivatives(
            0.0, nominal_state, q_j, disturbances={"T_f": plant.params.T_f + 10.0}
        )
        deriv_conc = plant.derivatives(
            0.0, nominal_state, q_j, disturbances={"C_Af": plant.params.C_Af * 1.5}
        )
        deriv_foul = plant.derivatives(
            0.0, nominal_state, q_j, disturbances={"UA": plant.params.UA * 0.7}
        )

        # Hotter feed must increase dT/dt (index 1)
        assert deriv_hot[1] > deriv_nom[1]
        # Higher feed concentration must increase dC_A/dt (index 0)
        assert deriv_conc[0] > deriv_nom[0]
        # Fouling (lower UA) decreases heat removal -> higher net dT/dt
        assert deriv_foul[1] > deriv_nom[1]


class TestNumericalIntegrator:
    """Validates numerical integration accuracy and trajectory generation."""

    def test_steady_state_integration_remains_constant(
        self,
        plant: CSTRPlant,
        integrator: NumericalIntegrator,
        nominal_steady_state: tuple[CSTRState, float],
    ) -> None:
        """Integrating from steady-state with constant input should produce flat trajectory."""
        ss, q_j_ss = nominal_steady_state
        dt = 0.01  # 0.6 seconds
        next_state = integrator.step(plant, ss, q_j=q_j_ss, t_current=0.0, dt=dt)

        np.testing.assert_allclose(next_state.to_array(), ss.to_array(), atol=1e-4)

    def test_open_loop_cooling_step_response(
        self,
        plant: CSTRPlant,
        integrator: NumericalIntegrator,
        nominal_steady_state: tuple[CSTRState, float],
    ) -> None:
        """Increasing coolant flow rate q_j must cool down reactor temperature."""
        ss, q_j_ss = nominal_steady_state
        q_j_step = q_j_ss + 20.0  # +20% coolant flow rate

        res = integrator.simulate_open_loop(
            plant=plant,
            initial_state=ss,
            t_span=(0.0, 5.0),
            dt=0.05,
            u_func=lambda t: q_j_step,
        )

        initial_T = res.states[0, 1]
        final_T = res.states[-1, 1]
        assert final_T < initial_T  # More cooling decreases reactor temperature

    def test_open_loop_with_disturbance_function(
        self,
        plant: CSTRPlant,
        integrator: NumericalIntegrator,
        nominal_steady_state: tuple[CSTRState, float],
    ) -> None:
        """Simulation with feed temperature disturbance heats up reactor compared to nominal."""
        ss, q_j_ss = nominal_steady_state

        res_nom = integrator.simulate_open_loop(
            plant=plant,
            initial_state=ss,
            t_span=(0.0, 3.0),
            dt=0.05,
            u_func=lambda t: q_j_ss,
        )

        res_dist = integrator.simulate_open_loop(
            plant=plant,
            initial_state=ss,
            t_span=(0.0, 3.0),
            dt=0.05,
            u_func=lambda t: q_j_ss,
            disturbance_func=lambda t: {
                "T_f": plant.params.T_f + 5.0 if t >= 1.0 else plant.params.T_f
            },
        )

        # Disturbed trajectory should end with a higher temperature
        assert res_dist.states[-1, 1] > res_nom.states[-1, 1]


class TestValveActuator:
    """Validates actuator physical saturation and slew-rate dynamics."""

    def test_saturation_clamping(self) -> None:
        """Tests that commands beyond [u_min, u_max] trigger saturation flag and are clamped."""
        # Disable slew rate limit (max_slew_rate=0.0) to test pure clamping
        limits = ActuatorLimits(u_min=10.0, u_max=200.0, max_slew_rate=0.0)
        valve = ValveActuator(limits=limits, initial_position=50.0)

        # Underflow command
        u_out, is_sat = valve.apply(u_desired=-5.0, dt=0.1)
        assert u_out == 10.0
        assert is_sat is True

        # Overflow command
        u_out, is_sat = valve.apply(u_desired=350.0, dt=0.1)
        assert u_out == 200.0
        assert is_sat is True

    def test_slew_rate_limiting(self) -> None:
        """Tests rate-of-change limitation per unit time."""
        limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=50.0)
        valve = ValveActuator(limits=limits, initial_position=100.0)

        # With dt = 0.1 min, maximum allowed jump is 50.0 * 0.1 = 5.0
        u_out, is_sat = valve.apply(u_desired=150.0, dt=0.1)
        assert u_out == pytest.approx(105.0)
        assert is_sat is True
