"""IC-T03: NMPC alignment (operating point, slew rate, oracle/MHE feedback)."""

import numpy as np
import pytest

from src.classical_control.closed_loop import ClosedLoopSimulator
from src.controllers.optimal.nmpc_controller import CstrNmpcController
from src.sim_core.cstr_plant import CSTRPlant

DT = 0.05
SLEW = 80.0


@pytest.fixture(scope="module")
def plant_and_ss():
    plant = CSTRPlant()
    return plant, plant.find_steady_state(q_j=100.0)


class TestNmpcAlignment:
    def test_defaults_match_benchmark_steady_state(self, plant_and_ss) -> None:
        _, ss = plant_and_ss
        nmpc = CstrNmpcController(horizon_steps=5, t_step_min=DT)
        assert nmpc.target_setpoint_k == pytest.approx(ss.T)
        np.testing.assert_allclose(nmpc.estimator.x_hat[:3], ss.to_array(), rtol=1e-9)
        nmpc.reset(initial_measurement=ss.T)
        np.testing.assert_allclose(nmpc.estimator.x_hat[:3], ss.to_array(), rtol=1e-9)

    def test_rejects_unknown_feedback_mode(self) -> None:
        with pytest.raises(ValueError):
            CstrNmpcController(horizon_steps=5, t_step_min=DT, feedback_mode="kalman")

    @pytest.mark.parametrize("mode", ["oracle", "mhe"])
    def test_slew_rate_respected_in_closed_loop(self, plant_and_ss, mode: str) -> None:
        plant, ss = plant_and_ss
        target = ss.T - 5.0
        nmpc = CstrNmpcController(
            horizon_steps=8, t_step_min=DT, setpoint_temperature_k=target,
            feedback_mode=mode, max_slew_rate=SLEW, tj_noise_std=0.05, seed=7,
        )
        res = ClosedLoopSimulator().run(
            plant=plant, controller=nmpc, initial_state=ss, t_span=(0.0, 1.5), dt=DT,
            setpoint_func=lambda t: target, noise_std=0.05 if mode == "mhe" else 0.0, seed=3,
        )
        moves = np.abs(np.diff(np.concatenate([[100.0], res.u_applied])))
        assert np.max(moves) <= SLEW * DT + 1e-6
        # A -5 K step needs more coolant: the valve must actually move at the slew limit
        assert np.max(moves) == pytest.approx(SLEW * DT, rel=1e-3)
        assert np.all((res.u_applied >= 0.0) & (res.u_applied <= 300.0))

    def test_mhe_mode_uses_estimated_concentration(self, plant_and_ss) -> None:
        plant, ss = plant_and_ss
        nmpc = CstrNmpcController(horizon_steps=5, t_step_min=DT, feedback_mode="mhe")
        nmpc.reset(initial_measurement=ss.T)
        _, diag = nmpc.compute(ss.T, ss.T, DT, full_state=ss.to_array())
        assert diag["c_a"] == pytest.approx(diag["c_a_hat"])
        oracle = CstrNmpcController(horizon_steps=5, t_step_min=DT, feedback_mode="oracle")
        oracle.reset(initial_measurement=ss.T)
        state = ss.to_array() + np.array([0.01, 0.0, 0.0])
        _, diag_o = oracle.compute(ss.T, ss.T, DT, full_state=state)
        assert diag_o["c_a"] == pytest.approx(state[0])


