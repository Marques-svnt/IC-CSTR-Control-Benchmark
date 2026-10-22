"""Global variance-based (Sobol) sensitivity of closed-loop CSTR performance via SALib.

Decomposes the variance of the closed-loop IAE and TV of a controller under four
simultaneous plant uncertainties xi = (E_a/R scale, UA scale, C_Af, theta_sensor):
    S_i  = V[E(Y | xi_i)] / V(Y)            (first order)
    S_Ti = E[V(Y | xi_~i)] / V(Y)           (total order, S_Ti >= S_i)
estimated with Saltelli sampling (SALib.sample.sobol) and Jansen/Saltelli estimators
(SALib.analyze.sobol).
"""

import logging
from collections import deque
from collections.abc import Callable, Mapping
from typing import Any, Optional

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series
from SALib.analyze import sobol as sobol_analyze
from SALib.sample import sobol as sobol_sample

from src.classical_control.closed_loop import ClosedLoopSimulator
from src.classical_control.pid_controller import AntiWindupMethod, PIDController, PIDGains
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRParameters, CSTRPlant

logger = logging.getLogger(__name__)

# Uncertainty box: +/-3 % activation energy, fouling 65-105 % UA, +/-15 % feed, 0-0.1 min sensor lag
CSTR_UNCERTAINTY_PROBLEM: dict[str, Any] = {
    "num_vars": 4,
    "names": ["E_over_R_scale", "UA_scale", "C_Af", "theta_sensor"],
    "bounds": [[0.97, 1.03], [0.65, 1.05], [0.85, 1.15], [0.0, 0.10]],
}


class SobolIndicesSchema(pa.DataFrameModel):
    """Contract for Sobol index tables: finite indices and S_T >= S_1 - 1e-2."""

    controller: Series[str]
    metric: Series[str] = pa.Field(isin=["IAE", "TV"])
    parameter: Series[str]
    S1: Series[float] = pa.Field(nullable=False)
    S1_conf: Series[float] = pa.Field(ge=0.0, nullable=False)
    ST: Series[float] = pa.Field(nullable=False)
    ST_conf: Series[float] = pa.Field(ge=0.0, nullable=False)

    @pa.dataframe_check
    def total_dominates_first_order(cls, df: pd.DataFrame) -> Series[bool]:  # noqa: N805
        """Total-order index cannot fall below first order beyond estimator noise."""
        return df["ST"] >= df["S1"] - 1e-2

    class Config:
        """Reject unknown columns and coerce dtypes."""

        strict = True
        coerce = True


def sobol_indices(
    evaluate: Callable[[np.ndarray], Mapping[str, float]],
    problem: Mapping[str, Any],
    n_base: int,
    seed: int,
) -> pd.DataFrame:
    """Saltelli-sample `problem`, evaluate every sample and return S1/ST per output.

    Args:
        evaluate: Maps one parameter vector to named scalar outputs, e.g. {"IAE": .., "TV": ..}.
        problem: SALib problem dict (num_vars, names, bounds).
        n_base: Base sample size N (power of 2); the model is run N * (D + 2) times.
        seed: Seed of the scrambled Sobol sequence.

    Returns:
        Long DataFrame with columns metric, parameter, S1, S1_conf, ST, ST_conf.
    """
    samples = sobol_sample.sample(dict(problem), N=n_base, calc_second_order=False, seed=seed)
    outputs = [evaluate(x) for x in samples]
    rows = []
    for metric in outputs[0]:
        y = np.array([o[metric] for o in outputs], dtype=np.float64)
        if not np.all(np.isfinite(y)):
            raise ValueError(f"Non-finite model output for metric {metric!r}")
        si = sobol_analyze.analyze(
            dict(problem), y, calc_second_order=False, print_to_console=False, seed=seed
        )
        for i, name in enumerate(problem["names"]):
            rows.append(
                {
                    "metric": metric,
                    "parameter": name,
                    "S1": float(si["S1"][i]),
                    "S1_conf": float(si["S1_conf"][i]),
                    "ST": float(si["ST"][i]),
                    "ST_conf": float(si["ST_conf"][i]),
                }
            )
    return pd.DataFrame(rows)


