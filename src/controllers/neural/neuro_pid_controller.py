"""Adaptive Neuro-PID and Differentiable Predictive Control (DPC) for Non-Linear CSTR.

Combines:
1. Classical baseline PID structure (SIMC / Optimal ITAE) with real-time neural gain
   scheduling (`NeuroPidController`).
2. Physics-Informed Differentiable Predictive Control (`DifferentiablePredictiveController`)
   built on PNNL `neuromancer` blocks with soft barrier penalties enforcing the
   Van Heerden thermal stability criterion and actuator slew-rate / saturation bounds.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from src.classical_control.pid_controller import AntiWindupMethod, PIDGains
from src.sim_core.actuators import ActuatorLimits, ValveActuator
from src.sim_core.cstr_plant import CSTRParameters

logger = logging.getLogger(__name__)


def _make_neuromancer_linear(in_features: int, out_features: int) -> nn.Module:
    """Instantiates a NeuroMANCER slim Linear map or standard nn.Linear fallback."""
    try:
        import neuromancer.slim as slim

        return slim.maps["linear"](in_features, out_features)
    except Exception:
        return nn.Linear(in_features, out_features)


class GainAdaptationNet(nn.Module):
    """Neural network predicting bounded relative gain adjustments delta_theta."""

    def __init__(self, input_dim: int = 5, hidden_dim: int = 32) -> None:
        """Initializes multi-layer perceptron for gain adjustment.

        Inputs: [error, d(error)/dt, C_A, T, T_j]
        Outputs: [delta_kp, delta_ti, delta_td] in [-1.0, 1.0] via Tanh
        """
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 3),
            nn.Tanh(),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """Predicts normalized gain modulation factors."""
        return self.net(features)


class NeuromancerDpcPolicy(nn.Module):
    """Differentiable Predictive Control (DPC) neural policy using PNNL NeuroMANCER slim blocks.

    Maps current state x_k = [C_A, T, T_j], reference r_k = T_sp, and previous control
    u_{k-1} into an optimal coolant flow rate u_k in [u_min, u_max] while minimizing
    a multi-step predictive horizon cost with Van Heerden thermal runaway barrier penalty.
    """

    def __init__(
        self,
        hidden_dim: int = 32,
        u_min: float = 0.0,
        u_max: float = 300.0,
        u_bias: float = 100.0,
    ) -> None:
        """Initializes NeuroMANCER DPC control policy.

        Args:
            hidden_dim: Width of NeuroMANCER linear/MLP layers.
            u_min: Minimum physical coolant flow rate [L/min].
            u_max: Maximum physical coolant flow rate [L/min].
            u_bias: Nominal steady-state coolant flow rate [L/min].
        """
        super().__init__()
        self.u_min = float(u_min)
        self.u_max = float(u_max)
        self.u_bias = float(u_bias)
        self.params = CSTRParameters()

        # Construct policy layers using NeuroMANCER slim linear maps
        self.fc1 = _make_neuromancer_linear(5, hidden_dim)
        self.fc2 = _make_neuromancer_linear(hidden_dim, hidden_dim)
        self.fc_out = _make_neuromancer_linear(hidden_dim, 1)
        self.act = nn.Tanh()

    def forward(
        self,
        state: torch.Tensor,
        setpoint: torch.Tensor,
        u_prev: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Evaluates bounded DPC control action u_k = pi_phi(x_k, r_k, u_{k-1}).

        Args:
            state: State tensor [batch, 3] with columns [C_A, T, T_j].
            setpoint: Target reactor temperature tensor [batch, 1].
            u_prev: Previous control action tensor [batch, 1].

        Returns:
            Control action tensor q_j in [u_min, u_max] of shape [batch, 1].
        """
        if state.ndim == 1:
            state = state.unsqueeze(0)
        if setpoint.ndim == 1:
            setpoint = setpoint.unsqueeze(-1)
        if u_prev is None:
            u_prev = torch.full_like(setpoint, self.u_bias)
        elif u_prev.ndim == 1:
            u_prev = u_prev.unsqueeze(-1)

        err_norm = (setpoint - state[:, 1:2]) / 10.0
        ca_norm = state[:, 0:1] - 0.1345
        t_norm = (state[:, 1:2] - 344.16) / 20.0
        tj_norm = (state[:, 2:3] - 330.43) / 20.0
        u_norm = (u_prev - self.u_bias) / 100.0

        feat = torch.cat([err_norm, ca_norm, t_norm, tj_norm, u_norm], dim=-1)
        h = self.act(self.fc1(feat))
        h = self.act(self.fc2(h))
        delta_u = self.act(self.fc_out(h)) * 150.0
        # Reverse-acting proportional feed-forward anchor + learned DPC residual
        u_raw = self.u_bias - 25.0 * (setpoint - state[:, 1:2]) + delta_u
        return torch.clamp(u_raw, min=self.u_min, max=self.u_max)

    def compute_dpc_van_heerden_loss(
        self,
        x0: torch.Tensor,
        setpoint: torch.Tensor,
        horizon_steps: int = 10,
        dt: float = 0.05,
        q_weight: float = 1.0,
        r_weight: float = 1e-3,
        lambda_vh: float = 1e-2,
        delta_min: float = 1000.0,
    ) -> Dict[str, torch.Tensor]:
        """Computes Differentiable Predictive Control rollout loss with Van Heerden barrier.

        Rolls out the differentiable physics-informed state-space equations over `horizon_steps`
        and penalizes tracking error, actuator effort variation, and violations of the
        Van Heerden thermal stability margin (dQ_rem/dT - dQ_gen/dT >= delta_min).

        Args:
            x0: Initial state batch [batch, 3].
            setpoint: Target temperature batch [batch, 1].
            horizon_steps: Prediction horizon N_p.
            dt: Discretization step [min].
            q_weight: Quadratic setpoint tracking weight Q.
            r_weight: Control rate-of-change penalty weight R.
            lambda_vh: Van Heerden stability barrier weight.
            delta_min: Minimum required Van Heerden slope margin [cal/(min*K)].

        Returns:
            Dictionary with 'tracking_loss', 'smoothness_loss',
            'van_heerden_loss', and 'total_dpc_loss'.
        """
        if x0.ndim == 1:
            x0 = x0.unsqueeze(0)
        if setpoint.ndim == 1:
            setpoint = setpoint.unsqueeze(-1)

        p = self.params
        x_curr = x0
        u_prev = torch.full((x0.shape[0], 1), self.u_bias, dtype=x0.dtype, device=x0.device)

        track_cost = torch.tensor(0.0, dtype=x0.dtype, device=x0.device)
        rate_cost = torch.tensor(0.0, dtype=x0.dtype, device=x0.device)
        vh_cost = torch.tensor(0.0, dtype=x0.dtype, device=x0.device)

        for _ in range(horizon_steps):
            u_k = self.forward(x_curr, setpoint, u_prev)
            c_a = torch.clamp(x_curr[:, 0:1], min=0.0, max=2.0)
            t_r = torch.clamp(x_curr[:, 1:2], min=250.0, max=500.0)
            t_j = torch.clamp(x_curr[:, 2:3], min=250.0, max=500.0)

            k_arr = p.k_0 * torch.exp(-p.E_over_R / t_r)
            r_a = k_arr * c_a

            dc_a = (p.q / p.V) * (p.C_Af - c_a) - r_a
            dt_r = (
                (p.q / p.V) * (p.T_f - t_r)
                + (-p.delta_H / p.rho_cp) * r_a
                - (p.UA / (p.V * p.rho_cp)) * (t_r - t_j)
            )
            dt_j = (u_k / p.V_j) * (p.T_jf - t_j) + (p.UA / (p.V_j * p.rho_j_cp_j)) * (t_r - t_j)

            x_next = x_curr + dt * torch.cat([dc_a, dt_r, dt_j], dim=-1)

            # Van Heerden thermal stability slope margin: dQ_rem/dT - dQ_gen/dT
            dq_gen_dt = (-p.delta_H) * p.V * k_arr * c_a * (p.E_over_R / (t_r**2))
            dq_rem_dt = p.q * p.rho_cp + p.UA
            margin_vh = dq_rem_dt - dq_gen_dt
            vh_violation = torch.relu(delta_min - margin_vh) / 1000.0

            track_cost = track_cost + q_weight * torch.mean((x_next[:, 1:2] - setpoint) ** 2)
            rate_cost = rate_cost + r_weight * torch.mean((u_k - u_prev) ** 2)
            vh_cost = vh_cost + lambda_vh * torch.mean(vh_violation**2)

            x_curr = x_next
            u_prev = u_k

        total_loss = track_cost + rate_cost + vh_cost
        return {
            "tracking_loss": track_cost,
            "smoothness_loss": rate_cost,
            "van_heerden_loss": vh_cost,
            "total_dpc_loss": total_loss,
        }


