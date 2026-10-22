"""Unit tests for NMPC (do-mpc), Neural ODE (torchdyn), and PINN surrogate."""

import torch

from src.controllers.neural.neural_ode_controller import (
    CstrNeuralOdePredictor,
)
from src.controllers.neural.pinn_surrogate import CstrPhysicsInformedNet
from src.controllers.optimal.nmpc_controller import CstrNmpcController


def test_nmpc_controller_initialization_and_step() -> None:
    """Verifies that CstrNmpcController solves optimal step within physical actuator bounds."""
    controller = CstrNmpcController(horizon_steps=5, t_step_min=0.1, setpoint_temperature_k=350.0)

    # Initial state: C_A = 0.8 mol/L, T = 345.0 K, T_j = 310.0 K
    action_qj = controller.compute_action(c_a=0.8, temperature_k=345.0, t_jacket_k=310.0)

    assert isinstance(action_qj, float)
    assert 0.0 <= action_qj <= 300.0  # Must adhere to bounds configured in MPC


def test_neural_ode_vector_field_and_trajectory() -> None:
    """Tests Neural ODE vector field evaluation and continuous trajectory integration."""
    predictor = CstrNeuralOdePredictor(solver="euler", hidden_dim=32)

    x0 = torch.tensor([0.8, 350.0, 310.0], dtype=torch.float32)
    t_span = torch.linspace(0.0, 1.0, 5)

    traj = predictor.forward_trajectory(x0, t_span)

    # Shape must be [num_steps, batch_size, state_dim]
    assert traj.shape == (5, 1, 3)
    assert torch.all(torch.isfinite(traj))


def test_pinn_surrogate_physics_loss() -> None:
    """Verifies PINN state prediction and automatic differentiation residual calculation."""
    pinn = CstrPhysicsInformedNet(hidden_dim=32)

    t_and_u = torch.tensor([[0.5, 120.0], [1.0, 150.0]], dtype=torch.float32)
    states = pinn(t_and_u)

    assert states.shape == (2, 3)

    loss_dict = pinn.compute_physics_loss(t_and_u)
    assert "loss_mass" in loss_dict
    assert "loss_energy" in loss_dict
    assert "total_physics_loss" in loss_dict

    total_loss = loss_dict["total_physics_loss"]
    assert total_loss.item() >= 0.0
    assert torch.isfinite(total_loss)