class DelayedMeasurementController:
    """Feeds a controller the measurement delayed by `delay_min` (linear interpolation)."""

    def __init__(self, controller: Any, delay_min: float, dt: float) -> None:
        """Wraps `controller`.

        Args:
            controller: Object with reset(initial_measurement, initial_u) and
                compute(setpoint, measurement, dt) -> (u, diag), plus attribute u_bias.
            delay_min: Pure sensor dead time [min] (>= 0).
            dt: Sampling interval [min] used to convert the delay into samples.
        """
        if delay_min < 0.0:
            raise ValueError("delay_min must be non-negative")
        self.inner = controller
        self.u_bias = controller.u_bias
        self._lag = delay_min / dt
        self._buffer: deque[float] = deque(maxlen=int(np.floor(self._lag)) + 2)

    def reset(self, initial_measurement: float, initial_u: Optional[float] = None) -> None:
        """Fills the delay line with the initial measurement and resets the inner controller."""
        self._buffer.clear()
        self._buffer.extend([float(initial_measurement)] * self._buffer.maxlen)
        self.inner.reset(initial_measurement=initial_measurement, initial_u=initial_u)

    def compute(self, setpoint: float, measurement: float, dt: float) -> tuple[float, dict]:
        """Pushes the new sample and forwards y(t - delay) to the inner controller."""
        self._buffer.append(float(measurement))
        k = int(np.floor(self._lag))
        frac = self._lag - k
        y_k = self._buffer[-1 - k]
        y_k1 = self._buffer[-2 - k]
        delayed = (1.0 - frac) * y_k + frac * y_k1
        return self.inner.compute(setpoint=setpoint, measurement=delayed, dt=dt)


def pid_factory(
    gains: PIDGains,
    limits: Optional[ActuatorLimits] = None,
    u_bias: float = 100.0,
    y_ss: Optional[float] = None,
) -> Callable[[], PIDController]:
    """Returns a zero-argument constructor of a fresh clamping-anti-windup PID."""
    lim = limits or ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)
    return lambda: PIDController(
        gains=gains,
        actuator_limits=lim,
        anti_windup=AntiWindupMethod.CLAMPING,
        u_bias=u_bias,
        y_ss=y_ss,
    )


def closed_loop_sobol(
    controllers: Mapping[str, Callable[[], Any]],
    n_base: int = 512,
    seed: int = 2026,
    q_j_ss: float = 100.0,
    setpoint_step: float = -2.0,
    t_final: float = 8.0,
    dt: float = 0.05,
    problem: Mapping[str, Any] = CSTR_UNCERTAINTY_PROBLEM,
) -> pd.DataFrame:
    """Sobol indices of IAE and TV for each controller under the CSTR uncertainty box.

    Each sample perturbs (E/R, UA, C_Af) of the plant, inserts a sensor dead time, starts
    from the nominal steady state and applies a setpoint step at t = 0.5 min.

    Args:
        controllers: Name -> zero-argument factory of a fresh controller.
        n_base: Saltelli base sample size N (power of 2).
        seed: Seed for the Sobol sequence and the bootstrap confidence intervals.
        q_j_ss: Nominal coolant flow [L/min].
        setpoint_step: Setpoint change applied at t = 0.5 min [K].
        t_final: Simulation horizon [min].
        dt: Sampling interval [min].
        problem: SALib problem with names (E_over_R_scale, UA_scale, C_Af, theta_sensor).

    Returns:
        DataFrame validated by SobolIndicesSchema.
    """
    nominal = CSTRParameters()
    ss = CSTRPlant(nominal).find_steady_state(q_j=q_j_ss)
    target = ss.T + setpoint_step
    sim = ClosedLoopSimulator()
    frames = []
    for name, make in controllers.items():

        def evaluate(x: np.ndarray, make: Callable[[], Any] = make) -> dict[str, float]:
            plant = CSTRPlant(
                CSTRParameters(
                    E_over_R=nominal.E_over_R * float(x[0]),
                    UA=nominal.UA * float(x[1]),
                    C_Af=float(x[2]),
                )
            )
            ctrl = DelayedMeasurementController(make(), delay_min=float(x[3]), dt=dt)
            res = sim.run(
                plant=plant,
                controller=ctrl,
                initial_state=ss,
                t_span=(0.0, t_final),
                dt=dt,
                setpoint_func=lambda t: target if t >= 0.5 else ss.T,
            )
            return {"IAE": res.metrics.iae, "TV": res.metrics.tv}

        logger.info("Sobol campaign for %s (N=%d)", name, n_base)
        df = sobol_indices(evaluate, problem, n_base=n_base, seed=seed)
        df.insert(0, "controller", name)
        frames.append(df)
    return SobolIndicesSchema.validate(pd.concat(frames, ignore_index=True))
