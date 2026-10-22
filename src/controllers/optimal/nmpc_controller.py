"""Nonlinear Model Predictive Control (NMPC) and Augmented MHE/EKF for CSTR via do-mpc.

Formulates continuous-time non-isothermal CSTR dynamics in CasADi/do-mpc coupled with
an online 4-state Augmented Estimator (reconstructing unmeasured reactant concentration
C_A(t) and heat exchanger fouling factor alpha_UA(t) = UA_eff(t) / UA_nom from thermal
measurements), eliminating static observer mismatch under fouling or feed disturbances.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any, Deque, Dict, Literal, Optional, Tuple

import casadi as ca
import do_mpc
import numpy as np
from scipy.optimize import least_squares

from src.sim_core.cstr_plant import CSTRParameters, CSTRPlant

logger = logging.getLogger(__name__)


def _nominal_state(params: CSTRParameters, q_j_ss: float) -> np.ndarray:
    """Steady state [C_A, T, T_j] of the benchmark plant at coolant flow q_j_ss."""
    return CSTRPlant(params=params).find_steady_state(q_j=q_j_ss).to_array()

# Keep legacy numpy behavior silently for do-mpc compatibility
try:
    ca.GlobalOptions.setNumpyMode(-1)
except (AttributeError, Exception):
    pass


class AugmentedCstrStateEstimator:
    """Online Moving Horizon / Augmented EKF estimator for [C_A, T, T_j, alpha_UA].

    Reconstructs unmeasured concentration C_A [mol/L] and dimensionless heat transfer
    fouling factor alpha_UA = UA_eff / UA_nom in [0.4, 1.2] using thermal measurements
    y_k = [T_k, T_{j,k}]^T over a moving horizon window N_m.
    """

    def __init__(
        self,
        params: Optional[CSTRParameters] = None,
        horizon_length: int = 8,
        initial_c_a: Optional[float] = None,
        initial_t: Optional[float] = None,
        initial_t_j: Optional[float] = None,
        initial_alpha_ua: float = 1.0,
        q_j_ss: float = 100.0,
    ) -> None:
        """Initializes augmented 4-state estimator.

        Args:
            params: Nominal CSTR physical parameters.
            horizon_length: Moving horizon estimation window length N_m.
            initial_c_a: Prior estimate of reactant concentration [mol/L].
            initial_t: Prior estimate of reactor temperature [K].
            initial_t_j: Prior estimate of jacket temperature [K].
            initial_alpha_ua: Prior estimate of fouling factor UA/UA_nom.
            q_j_ss: Nominal coolant flow whose steady state supplies any prior left as None.
        """
        self.params = params or CSTRParameters()
        self.x_ss = _nominal_state(self.params, q_j_ss)
        initial_c_a = self.x_ss[0] if initial_c_a is None else initial_c_a
        initial_t = self.x_ss[1] if initial_t is None else initial_t
        initial_t_j = self.x_ss[2] if initial_t_j is None else initial_t_j
        self.horizon_length = max(2, int(horizon_length))
        self.x_hat = np.array(
            [initial_c_a, initial_t, initial_t_j, initial_alpha_ua], dtype=np.float64
        )
        self.P = np.diag([0.05, 1.0, 1.0, 0.05])
        self.Q = np.diag([1e-4, 1e-2, 1e-2, 5e-4])
        self.R = np.diag([0.05, 0.05])
        self._history: Deque[Tuple[float, float, float, float]] = deque(
            maxlen=self.horizon_length
        )

    def reset(
        self,
        t_meas: float,
        t_j_meas: Optional[float] = None,
        c_a_init: Optional[float] = None,
        alpha_ua_init: float = 1.0,
    ) -> None:
        """Resets covariance and horizon buffer; None priors fall back to the steady state."""
        t_j_meas = self.x_ss[2] if t_j_meas is None else t_j_meas
        c_a_init = self.x_ss[0] if c_a_init is None else c_a_init
        self.x_hat = np.array(
            [c_a_init, t_meas, t_j_meas, alpha_ua_init], dtype=np.float64
        )
        self.P = np.diag([0.05, 1.0, 1.0, 0.05])
        self._history.clear()

    def _f_augmented(self, x: np.ndarray, u_qj: float) -> np.ndarray:
        """Evaluates continuous time derivatives for [C_A, T, T_j, alpha_UA]."""
        p = self.params
        c_a = max(0.0, float(x[0]))
        t_r = np.clip(float(x[1]), 250.0, 550.0)
        t_j = np.clip(float(x[2]), 250.0, 550.0)
        alpha = np.clip(float(x[3]), 0.3, 1.5)

        k = p.k_0 * np.exp(-p.E_over_R / t_r)
        r_a = k * c_a
        ua_eff = alpha * p.UA

        dc_a = (p.q / p.V) * (p.C_Af - c_a) - r_a
        dt_r = (
            (p.q / p.V) * (p.T_f - t_r)
            + (-p.delta_H / p.rho_cp) * r_a
            - (ua_eff / (p.V * p.rho_cp)) * (t_r - t_j)
        )
        dt_j = (u_qj / p.V_j) * (p.T_jf - t_j) + (ua_eff / (p.V_j * p.rho_j_cp_j)) * (t_r - t_j)
        return np.array([dc_a, dt_r, dt_j, 0.0], dtype=np.float64)

    def _jacobian_f(self, x: np.ndarray, u_qj: float) -> np.ndarray:
        """Computes analytical 4x4 state Jacobian of the augmented CSTR system."""
        p = self.params
        c_a = max(0.0, float(x[0]))
        t_r = np.clip(float(x[1]), 250.0, 550.0)
        t_j = np.clip(float(x[2]), 250.0, 550.0)
        alpha = np.clip(float(x[3]), 0.3, 1.5)

        k = p.k_0 * np.exp(-p.E_over_R / t_r)
        dk_dt = k * (p.E_over_R / (t_r**2))
        ua_eff = alpha * p.UA

        J = np.zeros((4, 4), dtype=np.float64)
        J[0, 0] = -(p.q / p.V) - k
        J[0, 1] = -dk_dt * c_a

        J[1, 0] = (-p.delta_H / p.rho_cp) * k
        J[1, 1] = (
            -(p.q / p.V)
            + (-p.delta_H / p.rho_cp) * dk_dt * c_a
            - (ua_eff / (p.V * p.rho_cp))
        )
        J[1, 2] = ua_eff / (p.V * p.rho_cp)
        J[1, 3] = -(p.UA / (p.V * p.rho_cp)) * (t_r - t_j)

        J[2, 1] = ua_eff / (p.V_j * p.rho_j_cp_j)
        J[2, 2] = -(u_qj / p.V_j) - (ua_eff / (p.V_j * p.rho_j_cp_j))
        J[2, 3] = (p.UA / (p.V_j * p.rho_j_cp_j)) * (t_r - t_j)
        return J

    def _rk4_augmented(self, x: np.ndarray, u_qj: float, dt: float, n_sub: int = 4) -> np.ndarray:
        """Advances the augmented state by dt with n_sub RK4 sub-steps (as in `_build_model`)."""
        h = dt / n_sub
        for _ in range(n_sub):
            k1 = self._f_augmented(x, u_qj)
            k2 = self._f_augmented(x + 0.5 * h * k1, u_qj)
            k3 = self._f_augmented(x + 0.5 * h * k2, u_qj)
            k4 = self._f_augmented(x + h * k3, u_qj)
            x = x + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        return x

    def step(
        self,
        u_prev: float,
        t_meas: float,
        t_j_meas: Optional[float] = None,
        dt: float = 0.05,
    ) -> np.ndarray:
        """Performs EKF propagation + Moving Horizon refinement on thermal measurements.

        Args:
            u_prev: Applied cooling jacket flow rate over previous interval [L/min].
            t_meas: Measured reactor temperature T [K].
            t_j_meas: Measured jacket temperature T_j [K] (if None, uses single-sensor T update).
            dt: Sampling interval [min].

        Returns:
            Updated 4D state estimate [C_A_hat, T_hat, T_j_hat, alpha_UA_hat].
        """
        dt_eff = max(1e-4, float(dt))

        # 1. RK4 state prediction, identical to the NMPC prediction model
        x_pred = self._rk4_augmented(self.x_hat, u_prev, dt_eff)

        F_k = np.eye(4) + dt_eff * self._jacobian_f(self.x_hat, u_prev)
        P_pred = F_k @ self.P @ F_k.T + self.Q

        # 2. Measurement update (T and optionally T_j)
        if t_j_meas is not None:
            H = np.array([[0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]], dtype=np.float64)
            y_vec = np.array([t_meas, t_j_meas], dtype=np.float64)
            R_mat = self.R
        else:
            H = np.array([[0.0, 1.0, 0.0, 0.0]], dtype=np.float64)
            y_vec = np.array([t_meas], dtype=np.float64)
            R_mat = self.R[:1, :1]

        innov = y_vec - (H @ x_pred)
        S_cov = H @ P_pred @ H.T + R_mat
        K_gain = P_pred @ H.T @ np.linalg.inv(S_cov)

        x_upd = x_pred + K_gain @ innov
        self.P = (np.eye(4) - K_gain @ H) @ P_pred

        # Record in moving horizon buffer
        tj_val = float(t_j_meas) if t_j_meas is not None else float(x_upd[2])
        self._history.append((float(u_prev), float(t_meas), tj_val, dt_eff))

        # 3. Moving Horizon Window Refinement for (C_A, alpha_UA) when window has >= 3 samples
        if len(self._history) >= 3:
            hist_list = list(self._history)

            def window_rollout(theta: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
                """Chained RK4 rollout of [C_A, T, T_j] from the window start with alpha_UA."""
                x_seg = np.array([theta[0], hist_list[0][1], hist_list[0][2], theta[1]])
                res = []
                for idx in range(len(hist_list) - 1):
                    # entry k stores the input applied over (k-1, k]: sample idx -> idx+1 uses
                    # the input recorded with sample idx + 1
                    u_i, t_next, tj_next, dt_i = hist_list[idx + 1]
                    x_seg = self._rk4_augmented(x_seg, u_i, dt_i)
                    res.append(t_next - x_seg[1])
                    res.append(0.5 * (tj_next - x_seg[2]))
                return np.asarray(res, dtype=np.float64), x_seg

            def mhe_residual(theta: np.ndarray) -> np.ndarray:
                # Prior arrival cost regularization, then window thermal-balance residuals
                prior = [2.0 * (theta[0] - x_upd[0]), 2.0 * (theta[1] - x_upd[3])]
                return np.concatenate([prior, window_rollout(theta)[0]])

            ls_res = least_squares(
                mhe_residual,
                x0=np.array([ np.clip(x_upd[0], 0.0, 1.0), np.clip(x_upd[3], 0.4, 1.2) ]),
                bounds=([0.0, 0.4], [1.0, 1.2]),
                max_nfev=15,
            )
            if ls_res.success:
                # Report C_A at the current sample, not at the window start
                x_upd[0] = float(window_rollout(ls_res.x)[1][0])
                x_upd[3] = float(ls_res.x[1])

        x_upd[0] = float(np.clip(x_upd[0], 0.0, 1.0))
        x_upd[1] = float(np.clip(x_upd[1], 250.0, 550.0))
        x_upd[2] = float(np.clip(x_upd[2], 250.0, 550.0))
        x_upd[3] = float(np.clip(x_upd[3], 0.4, 1.2))
        self.x_hat = x_upd
        return self.x_hat.copy()


class CstrNmpcController:
    """Nonlinear MPC for the exothermic CSTR with valve slew-rate and oracle/MHE feedback.

    The prediction model is the discrete-time ZOH map of the plant ODE (RK4 sub-steps over
    t_step) augmented with the previous valve position, so the valve constraint
    |q_j[k] - q_j[k-1]| <= max_slew_rate * t_step is imposed exactly on every predicted move.
    """

    supports_full_state: bool = True

    def __init__(
        self,
        horizon_steps: int = 15,
        t_step_min: float = 0.05,
        setpoint_temperature_k: Optional[float] = None,
        u_bias: float = 100.0,
        solver_mode: Literal["ipopt", "sqp_rti"] = "ipopt",
        mhe_horizon: int = 8,
        feedback_mode: Literal["oracle", "mhe"] = "oracle",
        max_slew_rate: float = 80.0,
        u_min: float = 0.0,
        u_max: float = 300.0,
        tj_noise_std: float = 0.0,
        seed: Optional[int] = None,
        params: Optional[CSTRParameters] = None,
        rk4_substeps: int = 4,
        true_alpha_ua: Optional[float] = None,
    ) -> None:
        """Initializes NMPC controller with horizon, time step, and online MHE/EKF observer.

        Args:
            horizon_steps: Prediction horizon length in discrete intervals.
            t_step_min: Sampling interval in minutes (must equal the simulator dt).
            setpoint_temperature_k: Target reactor temperature [K]. None -> plant steady state.
            u_bias: Nominal cooling jacket flow rate [L/min] (defines the operating point).
            solver_mode: Optimization solver strategy ('ipopt' or fast 'sqp_rti').
            mhe_horizon: Moving horizon window length for state & fouling estimation.
            feedback_mode: 'oracle' feeds true [C_A, T, T_j]; 'mhe' feeds the augmented
                estimator driven only by the thermal measurements (T, T_j).
            max_slew_rate: Valve slew-rate limit [L/min^2], same as ActuatorLimits.
            u_min: Lower valve bound [L/min].
            u_max: Upper valve bound [L/min].
            tj_noise_std: Std of Gaussian noise on the jacket thermocouple in 'mhe' mode [K].
            seed: Seed for the jacket-sensor noise generator.
            params: Plant parameters of the prediction model (defaults to the benchmark).
            rk4_substeps: RK4 sub-steps per sampling interval in the prediction model.
            true_alpha_ua: Known fouling factor for 'oracle' mode. None -> the Oracle estimates
                alpha_UA from the noise-free thermocouples (never from the noisy sensor).

        Raises:
            ValueError: On unknown feedback mode or non-positive slew rate / time step.
        """
        if feedback_mode not in ("oracle", "mhe"):
            raise ValueError(f"feedback_mode must be 'oracle' or 'mhe', got {feedback_mode!r}")
        if max_slew_rate <= 0.0 or t_step_min <= 0.0:
            raise ValueError("max_slew_rate and t_step_min must be positive")
        self.params = params or CSTRParameters()
        self.horizon_steps = horizon_steps
        self.t_step_min = t_step_min
        self.u_bias: float = float(u_bias)
        self.x_ss = _nominal_state(self.params, self.u_bias)
        self.target_setpoint_k: float = (
            float(self.x_ss[1]) if setpoint_temperature_k is None else float(setpoint_temperature_k)
        )
        self.solver_mode = solver_mode
        self.feedback_mode = feedback_mode
        self.max_slew_rate = float(max_slew_rate)
        self.u_min, self.u_max = float(u_min), float(u_max)
        self.tj_noise_std = float(tj_noise_std)
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        self.rk4_substeps = int(rk4_substeps)
        self.true_alpha_ua = true_alpha_ua

        self.estimator = AugmentedCstrStateEstimator(
            params=self.params, horizon_length=mhe_horizon, q_j_ss=self.u_bias
        )
        self._estimated_c_a: float = float(self.estimator.x_hat[0])
        self._estimated_t_j: float = float(self.estimator.x_hat[2])
        self._estimated_alpha_ua: float = float(self.estimator.x_hat[3])
        self._last_u: float = self.u_bias

        self.model = self._build_model()
        self.mpc = self._build_mpc()
        logger.info(
            "CstrNmpcController initialized (N=%d, dt=%.3f min, sp=%.2f K, mode=%s, slew=%.1f)",
            horizon_steps,
            t_step_min,
            self.target_setpoint_k,
            feedback_mode,
            self.max_slew_rate,
        )

    def _build_model(self) -> do_mpc.model.Model:
        """Discrete ZOH model x+ = RK4(f(x, q_j)), u_prev+ = q_j, with TVP setpoint and UA."""
        p = self.params
        model = do_mpc.model.Model("discrete")
        C_A = model.set_variable(var_type="_x", var_name="C_A")
        T = model.set_variable(var_type="_x", var_name="T")
        T_j = model.set_variable(var_type="_x", var_name="T_j")
        model.set_variable(var_type="_x", var_name="u_prev")
        q_j = model.set_variable(var_type="_u", var_name="q_j")
        model.set_variable(var_type="_tvp", var_name="T_sp")
        alpha_ua = model.set_variable(var_type="_tvp", var_name="alpha_ua")

        ua_eff = alpha_ua * p.UA

        def f(x: ca.SX) -> ca.SX:
            c_a, t_r, t_j = x[0], x[1], x[2]
            r_a = p.k_0 * ca.exp(-p.E_over_R / t_r) * c_a
            return ca.vertcat(
                (p.q / p.V) * (p.C_Af - c_a) - r_a,
                (p.q / p.V) * (p.T_f - t_r)
                + (-p.delta_H / p.rho_cp) * r_a
                - (ua_eff / (p.V * p.rho_cp)) * (t_r - t_j),
                (q_j / p.V_j) * (p.T_jf - t_j) + (ua_eff / (p.V_j * p.rho_j_cp_j)) * (t_r - t_j),
            )

        h = self.t_step_min / self.rk4_substeps
        x = ca.vertcat(C_A, T, T_j)
        for _ in range(self.rk4_substeps):
            k1 = f(x)
            k2 = f(x + 0.5 * h * k1)
            k3 = f(x + 0.5 * h * k2)
            k4 = f(x + h * k3)
            x = x + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

        model.set_rhs("C_A", x[0])
        model.set_rhs("T", x[1])
        model.set_rhs("T_j", x[2])
        model.set_rhs("u_prev", q_j)
        model.setup()
        return model

    def _build_mpc(self) -> do_mpc.controller.MPC:
        """Constructs and configures the optimization solver."""
        mpc = do_mpc.controller.MPC(self.model)
        ipopt_opts: Dict[str, Any] = {"ipopt.print_level": 0, "print_time": 0}
        if self.solver_mode == "sqp_rti":
            ipopt_opts["ipopt.max_iter"] = 15
            ipopt_opts["ipopt.tol"] = 1e-3

        mpc.set_param(
            n_horizon=self.horizon_steps,
            t_step=self.t_step_min,
            n_robust=0,
            store_full_solution=False,
            nlpsol_opts=ipopt_opts,
        )

        err = self.model.x["T"] - self.model.tvp["T_sp"]
        mpc.set_objective(mterm=err**2, lterm=err**2)
        mpc.set_rterm(q_j=1e-3)

        mpc.bounds["lower", "_u", "q_j"] = self.u_min
        mpc.bounds["upper", "_u", "q_j"] = self.u_max
        mpc.bounds["lower", "_x", "T"] = 280.0
        mpc.bounds["upper", "_x", "T"] = 450.0

        # Valve slew rate on every predicted move (hard constraint)
        max_move = self.max_slew_rate * self.t_step_min
        move = self.model.u["q_j"] - self.model.x["u_prev"]
        mpc.set_nl_cons("slew_up", move, ub=max_move)
        mpc.set_nl_cons("slew_down", -move, ub=max_move)

        tvp_template = mpc.get_tvp_template()

        def tvp_fun(_t_now: float) -> Any:
            tvp_template["_tvp", :, "T_sp"] = self.target_setpoint_k
            tvp_template["_tvp", :, "alpha_ua"] = self._estimated_alpha_ua
            return tvp_template

        mpc.set_tvp_fun(tvp_fun)
        mpc.setup()
        return mpc

    def _x0(self, c_a: float, temperature_k: float, t_jacket_k: float) -> np.ndarray:
        return np.array([[c_a], [temperature_k], [t_jacket_k], [self._last_u]], dtype=np.float64)

    def reset(self, initial_measurement: float, initial_u: Optional[float] = None) -> None:
        """Resets controller internal memory, MHE estimator, and solver state.

        Args:
            initial_measurement: Initial reactor temperature measurement [K].
            initial_u: Initial control command [L/min].
        """
        if initial_u is not None:
            self.u_bias = float(initial_u)
        self._last_u = self.u_bias
        self._rng = np.random.default_rng(self._seed)
        self.estimator.reset(t_meas=float(initial_measurement))
        self._estimated_c_a = float(self.estimator.x_hat[0])
        self._estimated_t_j = float(self.estimator.x_hat[2])
        self._estimated_alpha_ua = float(self.estimator.x_hat[3])

        self.mpc.x0 = self._x0(self._estimated_c_a, float(initial_measurement), self._estimated_t_j)
        self.mpc.set_initial_guess()
        logger.debug("CstrNmpcController reset at T=%.2f K", initial_measurement)

    def compute_action(
        self,
        c_a: float,
        temperature_k: float,
        t_jacket_k: float,
    ) -> float:
        """Solves the OCP from the given state and returns the slew-feasible first move.

        Args:
            c_a: Concentration of reactant A [mol/L].
            temperature_k: Reactor bulk temperature [K].
            t_jacket_k: Cooling jacket temperature [K].

        Returns:
            Optimal cooling jacket flow rate q_j [L/min].
        """
        x0 = self._x0(float(c_a), float(temperature_k), float(t_jacket_k))
        self.mpc.x0 = x0
        self.mpc.set_initial_guess()

        u_opt = float(np.asarray(self.mpc.make_step(x0)).ravel()[0])
        # IPOPT satisfies constraints only to tolerance: clamp to the exact physical envelope
        max_move = self.max_slew_rate * self.t_step_min
        action = float(np.clip(u_opt, self._last_u - max_move, self._last_u + max_move))
        action = float(np.clip(action, self.u_min, self.u_max))
        self._last_u = action
        logger.debug(
            "NMPC step: x=[%.3f, %.1f, %.1f] (alpha_UA=%.2f) -> u=%.2f",
            c_a,
            temperature_k,
            t_jacket_k,
            self._estimated_alpha_ua,
            action,
        )
        return action

    def compute(
        self,
        setpoint: float,
        measurement: float,
        dt: float,
        full_state: Optional[np.ndarray] = None,
    ) -> Tuple[float, Dict[str, float]]:
        """Standard control step interface compatible with ClosedLoopSimulator.

        The estimator always runs (it supplies alpha_UA to the model). In 'oracle' mode the
        OCP is initialised from the true state; in 'mhe' mode from the estimate built on the
        (noisy) T measurement and a noisy jacket thermocouple T_j.

        Args:
            setpoint: Target reactor temperature [K].
            measurement: Measured temperature [K].
            dt: Sampling step [min].
            full_state: True continuous state [C_A, T, T_j] (only T_j is used in 'mhe').

        Returns:
            Tuple with (applied_control_signal, diagnostic_dictionary).
        """
        self.target_setpoint_k = float(setpoint)
        t_meas, t_j_meas = float(measurement), None
        if full_state is not None:
            t_j_meas = float(full_state[2])
            if self.feedback_mode == "mhe" and self.tj_noise_std > 0.0:
                t_j_meas += float(self._rng.normal(0.0, self.tj_noise_std))
            if self.feedback_mode == "oracle":
                # Oracle never sees the sensor: noise-free thermocouples only
                t_meas = float(full_state[1])
        x_est = self.estimator.step(
            u_prev=self._last_u, t_meas=t_meas, t_j_meas=t_j_meas, dt=dt
        )
        self._estimated_c_a = float(x_est[0])
        self._estimated_t_j = float(x_est[2])
        self._estimated_alpha_ua = float(x_est[3])
        if self.feedback_mode == "oracle" and self.true_alpha_ua is not None:
            self._estimated_alpha_ua = float(self.true_alpha_ua)

        if self.feedback_mode == "oracle" and full_state is not None:
            c_a, t, t_j = (float(v) for v in full_state[:3])
        else:
            c_a, t, t_j = float(x_est[0]), float(x_est[1]), float(x_est[2])

        u = self.compute_action(c_a, t, t_j)
        diag = {
            "u_unconstrained": u,
            "error": setpoint - measurement,
            "c_a": c_a,
            "c_a_hat": self._estimated_c_a,
            "t_j": t_j,
            "alpha_ua_hat": self._estimated_alpha_ua,
        }
        return u, diag


def observability_rank(
    x_ss: np.ndarray,
    alpha_ua: float,
    q_j: float,
    dt: float,
    outputs: Tuple[int, ...] = (1, 2),
    params: Optional[CSTRParameters] = None,
) -> int:
    """Rank of the discrete observability matrix of the augmented estimator model.

    Linearizes x_a = [C_A, T, T_j, alpha_UA] (alpha_UA random walk) at (x_ss, alpha_ua, q_j),
    discretizes as Phi = I + dt * J (the EKF covariance map) and stacks H Phi^i, i = 0..3.

    Args:
        x_ss: Operating point [C_A, T, T_j].
        alpha_ua: Fouling factor at the operating point.
        q_j: Coolant flow at the operating point [L/min].
        dt: Sampling interval [min].
        outputs: Measured augmented-state indices (1 = T, 2 = T_j).
        params: Plant parameters (defaults to the benchmark).

    Returns:
        Numerical rank (4 = locally observable).
    """
    est = AugmentedCstrStateEstimator(params=params, q_j_ss=q_j)
    x_a = np.array([*np.asarray(x_ss, dtype=np.float64)[:3], alpha_ua])
    phi = np.eye(4) + dt * est._jacobian_f(x_a, q_j)
    h = np.eye(4)[list(outputs)]
    obs = np.vstack([h @ np.linalg.matrix_power(phi, i) for i in range(4)])
    return int(np.linalg.matrix_rank(obs))
