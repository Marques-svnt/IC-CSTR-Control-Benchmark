"""Unit and integration tests for FOPTD identification and tuning rules.

Covers ZN, Cohen-Coon, Skogestad SIMC, and numerical optimization.
"""

import numpy as np
import pytest

from src.classical_control.closed_loop import ClosedLoopSimulator
from src.classical_control.foptd import FOPTDModel, identify_foptd
from src.classical_control.pid_controller import AntiWindupMethod, PIDController, PIDGains
from src.classical_control.tuning_analytical import TuningRule, tune_analytical
from src.classical_control.tuning_optimization import (
    OptimizationCriterion,
    calculate_maximum_sensitivity,
    tune_by_optimization,
)
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRPlant, CSTRState
from src.sim_core.integrator import NumericalIntegrator


class TestFOPTDIdentification:
    """Tests accuracy of step-response transfer function identification."""

    def test_synthetic_foptd_recovery(self) -> None:
        """Identifies known synthetic FOPTD model parameters with high precision."""
        true_model = FOPTDModel(k_p=-0.5, tau=2.0, theta=0.3)
        t = np.linspace(0, 10, 201)
        delta_u = 10.0
        y_synthetic = true_model.step_response(t=t, delta_u=delta_u, y0=350.0)

        identified, rmse = identify_foptd(t=t, y=y_synthetic, delta_u=delta_u, y0=350.0)

        assert rmse < 1e-3
        assert identified.k_p == pytest.approx(true_model.k_p, rel=0.05)
        assert identified.tau == pytest.approx(true_model.tau, rel=0.05)
        assert identified.theta == pytest.approx(true_model.theta, abs=0.08)

    def test_cstr_open_loop_identification(
        self,
        plant: CSTRPlant,
        integrator: NumericalIntegrator,
        nominal_steady_state: tuple[CSTRState, float],
    ) -> None:
        """Identifies FOPTD model from non-linear open-loop CSTR simulation."""
        ss, q_j_ss = nominal_steady_state
        delta_q = 10.0  # +10 L/min coolant step

        res = integrator.simulate_open_loop(
            plant=plant,
            initial_state=ss,
            t_span=(0.0, 8.0),
            dt=0.02,
            u_func=lambda t: q_j_ss + delta_q,
        )

        foptd, rmse = identify_foptd(t=res.t, y=res.states[:, 1], delta_u=delta_q, y0=ss.T)

        # CSTR cooling response has negative gain and positive time constant
        assert foptd.k_p < 0.0
        assert foptd.tau > 0.1
        assert foptd.theta >= 0.0
        assert rmse < 0.2  # Close fit to first-order approximation


class TestAnalyticalTuningRules:
    """Verifies ZN, Cohen-Coon, and SIMC gain formulas and closed-loop stability."""

    @pytest.fixture
    def cstr_foptd(self) -> FOPTDModel:
        """Representative FOPTD parameters for CSTR cooling loop."""
        return FOPTDModel(k_p=-0.15, tau=1.2, theta=0.25)

    def test_tuning_signs_match_process(self, cstr_foptd: FOPTDModel) -> None:
        """Negative process gain must yield negative controller gains (reverse action)."""
        rules = [
            TuningRule.ZIEGLER_NICHOLS_PID,
            TuningRule.COHEN_COON_PID,
            TuningRule.SKOGESTAD_SIMC_PID,
            TuningRule.SKOGESTAD_SIMC_PI,
        ]

        for rule in rules:
            gains = tune_analytical(cstr_foptd, rule=rule)
            assert gains.kp < 0.0
            assert gains.ti > 0.0
            if rule != TuningRule.SKOGESTAD_SIMC_PI:
                assert gains.td > 0.0

    def test_simc_closed_loop_stabilization(
        self,
        plant: CSTRPlant,
        nominal_steady_state: tuple[CSTRState, float],
        cstr_foptd: FOPTDModel,
    ) -> None:
        """Skogestad SIMC tuned PID stabilizes the non-linear CSTR upon setpoint change."""
        ss, q_j_ss = nominal_steady_state
        gains = tune_analytical(cstr_foptd, rule=TuningRule.SKOGESTAD_SIMC_PID, tau_c=0.5)

        limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=100.0)
        pid = PIDController(
            gains=gains,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        )

        sim = ClosedLoopSimulator()
        target_T = ss.T - 2.0

        res = sim.run(
            plant=plant,
            controller=pid,
            initial_state=ss,
            t_span=(0.0, 8.0),
            dt=0.02,
            setpoint_func=lambda t: target_T,
        )

        # Must reach setpoint within 0.3 K
        assert abs(res.t_pv[-1] - target_T) < 0.3
        assert res.metrics.overshoot_pct < 40.0


