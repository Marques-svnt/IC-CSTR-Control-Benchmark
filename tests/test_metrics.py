"""Unit tests for performance metrics calculation."""

import numpy as np
import pytest

from src.evaluation.metrics import evaluate_performance


class TestControlPerformanceMetrics:
    """Tests accuracy and edge cases of the benchmark metrics evaluator."""

    def test_zero_error_produces_zero_iae_itae_ise(self) -> None:
        """When PV perfectly tracks SP, error metrics must be identically zero."""
        t = np.linspace(0, 10, 101)
        sp = np.ones_like(t) * 350.0
        y = np.ones_like(t) * 350.0
        u = np.ones_like(t) * 100.0

        metrics = evaluate_performance(t=t, y=y, setpoint=sp, u=u)

        assert metrics.iae == pytest.approx(0.0)
        assert metrics.itae == pytest.approx(0.0)
        assert metrics.ise == pytest.approx(0.0)
        assert metrics.tv == pytest.approx(0.0)
        assert metrics.overshoot_pct == pytest.approx(0.0)
        assert metrics.settling_time == pytest.approx(0.0)

    def test_total_variation_monotonic_vs_oscillatory(self) -> None:
        """Oscillating actuator signal must generate strictly higher TV than monotonic signal."""
        t = np.linspace(0, 10, 11)
        sp = np.ones_like(t) * 10.0
        y = np.linspace(0, 10, 11)

        # Monotonic ramp from 0 to 10: TV should be 10.0
        u_mono = np.linspace(0, 10, 11)
        m_mono = evaluate_performance(t, y, sp, u_mono)
        assert m_mono.tv == pytest.approx(10.0)

        # Oscillating signal between 0 and 10
        u_osc = np.array([0, 10, 0, 10, 0, 10, 0, 10, 0, 10, 0], dtype=np.float64)
        m_osc = evaluate_performance(t, y, sp, u_osc)
        assert m_osc.tv == pytest.approx(100.0)
        assert m_osc.tv > m_mono.tv

    def test_overshoot_detection(self) -> None:
        """Tests that peak overshoot above final setpoint is correctly computed."""
        t = np.linspace(0, 5, 6)
        sp = np.ones_like(t) * 100.0
        # Starts at 0, peaks at 120, settles at 100 -> Overshoot is (120 - 100)/100 * 100 = 20%
        y = np.array([0.0, 50.0, 120.0, 105.0, 100.0, 100.0])
        u = np.ones_like(t) * 50.0

        metrics = evaluate_performance(t, y, sp, u)
        assert metrics.overshoot_pct == pytest.approx(20.0)

    def test_dimension_mismatch_raises_error(self) -> None:
        """Throws ValueError if input arrays have unequal lengths."""
        t = np.array([0.0, 1.0, 2.0])
        y = np.array([10.0, 20.0])
        sp = np.array([20.0, 20.0, 20.0])
        u = np.array([5.0, 5.0, 5.0])

        with pytest.raises(ValueError, match="Array length mismatch"):
            evaluate_performance(t, y, sp, u)

    def test_total_variation_counts_initial_actuator_jump(self) -> None:
        """Valve jumping 100 -> 300 L/min at t=0 and staying there has TV = 200 L/min."""
        t = np.linspace(0, 5, 51)
        sp = np.full_like(t, 394.65)
        y = np.full_like(t, 396.65)
        u = np.full_like(t, 300.0)

        assert evaluate_performance(t, y, sp, u).tv == pytest.approx(0.0)
        assert evaluate_performance(t, y, sp, u, u_init=100.0).tv == pytest.approx(200.0)


class TestIC06StepShiftedItae:
    """IC-T06: ITAE weights the error by time elapsed since the setpoint step."""

    def test_pre_step_error_contributes_no_itae(self) -> None:
        """Error before t_step must not inflate ITAE when t_step is given."""
        t = np.linspace(0.0, 10.0, 1001)
        sp = np.full_like(t, 348.0)
        y = np.where(t < 0.5, 353.0, 348.0)  # 5 K error only before the step
        u = np.full_like(t, 100.0)

        shifted = evaluate_performance(t=t, y=y, setpoint=sp, u=u, t_step=0.5)
        unshifted = evaluate_performance(t=t, y=y, setpoint=sp, u=u)

        assert shifted.itae == pytest.approx(0.0, abs=1e-12)
        assert unshifted.itae > 0.0
        assert shifted.iae == pytest.approx(unshifted.iae)
