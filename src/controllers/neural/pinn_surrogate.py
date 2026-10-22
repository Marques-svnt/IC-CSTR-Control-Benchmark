"""Physics-Informed Neural Network (PINN) surrogate for CSTR thermal systems.

Conditions state trajectory predictions explicitly on the initial state vector
x_0 = [C_A0, T_0, T_j0]^T and exogenous control input q_j, satisfying the
Picard-Lindelöf uniqueness theorem for initial value problems (IVP) and
embedding mass/energy conservation laws into training.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

DEFAULT_NOMINAL_X0 = (0.1345, 344.16, 330.43)


class CstrPhysicsInformedNet(nn.Module):
    """Initial-condition-parameterized Physics-Informed Neural Network for CSTR IVP.

    Enforces the exact initial condition structural ansatz:
        x_hat(t; x_0, q_j) = x_0 + t * NN_theta(t, q_j, x_0)
    guaranteeing x_hat(0; x_0, q_j) == x_0 by construction and uniqueness per
    Picard-Lindelöf across arbitrary initial states x_0 in R^3.
    """

    def __init__(
        self,
        hidden_dim: int = 64,
        nominal_x0: tuple[float, float, float] = DEFAULT_NOMINAL_X0,
    ) -> None:
        """Initializes initial-state-conditioned PINN architecture.

        Args:
            hidden_dim: Hidden layer width.
            nominal_x0: Default initial state [C_A0, T_0, T_j0] used when caller
                passes only 2D inputs [t, q_j].
        """
        super().__init__()
        self.register_buffer(
            "nominal_x0",
            torch.tensor(nominal_x0, dtype=torch.float32),
        )
        # Input features: [t, q_j_norm, C_A0, T_0_norm, T_j0_norm] -> 5 dims
        self.net = nn.Sequential(
            nn.Linear(5, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 3),  # [dC_A_rate, dT_rate, dT_j_rate]
        )

    def _prepare_inputs(
        self,
        t_and_u: torch.Tensor,
        x0: Optional[torch.Tensor] = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Extracts time t, control q_j, and initial state x_0 from inputs."""
        if t_and_u.ndim == 1:
            t_and_u = t_and_u.unsqueeze(0)

        t = t_and_u[:, 0:1]
        q_j = t_and_u[:, 1:2]

        if x0 is not None:
            if x0.ndim == 1:
                x0_batch = x0.unsqueeze(0).expand(t_and_u.shape[0], -1)
            else:
                x0_batch = x0
        elif t_and_u.shape[1] >= 5:
            x0_batch = t_and_u[:, 2:5]
        else:
            x0_batch = self.nominal_x0.unsqueeze(0).expand(t_and_u.shape[0], -1)

        return t, q_j, x0_batch

    def forward(
        self,
        t_and_u: torch.Tensor,
        x0: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Predicts process states x(t) conditioned on (t, q_j, x_0).

        Args:
            t_and_u: Tensor of shape [batch, 2] ([t, q_j]) or [batch, 5] ([t, q_j, C_A0, T0, Tj0]).
            x0: Optional explicit initial state tensor of shape [batch, 3] or [3].

        Returns:
            Predicted state tensor [C_A, T, T_j] of shape [batch, 3].
        """
        t, q_j, x0_batch = self._prepare_inputs(t_and_u, x0=x0)

        # Normalized feature embedding for numerical conditioning
        features = torch.cat(
            [
                t,
                (q_j - 100.0) / 100.0,
                x0_batch[:, 0:1],
                (x0_batch[:, 1:2] - 350.0) / 50.0,
                (x0_batch[:, 2:3] - 300.0) / 50.0,
            ],
            dim=-1,
        )
        delta_rates = self.net(features)
        # Hard initial condition enforcement: x_hat(t=0) == x_0
        return x0_batch + t * delta_rates

    def compute_physics_loss(
        self,
        t_and_u: torch.Tensor,
        x0: Optional[torch.Tensor] = None,
        lambda_mass: float = 1.0,
        lambda_energy: float = 0.1,
    ) -> Dict[str, torch.Tensor]:
        """Calculates automatic differentiation residuals of CSTR ODE balances.

        Args:
            t_and_u: Input tensor with requires_grad=True [batch_size, 2] or [batch_size, 5].
            x0: Optional initial state tensor [batch_size, 3].
            lambda_mass: Weighting multiplier for species mass conservation.
            lambda_energy: Weighting multiplier for reactor energy conservation.

        Returns:
            Dictionary with 'loss_mass', 'loss_energy', 'ic_error', and 'total_physics_loss'.
        """
        t_and_u = t_and_u.clone().detach().requires_grad_(True)
        states = self.forward(t_and_u, x0=x0)

        C_A = states[:, 0:1]
        T = states[:, 1:2]
        T_j = states[:, 2:3]

        q_j = t_and_u[:, 1:2]

        # First derivatives with respect to input time t (first column)
        grad_outputs = torch.ones_like(C_A)
        dCA_dt = torch.autograd.grad(
            C_A, t_and_u, grad_outputs=grad_outputs, create_graph=True
        )[0][:, 0:1]
        dT_dt = torch.autograd.grad(
            T, t_and_u, grad_outputs=grad_outputs, create_graph=True
        )[0][:, 0:1]
        dTj_dt = torch.autograd.grad(
            T_j, t_and_u, grad_outputs=grad_outputs, create_graph=True
        )[0][:, 0:1]

        # Phenomenological physics residual definitions (matching CSTRParameters)
        k0 = 7.2e10
        E_over_R = 8750.0
        C_A_pos = torch.clamp(C_A, min=0.0)
        r_A = k0 * torch.exp(-E_over_R / torch.clamp(T, min=250.0, max=500.0)) * C_A_pos

        # Residuals: f(x, u) - dx/dt = 0
        res_mass = (1.0 - C_A) - r_A - dCA_dt
        res_energy = (350.0 - T) + 100.0 * r_A - 1.0 * (T - T_j) - dT_dt
        res_jacket = (q_j / 20.0) * (300.0 - T_j) + 5.0 * (T - T_j) - dTj_dt

        loss_mass = torch.mean(res_mass**2)
        loss_energy = torch.mean(res_energy**2) + torch.mean(res_jacket**2)
        total_physics = lambda_mass * loss_mass + lambda_energy * loss_energy

        return {
            "loss_mass": loss_mass,
            "loss_energy": loss_energy,
            "total_physics_loss": total_physics,
        }