class TestSobolSensitivity:
    def test_ishigami_indices_match_analytic_values(self) -> None:
        """SALib wiring check on the Ishigami function (a=7, b=0.1), known closed form."""
        from src.evaluation.sobol_sensitivity import sobol_indices

        problem = {
            "num_vars": 3,
            "names": ["x1", "x2", "x3"],
            "bounds": [[-np.pi, np.pi]] * 3,
        }

        def ishigami(x: np.ndarray) -> dict[str, float]:
            return {"f": np.sin(x[0]) + 7.0 * np.sin(x[1]) ** 2 + 0.1 * x[2] ** 4 * np.sin(x[0])}

        df = sobol_indices(ishigami, problem, n_base=4096, seed=1).set_index("parameter")
        np.testing.assert_allclose(df["S1"].to_numpy(), [0.3139, 0.4424, 0.0], atol=0.03)
        np.testing.assert_allclose(df["ST"].to_numpy(), [0.5576, 0.4424, 0.2437], atol=0.03)

    def test_schema_rejects_total_below_first_order(self) -> None:
        import pandas as pd
        import pandera as pa

        from src.evaluation.sobol_sensitivity import SobolIndicesSchema

        bad = pd.DataFrame(
            {"controller": ["SIMC"], "metric": ["IAE"], "parameter": ["UA_scale"],
             "S1": [0.6], "S1_conf": [0.01], "ST": [0.4], "ST_conf": [0.01]}
        )
        with pytest.raises(pa.errors.SchemaError):
            SobolIndicesSchema.validate(bad)

    def test_fractional_sensor_delay(self) -> None:
        from src.evaluation.sobol_sensitivity import DelayedMeasurementController

        class Probe:
            u_bias = 100.0
            seen: list[float] = []

            def reset(self, initial_measurement: float, initial_u: float | None = None) -> None:
                self.seen = []

            def compute(self, setpoint: float, measurement: float, dt: float):
                self.seen.append(measurement)
                return self.u_bias, {}

        probe = Probe()
        wrapped = DelayedMeasurementController(probe, delay_min=0.15, dt=0.1)
        wrapped.reset(initial_measurement=0.0)
        for y in [10.0, 20.0, 30.0, 40.0]:
            wrapped.compute(0.0, y, 0.1)
        # y(t - 0.15) with samples every 0.1 -> halfway between y[k-1] and y[k-2]
        assert probe.seen == pytest.approx([0.0, 5.0, 15.0, 25.0])

    def test_closed_loop_sobol_is_valid_and_exports_csv(self, tmp_path) -> None:
        from src.classical_control.foptd import FOPTDModel
        from src.classical_control.tuning_analytical import tune_amigo
        from src.evaluation.sobol_sensitivity import closed_loop_sobol, pid_factory

        gains = tune_amigo(FOPTDModel(k_p=-0.1190, tau=0.9096, theta=0.1462))
        df = closed_loop_sobol({"AMIGO": pid_factory(gains)}, n_base=128, seed=0)
        assert set(df["metric"]) == {"IAE", "TV"}
        assert len(df) == 2 * 4
        out = tmp_path / "sobol.csv"
        df.to_csv(out, index=False)
        assert out.stat().st_size > 0


class TestIC07NoiseLeakAndZeroNoiseEquivalence:
    """IC-T07: NMPC-Oracle is blind to sensor noise; NMPC-MHE matches it at zero noise."""

    def test_oracle_is_bit_identical_across_sensor_noise(self, plant_and_ss) -> None:
        plant, ss = plant_and_ss
        target = ss.T - 5.0
        runs = []
        for noise in (0.0, 1.0):
            nmpc = CstrNmpcController(
                horizon_steps=8, t_step_min=DT, setpoint_temperature_k=target,
                feedback_mode="oracle", max_slew_rate=SLEW,
            )
            runs.append(
                ClosedLoopSimulator().run(
                    plant=plant, controller=nmpc, initial_state=ss, t_span=(0.0, 1.0), dt=DT,
                    setpoint_func=lambda t: target, noise_std=noise, seed=11,
                )
            )
        clean, noisy = runs
        np.testing.assert_array_equal(clean.u_applied, noisy.u_applied)
        assert clean.metrics.iae == noisy.metrics.iae
        assert clean.metrics.tv == noisy.metrics.tv

    def test_zero_noise_mhe_reproduces_oracle_trajectory(self, plant_and_ss) -> None:
        plant, ss = plant_and_ss
        target = ss.T - 5.0
        metrics = {}
        for mode in ("oracle", "mhe"):
            nmpc = CstrNmpcController(
                horizon_steps=8, t_step_min=DT, setpoint_temperature_k=target,
                feedback_mode=mode, max_slew_rate=SLEW,
            )
            res = ClosedLoopSimulator().run(
                plant=plant, controller=nmpc, initial_state=ss, t_span=(0.0, 2.0), dt=DT,
                setpoint_func=lambda t: target, noise_std=0.0, seed=0,
            )
            metrics[mode] = res.metrics
        assert metrics["mhe"].iae == pytest.approx(metrics["oracle"].iae, rel=1e-2)
        assert metrics["mhe"].tv == pytest.approx(metrics["oracle"].tv, rel=1e-2)

    def test_oracle_uses_known_alpha_when_given(self, plant_and_ss) -> None:
        _, ss = plant_and_ss
        nmpc = CstrNmpcController(horizon_steps=5, t_step_min=DT, true_alpha_ua=0.7)
        nmpc.reset(initial_measurement=ss.T)
        _, diag = nmpc.compute(ss.T, ss.T + 3.0, DT, full_state=ss.to_array())
        assert diag["alpha_ua_hat"] == 0.7


def test_augmented_estimator_is_locally_observable_from_thermocouples(plant_and_ss) -> None:
    """Banca item 2: [C_A, T, T_j, alpha_UA] is locally observable from (T, T_j) at x_ss."""
    from src.controllers.optimal.nmpc_controller import observability_rank

    _, ss = plant_and_ss
    assert observability_rank(ss.to_array(), alpha_ua=1.0, q_j=100.0, dt=DT) == 4
    # With T only, the fouling factor and C_A must still be reconstructible
    assert observability_rank(ss.to_array(), alpha_ua=1.0, q_j=100.0, dt=DT, outputs=(1,)) == 4
