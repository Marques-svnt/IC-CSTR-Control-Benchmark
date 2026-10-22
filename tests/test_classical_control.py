"""IC-T01: modern classical baselines (Tyreus-Luyben, AMIGO) and 2-DOF setpoint-weighted PID."""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.classical_control.closed_loop import ClosedLoopSimulator
from src.classical_control.foptd import FOPTDModel
from src.classical_control.pid_controller import AntiWindupMethod, PIDController, PIDGains
from src.classical_control.tuning_analytical import (
    TuningRule,
    tune_amigo,
    tune_analytical,
    tune_tyreus_luyben,
)
from src.classical_control.tuning_optimization import calculate_maximum_sensitivity_foptd
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRPlant, CSTRState

NOMINAL_FOPTD = FOPTDModel(k_p=-0.1190, tau=0.9096, theta=0.1462)


class TestModernAnalyticalRules:
    """Tyreus-Luyben and AMIGO tuning on the nominal CSTR FOPTD model."""

    @pytest.mark.parametrize(
        ("tuner", "mode"),
        [
            pytest.param(
                tune_tyreus_luyben,
                "PID",
                marks=pytest.mark.xfail(
                    strict=True,
                    reason="Exact TL-PID (Ku/2.2, 2.2Pu, Pu/6.3) gives Ms~2.32 on this FOPTD; "
                    "ticket criterion Ms<=1.65 is not met by the published rule. "
                    "Escalated to the auditor instead of altering the formula.",
                ),
            ),
            (tune_tyreus_luyben, "PI"),
            (tune_amigo, "PID"),
        ],
    )
    def test_robustness_ms_below_1_65(self, tuner, mode: str) -> None:
        gains = tuner(NOMINAL_FOPTD, mode=mode)
        assert gains.kp < 0.0
        assert gains.ti > 0.0
        assert calculate_maximum_sensitivity_foptd(NOMINAL_FOPTD, gains) <= 1.65

    def test_tyreus_luyben_ultimate_point_satisfies_phase_condition(self) -> None:
        """Kp = Ku/2.2 and Pu recovered from Ti must satisfy the -pi phase crossover."""
        gains = tune_tyreus_luyben(NOMINAL_FOPTD)
        p_u = gains.ti / 2.2
        w_u = 2.0 * np.pi / p_u
        k, tau, theta = NOMINAL_FOPTD.k_p, NOMINAL_FOPTD.tau, NOMINAL_FOPTD.theta
        assert theta * w_u + np.arctan(tau * w_u) == pytest.approx(np.pi, abs=1e-8)
        k_u = gains.kp * 2.2
        # |K_u * G(j w_u)| = 1 at the ultimate point
        assert abs(k_u * k) / np.sqrt(1.0 + (tau * w_u) ** 2) == pytest.approx(1.0, rel=1e-9)
        assert gains.td == pytest.approx(p_u / 6.3)

    def test_tyreus_luyben_pi_mode(self) -> None:
        pid = tune_tyreus_luyben(NOMINAL_FOPTD)
        pi = tune_tyreus_luyben(NOMINAL_FOPTD, mode="PI")
        assert pi.td == 0.0
        assert pi.ti == pytest.approx(pid.ti)
        assert pi.kp == pytest.approx(pid.kp * 2.2 / 3.2)

    def test_amigo_matches_astrom_hagglund_equations(self) -> None:
        k, tau, theta = NOMINAL_FOPTD.k_p, NOMINAL_FOPTD.tau, NOMINAL_FOPTD.theta
        g = tune_amigo(NOMINAL_FOPTD)
        assert g.kp == pytest.approx((0.2 + 0.45 * tau / theta) / k)
        assert g.ti == pytest.approx((0.4 * theta + 0.8 * tau) / (theta + 0.1 * tau) * theta)
        assert g.td == pytest.approx(0.5 * theta * tau / (0.3 * theta + tau))

    def test_wired_into_tune_analytical(self) -> None:
        assert tune_analytical(NOMINAL_FOPTD, TuningRule.TYREUS_LUYBEN) == tune_tyreus_luyben(
            NOMINAL_FOPTD
        )
        assert tune_analytical(NOMINAL_FOPTD, TuningRule.AMIGO) == tune_amigo(NOMINAL_FOPTD)

    @settings(max_examples=60, deadline=None)
    @given(
        k=st.floats(min_value=-5.0, max_value=-0.01),
        tau=st.floats(min_value=0.1, max_value=10.0),
        ratio=st.floats(min_value=0.05, max_value=2.0),
    )
    def test_reverse_acting_sign_and_closed_loop_stability(
        self, k: float, tau: float, ratio: float
    ) -> None:
        """For any reverse-acting FOPTD, both rules give Kp < 0 and a finite Ms (< 3)."""
        model = FOPTDModel(k_p=k, tau=tau, theta=ratio * tau)
        for tuner in (tune_tyreus_luyben, tune_amigo):
            gains = tuner(model)
            assert gains.kp < 0.0
            assert 1.0 <= calculate_maximum_sensitivity_foptd(model, gains) < 3.0


