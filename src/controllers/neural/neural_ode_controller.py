"""Controlled Continuous-Time Neural ODE Vector Field and Predictor via torchdiffeq.

Replaces deprecated autonomous torchdyn models with a non-autonomous Controlled
Neural ODE dx/dt = f_theta(t, x, u(t)) integrated via torchdiffeq (supporting
explicit and adaptive stiff-capable solvers such as dopri5, bosh3, rk4, euler).
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Union

import torch
import torch.nn as nn
from torchdiffeq import odeint, odeint_adjoint

logger = logging.getLogger(__name__)


class CstrNeuralVectorField(nn.Module):
    """Parameterized controlled continuous vector field dx/dt = f_theta(t, x, u)."""

    def __init__(
        self,
        state_dim: int = 3,
        control_dim: int = 1,
        hidden_dim: int = 64,
        default_u: float = 100.0,
    ) -> None:
        """Initializes controlled neural vector field network.

        Args:
            state_dim: Number of continuous state variables (C_A, T, T_j).
            control_dim: Dimension of exogenous control input (q_j).
            hidden_dim: Number of hidden units per layer.
            default_u: Default coolant flow rate [L/min] when no control is bound.
        """
        super().__init__()
        self.state_dim = state_dim
        self.control_dim = control_dim
        self.default_u = float(default_u)
        self._control_source: Optional[
            Union[torch.Tensor, Callable[[torch.Tensor], torch.Tensor]]
        ] = None

        self.net = nn.Sequential(
            nn.Linear(state_dim + control_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, state_dim),
        )

    def bind_control(
        self,
        u: Optional[Union[float, torch.Tensor, Callable[[torch.Tensor], torch.Tensor]]],
    ) -> None:
        """Binds an exogenous control input u (constant or time-callable) for integration."""
        if isinstance(u, (int, float)):
            self._control_source = torch.tensor([float(u)], dtype=torch.float32)
        else:
            self._control_source = u

    def _resolve_u(self, t: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        """Resolves control tensor matching batch dimension of state x."""
        batch_size = x.shape[0]
        if self._control_source is None:
            u_val = torch.full(
                (batch_size, self.control_dim),
                self.default_u,
                dtype=x.dtype,
                device=x.device,
            )
        elif callable(self._control_source):
            u_raw = self._control_source(t)
            u_val = u_raw.to(dtype=x.dtype, device=x.device)
            if u_val.ndim == 0:
                u_val = u_val.view(1, 1).expand(batch_size, self.control_dim)
            elif u_val.ndim == 1:
                u_val = u_val.unsqueeze(0).expand(batch_size, -1)
        else:
            u_val = self._control_source.to(dtype=x.dtype, device=x.device)
            if u_val.ndim == 0:
                u_val = u_val.view(1, 1).expand(batch_size, self.control_dim)
            elif u_val.ndim == 1:
                if u_val.shape[0] == batch_size and self.control_dim == 1:
                    u_val = u_val.unsqueeze(-1)
                else:
                    u_val = u_val.unsqueeze(0).expand(batch_size, -1)
        return (u_val - 100.0) / 100.0

    def forward(
        self,
        t: torch.Tensor,
        x: torch.Tensor,
        u: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Evaluates controlled vector field dx/dt = f_theta(t, x, u).

        Args:
            t: Scalar time tensor.
            x: State tensor of shape [batch_size, 3] or [3].
            u: Optional explicit control input tensor [batch_size, 1].

        Returns:
            Time derivative tensor dx/dt of same shape as x.
        """
        squeeze_out = False
        if x.ndim == 1:
            x = x.unsqueeze(0)
            squeeze_out = True

        if u is not None:
            u_norm = (u.view(x.shape[0], -1) - 100.0) / 100.0
        else:
            u_norm = self._resolve_u(t, x)

        # Normalize states around nominal operating regime
        x_norm = torch.cat(
            [
                x[:, 0:1],
                (x[:, 1:2] - 350.0) / 50.0,
                (x[:, 2:3] - 300.0) / 50.0,
            ],
            dim=-1,
        )
        xu = torch.cat([x_norm, u_norm], dim=-1)
        dx = self.net(xu)
        return dx.squeeze(0) if squeeze_out else dx


class CstrNeuralOdePredictor:
    """Controlled Neural ODE wrapper using torchdiffeq for trajectory forecasting."""

    def __init__(
        self,
        solver: str = "rk4",
        hidden_dim: int = 64,
        use_adjoint: bool = False,
        rtol: float = 1e-4,
        atol: float = 1e-6,
    ) -> None:
        """Initializes Controlled Neural ODE predictor via torchdiffeq.

        Args:
            solver: Numerical ODE solver ('euler', 'rk4', 'midpoint', 'dopri5', 'bosh3').
            hidden_dim: Network hidden dimension.
            use_adjoint: Whether to use memory-efficient adjoint sensitivity method.
            rtol: Relative tolerance for adaptive solvers.
            atol: Absolute tolerance for adaptive solvers.
        """
        self.solver = solver
        self.use_adjoint = use_adjoint
        self.rtol = rtol
        self.atol = atol
        self.vector_field = CstrNeuralVectorField(
            state_dim=3, control_dim=1, hidden_dim=hidden_dim
        )
        logger.info(
            "CstrNeuralOdePredictor initialized (torchdiffeq solver=%s, hidden=%d, adjoint=%s)",
            solver,
            hidden_dim,
            use_adjoint,
        )

    def forward_trajectory(
        self,
        x0: torch.Tensor,
        t_span: torch.Tensor,
        u: Optional[Union[float, torch.Tensor, Callable[[torch.Tensor], torch.Tensor]]] = None,
    ) -> torch.Tensor:
        """Integrates controlled vector field across specified continuous time span.

        Args:
            x0: Initial state tensor of shape [batch_size, 3] or [3].
            t_span: Monotonically increasing time evaluation grid tensor [num_steps].
            u: Optional exogenous coolant flow rate q_j [L/min] (float, Tensor, or callable u(t)).

        Returns:
            Integrated trajectory tensor of shape [num_steps, batch_size, 3].
        """
        if x0.ndim == 1:
            x0 = x0.unsqueeze(0)

        self.vector_field.bind_control(u)
        integrator_fn = odeint_adjoint if self.use_adjoint else odeint

        if self.solver in ("dopri5", "bosh3", "adams"):
            trajectory = integrator_fn(
                self.vector_field,
                x0,
                t_span,
                method=self.solver,
                rtol=self.rtol,
                atol=self.atol,
            )
        else:
            trajectory = integrator_fn(
                self.vector_field,
                x0,
                t_span,
                method=self.solver,
            )
        return trajectory