class TestOptimizationTuning:
    """Verifies frequency-domain Ms sensitivity and numerical optimization tuner."""

    def test_maximum_sensitivity_calculation(
        self, plant: CSTRPlant, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        """Validates Ms computation yields physically realistic robustness margins."""
        ss, q_j_ss = nominal_steady_state
        # Conservative gain
        conservative_gains = tune_analytical(
            FOPTDModel(k_p=-0.15, tau=1.2, theta=0.25),
            rule=TuningRule.SKOGESTAD_SIMC_PID,
            tau_c=1.0,
        )

        ms = calculate_maximum_sensitivity(plant, ss, q_j_ss, conservative_gains)
        assert 1.0 < ms < 2.5

    def test_optimization_tuning_improves_or_meets_robustness(
        self, plant: CSTRPlant, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        """Optimization finds gains that respect Ms <= 1.8 constraint."""
        ss, q_j_ss = nominal_steady_state
        opt_gains = tune_by_optimization(
            plant=plant,
            nominal_state=ss,
            q_j_ss=q_j_ss,
            target_dT=-1.5,
            criterion=OptimizationCriterion.ITAE,
            max_ms=1.8,
            t_sim=4.0,
            dt=0.04,
        )

        assert opt_gains.kp < 0.0
        assert opt_gains.ti > 0.0
        ms_opt = calculate_maximum_sensitivity(plant, ss, q_j_ss, opt_gains)
        assert ms_opt <= 2.0  # Satisfies robustness target

    def test_optimization_enforces_foptd_dead_time_ms(
        self, plant: CSTRPlant, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        """With the identified FOPTD passed in, the Ms <= 1.60 penalty acts on the delayed loop."""
        from src.classical_control.tuning_optimization import calculate_maximum_sensitivity_foptd

        ss, q_j_ss = nominal_steady_state
        foptd = FOPTDModel(k_p=-0.1190, tau=0.9096, theta=0.1462)
        opt_gains = tune_by_optimization(
            plant=plant,
            nominal_state=ss,
            q_j_ss=q_j_ss,
            target_dT=-2.0,
            criterion=OptimizationCriterion.ITAE,
            max_ms=1.6,
            t_sim=4.0,
            dt=0.04,
            foptd=foptd,
            limits=ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0),
        )
        assert calculate_maximum_sensitivity_foptd(foptd, opt_gains) <= 1.60 + 1e-3


class TestClosedLoopTotalVariation:
    """ClosedLoopSimulator must account for the first actuator move from q_j_ss."""

    def test_tv_includes_jump_from_bias(
        self, plant: CSTRPlant, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        ss, q_j_ss = nominal_steady_state
        pid = PIDController(
            gains=PIDGains(kp=-200.0, ti=1.0),
            actuator_limits=ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=1e6),
            u_bias=q_j_ss,
        )
        res = ClosedLoopSimulator().run(
            plant=plant, controller=pid, initial_state=ss, t_span=(0.0, 0.2), dt=0.02,
            setpoint_func=lambda t: ss.T - 2.0,
        )
        u = res.u_applied
        expected = abs(u[0] - q_j_ss) + np.sum(np.abs(np.diff(u)))
        assert u[0] > q_j_ss
        assert res.metrics.tv == pytest.approx(expected)