class TestTwoDofPid:
    """Setpoint weighting (beta, gamma) in deviation variables."""

    def test_gains_weights_are_validated(self) -> None:
        with pytest.raises(ValueError):
            PIDGains(kp=-1.0, ti=1.0, beta=1.5)
        with pytest.raises(ValueError):
            PIDGains(kp=-1.0, ti=1.0, gamma=-0.1)

    def test_no_proportional_bias_from_absolute_kelvin(self) -> None:
        """At y_meas = y_sp = y_ss, a beta<1 controller must output exactly u_bias."""
        pid = PIDController(PIDGains(kp=-20.0, ti=1.0, td=0.1, beta=0.5), u_bias=100.0)
        pid.reset(initial_measurement=396.65)
        u, _ = pid.compute(setpoint=396.65, measurement=396.65, dt=0.02)
        assert u == pytest.approx(100.0)

    @staticmethod
    def _simulate(
        plant: CSTRPlant, ss: CSTRState, q_j_ss: float, beta: float, servo: bool
    ) -> np.ndarray:
        base = tune_amigo(NOMINAL_FOPTD)
        gains = PIDGains(kp=base.kp, ti=base.ti, td=base.td, beta=beta, gamma=0.0)
        pid = PIDController(
            gains=gains,
            actuator_limits=ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0),
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
            y_ss=ss.T,
        )
        if servo:
            sp, dist = (lambda t: ss.T - 2.0), None
        else:
            sp, dist = (lambda t: ss.T), (lambda t: {"T_f": 355.0} if t >= 0.5 else {})
        res = ClosedLoopSimulator().run(
            plant=plant,
            controller=pid,
            initial_state=ss,
            t_span=(0.0, 6.0),
            dt=0.02,
            setpoint_func=sp,
            disturbance_func=dist,
        )
        return res

    def test_two_dof_reduces_overshoot_preserves_regulation(
        self, plant: CSTRPlant, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        ss, q_j_ss = nominal_steady_state
        servo_1dof = self._simulate(plant, ss, q_j_ss, beta=1.0, servo=True)
        servo_2dof = self._simulate(plant, ss, q_j_ss, beta=0.5, servo=True)
        assert servo_2dof.metrics.overshoot_pct < servo_1dof.metrics.overshoot_pct

        reg_1dof = self._simulate(plant, ss, q_j_ss, beta=1.0, servo=False)
        reg_2dof = self._simulate(plant, ss, q_j_ss, beta=0.5, servo=False)
        np.testing.assert_allclose(reg_2dof.t_pv, reg_1dof.t_pv, rtol=0, atol=1e-10)
        np.testing.assert_allclose(reg_2dof.u_applied, reg_1dof.u_applied, rtol=0, atol=1e-10)


def test_sensitivity_magnitude_peak_equals_ms() -> None:
    from src.classical_control.tuning_optimization import sensitivity_magnitude_foptd

    gains = tune_amigo(NOMINAL_FOPTD)
    omegas = np.logspace(-3, 3, 5000)
    mag = sensitivity_magnitude_foptd(NOMINAL_FOPTD, gains, omegas)
    assert mag.shape == omegas.shape
    assert np.max(mag) == pytest.approx(calculate_maximum_sensitivity_foptd(NOMINAL_FOPTD, gains))
    assert mag[0] < 1e-2  # integral action: |S(j0)| -> 0


class TestIC06SlewAndTrueStateMetrics:
    """IC-T06: directional clamping under slew-rate saturation and true-state IAE."""

    def test_clamping_freezes_integrator_during_slew_limited_cooling_ramp(self) -> None:
        """Kp < 0 and e_k < 0 drive u toward u_max; slew saturation must freeze the integrator."""
        limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=50.0)
        gains = PIDGains(kp=-5.0, ti=1.0, td=0.0)
        pid = PIDController(
            gains=gains, actuator_limits=limits, anti_windup=AntiWindupMethod.CLAMPING, u_bias=100.0
        )

        integrals = []
        for _ in range(10):
            _, diag = pid.compute(setpoint=340.0, measurement=350.0, dt=0.1)
            integrals.append(diag["i"])

        # Step 1 integrates once; from step 2 the valve is slew-saturated and integration freezes
        assert integrals[0] > 0.0
        assert all(i == pytest.approx(integrals[0]) for i in integrals[1:])

    def test_closed_loop_iae_uses_true_reactor_temperature(
        self, plant: CSTRPlant, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        """IAE must integrate |SP - T_true|, not the noisy sensor signal."""
        ss, q_j_ss = nominal_steady_state
        pid = PIDController(
            gains=PIDGains(kp=-5.0, ti=1.5, td=0.2),
            actuator_limits=ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=50.0),
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        )
        sp = ss.T - 2.0
        result = ClosedLoopSimulator().run(
            plant=plant,
            controller=pid,
            initial_state=ss,
            t_span=(0.0, 5.0),
            dt=0.02,
            setpoint_func=lambda t: sp,
            noise_std=1.0,
            seed=0,
        )

        err_true = np.abs(sp - result.states[:, 1])
        expected = np.sum(0.5 * (err_true[:-1] + err_true[1:]) * np.diff(result.t))
        assert result.metrics.iae == pytest.approx(float(expected), rel=1e-9)
        err_pv = np.abs(sp - result.t_pv)
        noisy = np.sum(0.5 * (err_pv[:-1] + err_pv[1:]) * np.diff(result.t))
        assert result.metrics.iae != pytest.approx(float(noisy), rel=1e-6)


