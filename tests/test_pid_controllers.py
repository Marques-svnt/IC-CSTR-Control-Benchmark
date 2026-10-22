"""Unit and integration tests for PID controller architectures and anti-windup schemes."""

import pytest

from src.classical_control.closed_loop import ClosedLoopSimulator
from src.classical_control.pid_controller import AntiWindupMethod, PIDController, PIDGains
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRPlant, CSTRState


class TestPIDControllerBasics:
    """Verifies fundamental P, I, D mathematical terms and filter logic."""

    def test_proportional_only_action(self) -> None:
        """With Ti=inf (represented by huge Ti) and Td=0, output is purely Kp * e."""
        gains = PIDGains(kp=2.0, ti=1e9, td=0.0)
        pid = PIDController(gains=gains, u_bias=100.0, anti_windup=AntiWindupMethod.NONE)

        # SP = 360, PV = 355 -> error = 5 -> P = 2.0 * 5 = 10 -> u = 100 + 10 = 110
        u_act, diag = pid.compute(setpoint=360.0, measurement=355.0, dt=0.1)

        assert diag["p"] == pytest.approx(10.0)
        assert diag["d"] == pytest.approx(0.0)
        assert u_act == pytest.approx(110.0)

    def test_integral_accumulation(self) -> None:
        """Constant error must produce ramp in integral term."""
        gains = PIDGains(kp=1.0, ti=2.0, td=0.0)
        pid = PIDController(gains=gains, u_bias=100.0, anti_windup=AntiWindupMethod.NONE)

        # Step 1: error = 2.0 -> trapezoid 0.5 * (2.0 + 0.0) * 0.1 * (1/2) = 0.05
        _, diag1 = pid.compute(setpoint=10.0, measurement=8.0, dt=0.1)
        # Step 2: error = 2.0 -> trapezoid 0.5 * (2.0 + 2.0) * 0.1 * (1/2) = 0.10
        _, diag2 = pid.compute(setpoint=10.0, measurement=8.0, dt=0.1)

        assert diag1["i"] == pytest.approx(0.05)
        assert diag2["i"] == pytest.approx(0.15)

    def test_derivative_kick_mitigation(self) -> None:
        """Derivative on measurement should not spike upon setpoint jump."""
        gains = PIDGains(kp=2.0, ti=10.0, td=1.0, n_filter=10.0)
        # 1. Derivative on measurement (default)
        pid_kickless = PIDController(gains=gains, derivative_on_measurement=True, u_bias=100.0)
        pid_kickless.reset(initial_measurement=350.0)
        _, diag_kickless = pid_kickless.compute(setpoint=360.0, measurement=350.0, dt=0.1)

        # PV did not move -> D term must be zero
        assert diag_kickless["d"] == pytest.approx(0.0)

        # 2. Derivative on error
        pid_with_kick = PIDController(gains=gains, derivative_on_measurement=False, u_bias=100.0)
        pid_with_kick.reset(initial_measurement=350.0)
        _, diag_kick = pid_with_kick.compute(setpoint=360.0, measurement=350.0, dt=0.1)

        # Error jumped from 0 to 10 -> D term must be strictly positive
        assert diag_kick["d"] > 0.0


class TestAntiWindupStrategies:
    """Rigorous comparison between None, Clamping, and Back-Calculation anti-windup."""

    def test_clamping_freezes_integrator_under_saturation(self) -> None:
        """When saturated at u_max and error > 0, clamping stops integral accumulation."""
        limits = ActuatorLimits(u_min=0.0, u_max=150.0, max_slew_rate=0.0)
        gains = PIDGains(kp=10.0, ti=1.0, td=0.0)

        pid_none = PIDController(
            gains=gains, actuator_limits=limits, anti_windup=AntiWindupMethod.NONE, u_bias=100.0
        )
        pid_clamp = PIDController(
            gains=gains, actuator_limits=limits, anti_windup=AntiWindupMethod.CLAMPING, u_bias=100.0
        )

        # Large setpoint step causing severe saturation (P = 10 * 20 = 200 > 150)
        for _ in range(20):
            pid_none.compute(setpoint=370.0, measurement=350.0, dt=0.1)
            _, diag_clamp = pid_clamp.compute(setpoint=370.0, measurement=350.0, dt=0.1)

        # Without anti-windup, integral term grows uncontrollably
        assert pid_none._integral_state > 100.0
        # With clamping, integral state is strictly frozen
        assert diag_clamp["i"] < 25.0

    def test_back_calculation_limits_windup(self) -> None:
        """Back-calculation continuously pulls integral term back to prevent windup."""
        limits = ActuatorLimits(u_min=0.0, u_max=120.0, max_slew_rate=0.0)
        gains = PIDGains(kp=5.0, ti=1.0, td=0.0, tt=0.5)

        pid_bc = PIDController(
            gains=gains,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.BACK_CALCULATION,
            u_bias=100.0,
        )

        for _ in range(15):
            pid_bc.compute(setpoint=370.0, measurement=350.0, dt=0.1)

        # Output remains saturated, but integral is bounded by tracking difference
        assert pid_bc._is_saturated is True
        assert pid_bc._integral_state < 30.0


class TestClosedLoopIntegration:
    """Validates full closed-loop simulation of CSTR with PID control."""

    def test_temperature_setpoint_tracking(
        self, plant: CSTRPlant, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        """PID controller successfully tracks a +2 K temperature setpoint change in CSTR."""
        ss, q_j_ss = nominal_steady_state
        # Nominal temperature is around ss.T (approx 346 K)
        target_T = ss.T - 2.0  # Cooling target: lower temperature requires higher coolant flow

        # PID gains for CSTR temperature loop
        gains = PIDGains(kp=-5.0, ti=1.5, td=0.2)  # Negative gain: higher T requires higher q_j
        limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=50.0)
        pid = PIDController(
            gains=gains,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        )

        sim = ClosedLoopSimulator()
        result = sim.run(
            plant=plant,
            controller=pid,
            initial_state=ss,
            t_span=(0.0, 10.0),
            dt=0.02,
            setpoint_func=lambda t: target_T,
        )

        final_pv = result.t_pv[-1]
        assert abs(final_pv - target_T) < 0.2  # Settled within 0.2 K of setpoint
        assert result.metrics.iae > 0.0
        assert result.metrics.tv > 0.0

    def test_load_disturbance_rejection(
        self, plant: CSTRPlant, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        """Controller rejects feed temperature load disturbance (+5 K step at t=2 min)."""
        ss, q_j_ss = nominal_steady_state
        gains = PIDGains(kp=-5.0, ti=1.5, td=0.2)
        limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)
        pid = PIDController(
            gains=gains,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        )

        sim = ClosedLoopSimulator()
        result = sim.run(
            plant=plant,
            controller=pid,
            initial_state=ss,
            t_span=(0.0, 12.0),
            dt=0.02,
            setpoint_func=lambda t: ss.T,  # Constant regulatory setpoint
            disturbance_func=lambda t: {"T_f": plant.params.T_f + 5.0} if t >= 2.0 else {},
        )

        # Before disturbance, error is 0. After disturbance at t=2.0, controller rejects it
        final_pv = result.t_pv[-1]
        assert abs(final_pv - ss.T) < 0.15  # Returns to within 0.15 K of nominal setpoint
        assert result.metrics.iae > 0.0