class NeuroPidController:
    """Adaptive Neuro-PID controller with physical actuator constraints and anti-windup."""

    supports_full_state: bool = True

    def __init__(
        self,
        base_gains: PIDGains,
        actuator_limits: Optional[ActuatorLimits] = None,
        anti_windup: AntiWindupMethod = AntiWindupMethod.CLAMPING,
        u_bias: float = 100.0,
        adaptation_scale: float = 0.35,
        hidden_dim: int = 32,
        use_dpc_blend: bool = False,
        dpc_blend_weight: float = 0.25,
    ) -> None:
        """Initializes Neuro-PID controller with optional NeuroMANCER DPC policy blending.

        Args:
            base_gains: Nominal PID gains (e.g. from SIMC or Nelder-Mead).
            actuator_limits: Physical bounds and slew rate of the control valve.
            anti_windup: Anti-windup clamping mechanism.
            u_bias: Nominal operating flow rate [L/min].
            adaptation_scale: Maximum fraction of gain modification (+/- scale * 100%).
            hidden_dim: Number of hidden units in the neural adapter.
            use_dpc_blend: If True, blends NeuroMANCER DPC feed-forward action.
            dpc_blend_weight: Weighting factor in [0, 1] for DPC action blending.
        """
        self.base_gains = base_gains
        self.limits = actuator_limits or ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)
        self.valve = ValveActuator(limits=self.limits, initial_position=u_bias)
        self.anti_windup = anti_windup
        self.u_bias = float(u_bias)
        self.adaptation_scale = float(adaptation_scale)
        self.use_dpc_blend = bool(use_dpc_blend)
        self.dpc_blend_weight = float(np.clip(dpc_blend_weight, 0.0, 1.0))

        self.neural_adapter = GainAdaptationNet(input_dim=5, hidden_dim=hidden_dim)
        self.neural_adapter.eval()
        self.dpc_policy = NeuromancerDpcPolicy(
            hidden_dim=hidden_dim,
            u_min=self.limits.u_min,
            u_max=self.limits.u_max,
            u_bias=self.u_bias,
        )
        self.dpc_policy.eval()

        # Internal discrete states
        self._integral_state: float = 0.0
        self._prev_error: float = 0.0
        self._prev_measurement: float = 344.16
        self._filtered_deriv: float = 0.0
        self._last_u_unconstrained: float = self.u_bias
        self._last_u_applied: float = self.u_bias
        self._is_saturated: bool = False

        # Current adaptive gains
        self.current_kp: float = base_gains.kp
        self.current_ti: float = base_gains.ti
        self.current_td: float = base_gains.td

        logger.info(
            "NeuroPidController initialized: base_kp=%.3f, ti=%.3f, td=%.3f, scale=%.2f",
            base_gains.kp,
            base_gains.ti,
            base_gains.td,
            adaptation_scale,
        )

    def reset(self, initial_measurement: float, initial_u: Optional[float] = None) -> None:
        """Resets controller internal state buffers."""
        u_init = initial_u if initial_u is not None else self.u_bias
        self.valve.reset(u_init)
        self._integral_state = 0.0
        self._prev_error = 0.0
        self._prev_measurement = float(initial_measurement)
        self._filtered_deriv = 0.0
        self._last_u_unconstrained = u_init
        self._last_u_applied = u_init
        self._is_saturated = False
        self.current_kp = self.base_gains.kp
        self.current_ti = self.base_gains.ti
        self.current_td = self.base_gains.td

    def bumpless_transfer(self, target_u: float, current_error: float = 0.0) -> None:
        """Adjusts internal integral state to guarantee C^0 bumpless policy handoff."""
        p_term = self.current_kp * current_error
        self._integral_state = float(target_u - self.u_bias - p_term)
        self._last_u_applied = float(target_u)
        self.valve.reset(float(target_u))

    def compute(
        self,
        setpoint: float,
        measurement: float,
        dt: float,
        full_state: Optional[np.ndarray] = None,
    ) -> Tuple[float, Dict[str, float]]:
        """Calculates adaptive control command with neural gain scheduling.

        Args:
            setpoint: Target reactor temperature [K].
            measurement: Measured reactor temperature [K].
            dt: Sampling interval [min].
            full_state: Continuous states [C_A, T, T_j].

        Returns:
            Tuple with (applied_actuator_flow, diagnostic_metrics).
        """
        error = setpoint - measurement
        d_error = (error - self._prev_error) / dt if dt > 0.0 else 0.0

        if full_state is not None:
            c_a = float(full_state[0])
            t_reactor = float(full_state[1])
            t_jacket = float(full_state[2])
        else:
            c_a = 0.1345
            t_reactor = measurement
            t_jacket = 330.43

        # 1. Neural Gain Adaptation Inference
        feat_vec = torch.tensor(
            [
                error / 10.0,
                d_error / 50.0,
                (c_a - 0.1345) / 0.5,
                (t_reactor - 344.16) / 20.0,
                (t_jacket - 330.43) / 20.0,
            ],
            dtype=torch.float32,
        )
        with torch.no_grad():
            delta = self.neural_adapter(feat_vec).numpy()

        # Update adaptive gains bounded by adaptation_scale
        scale = self.adaptation_scale
        self.current_kp = float(self.base_gains.kp * (1.0 + scale * delta[0]))
        self.current_ti = float(max(0.01, self.base_gains.ti * (1.0 - scale * delta[1])))
        self.current_td = float(max(0.0, self.base_gains.td * (1.0 + scale * delta[2])))

        # 2. Proportional Action
        p_term = self.current_kp * error

        # 3. Filtered Derivative Action on Measurement (eliminates derivative kick)
        d_meas = (measurement - self._prev_measurement) / dt if dt > 0.0 else 0.0
        n_filter = max(1.0, self.base_gains.n_filter)
        tau_f = (self.current_td / n_filter) if self.current_td > 0.0 else 0.01
        alpha = dt / (tau_f + dt)
        self._filtered_deriv = (1.0 - alpha) * self._filtered_deriv + alpha * d_meas
        d_term = -self.current_kp * self.current_td * self._filtered_deriv

        # 4. Integral Action with Anti-Windup Clamping
        ti_eff = max(1e-4, self.current_ti)
        delta_integral = (self.current_kp / ti_eff) * 0.5 * (error + self._prev_error) * dt

        should_freeze = False
        if self.anti_windup == AntiWindupMethod.CLAMPING and self._is_saturated:
            if (self._last_u_unconstrained > self.limits.u_max and p_term > 0) or (
                self._last_u_unconstrained < self.limits.u_min and p_term < 0
            ):
                should_freeze = True

        if not should_freeze:
            self._integral_state += delta_integral

        i_term = self._integral_state

        # Unconstrained ideal control effort (+ optional NeuroMANCER DPC blend)
        u_pid = self.u_bias + p_term + i_term + d_term
        if self.use_dpc_blend:
            with torch.no_grad():
                st_tensor = torch.tensor([[c_a, t_reactor, t_jacket]], dtype=torch.float32)
                sp_tensor = torch.tensor([[setpoint]], dtype=torch.float32)
                up_tensor = torch.tensor([[self._last_u_applied]], dtype=torch.float32)
                u_dpc = float(self.dpc_policy(st_tensor, sp_tensor, up_tensor).item())
            u_unconstrained = (
                1.0 - self.dpc_blend_weight
            ) * u_pid + self.dpc_blend_weight * u_dpc
        else:
            u_unconstrained = u_pid

        self._last_u_unconstrained = float(u_unconstrained)

        # 5. Physical Valve Actuation (Saturation and Rate Limiting)
        u_applied, self._is_saturated = self.valve.apply(u_desired=u_unconstrained, dt=dt)
        self._last_u_applied = float(u_applied)

        # Update memories for next sample
        self._prev_error = error
        self._prev_measurement = measurement

        diag = {
            "u_unconstrained": u_unconstrained,
            "p_term": p_term,
            "i_term": i_term,
            "d_term": d_term,
            "adaptive_kp": self.current_kp,
            "adaptive_ti": self.current_ti,
            "adaptive_td": self.current_td,
            "is_saturated": 1.0 if self._is_saturated else 0.0,
        }
        return u_applied, diag