class TestLoopMarginsFoptdVsLinearized:
    """Banca item 3: phase margin of the FOPTD design loop vs the exact linearized plant."""

    def test_phase_margin_of_integrator_is_90_degrees(self) -> None:
        from src.classical_control.tuning_optimization import phase_margin_deg

        omegas = np.logspace(-2, 2, 4000)
        assert phase_margin_deg(2.0 / (1j * omegas), omegas) == pytest.approx(90.0, abs=1e-6)

    def test_foptd_margin_respects_ms_bound(self) -> None:
        from src.classical_control.tuning_optimization import loop_gain_foptd, phase_margin_deg

        omegas = np.logspace(-3, 3, 20000)
        gains = tune_amigo(NOMINAL_FOPTD)
        ms = calculate_maximum_sensitivity_foptd(NOMINAL_FOPTD, gains)
        pm = phase_margin_deg(loop_gain_foptd(NOMINAL_FOPTD, gains, omegas), omegas)
        assert pm >= np.degrees(2.0 * np.arcsin(1.0 / (2.0 * ms))) - 1e-6

    def test_linearized_loop_gain_matches_existing_ms(
        self, plant: CSTRPlant, nominal_steady_state: tuple[CSTRState, float]
    ) -> None:
        from src.classical_control.tuning_optimization import (
            calculate_maximum_sensitivity,
            loop_gain_linearized,
        )

        ss, q_j_ss = nominal_steady_state
        gains = tune_amigo(NOMINAL_FOPTD)
        omegas = np.logspace(-3, 3, 2000)
        loop = loop_gain_linearized(plant, ss, q_j_ss, gains, omegas, theta=0.01)
        ms = calculate_maximum_sensitivity(plant, ss, q_j_ss, gains, theta=0.01)
        assert np.max(np.abs(1.0 / (1.0 + loop))) == pytest.approx(ms, rel=1e-9)


class TestNaiveClampingAblation:
    """Artigo 1 ablation: amplitude-only, sign-blind clamping misses the reverse-acting windup."""

    def test_naive_rule_keeps_integrating_during_slew_limited_ramp(self) -> None:
        limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=50.0)
        gains = PIDGains(kp=-5.0, ti=1.0, td=0.0)
        naive = PIDController(gains, limits, AntiWindupMethod.CLAMPING_NAIVE, u_bias=100.0)
        directional = PIDController(gains, limits, AntiWindupMethod.CLAMPING, u_bias=100.0)
        i_naive = i_dir = 0.0
        for _ in range(10):
            # Kp < 0 and e < 0 push u up; the valve is slew-limited, never at u_max
            i_naive = naive.compute(setpoint=340.0, measurement=350.0, dt=0.1)[1]["i"]
            i_dir = directional.compute(setpoint=340.0, measurement=350.0, dt=0.1)[1]["i"]
        assert i_naive > 5.0 * i_dir > 0.0

    def test_naive_rule_freezes_at_amplitude_limit_with_positive_error(self) -> None:
        limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=1e6)
        pid = PIDController(
            PIDGains(kp=50.0, ti=1.0), limits, AntiWindupMethod.CLAMPING_NAIVE, u_bias=100.0
        )
        pid.compute(setpoint=360.0, measurement=350.0, dt=0.1)  # saturates at u_max with e > 0
        i1 = pid.compute(setpoint=360.0, measurement=350.0, dt=0.1)[1]["i"]
        i2 = pid.compute(setpoint=360.0, measurement=350.0, dt=0.1)[1]["i"]
        assert i2 == pytest.approx(i1)
