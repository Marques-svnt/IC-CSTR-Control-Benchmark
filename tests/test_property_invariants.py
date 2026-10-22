"""Property-based (Hypothesis) and SOTA integration tests for CSTR control framework."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandera.pandas as pa
import pytest
import torch
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from src.classical_control.foptd import FOPTDModel
from src.classical_control.pid_controller import PIDGains
from src.classical_control.subspace_identification import (
    compare_foptd_vs_subspace,
    generate_prbs_signal,
    identify_subspace_or_armax,
)
from src.classical_control.tuning_optimization import (
    analyze_loop_margins_and_gang_of_4,
    calculate_maximum_sensitivity_foptd,
)
from src.controllers.agents.cstr_supervisory_graph import (
    CstrSupervisorState,
    audit_van_heerden_criterion,
)
from src.controllers.neural.neural_ode_controller import CstrNeuralOdePredictor
from src.controllers.neural.neuro_pid_controller import (
    NeuromancerDpcPolicy,
    NeuroPidController,
)
from src.controllers.neural.pinn_surrogate import CstrPhysicsInformedNet
from src.controllers.optimal.nmpc_controller import (
    AugmentedCstrStateEstimator,
    CstrNmpcController,
)
from src.evaluation.metrics import evaluate_performance
from src.evaluation.pareto import (
    ParetoPoint,
    compute_hypervolume_pymoo,
    optimize_pid_nsga3_pymoo,
    run_sobol_global_sensitivity,
)
from src.evaluation.plot_styles import apply_repulsive_annotations, get_tueplots_rcparams
from src.sim_core.actuators import ActuatorLimits, ValveActuator
from src.sim_core.cstr_plant import CSTRParameters, CSTRPlant, CSTRState
from src.sim_core.integrator import NumericalIntegrator
from src.sim_core.schemas import (
    validate_benchmark_dataframe,
    validate_trajectory_dataframe,
)


@settings(max_examples=25, deadline=None)
@given(
    c_a0=st.floats(min_value=0.02, max_value=0.95),
    t0=st.floats(min_value=310.0, max_value=380.0),
    t_j0=st.floats(min_value=290.0, max_value=350.0),
    q_j=st.floats(min_value=0.0, max_value=300.0),
)
def test_property_thermodynamic_state_invariants(
    c_a0: float, t0: float, t_j0: float, q_j: float
) -> None:
    """Proves C_A(t) in [0, C_Af] and T(t) > 0 for admissible states and q_j in [0, 300]."""
    plant = CSTRPlant()
    integrator = NumericalIntegrator(method="RK45")
    state0 = CSTRState(C_A=c_a0, T=t0, T_j=t_j0)

    next_state = integrator.step(
        plant=plant,
        current_state=state0,
        q_j=q_j,
        t_current=0.0,
        dt=0.02,
    )

    assert 0.0 <= next_state.C_A <= plant.params.C_Af + 1e-6
    assert next_state.T > 0.0
    assert next_state.T_j > 0.0


@settings(max_examples=30, deadline=None)
@given(
    u_cmd=st.lists(
        st.floats(min_value=-150.0, max_value=500.0),
        min_size=5,
        max_size=25,
    ),
    max_slew=st.floats(min_value=10.0, max_value=150.0),
    dt=st.floats(min_value=0.01, max_value=0.2),
)
def test_property_actuator_slew_rate_and_saturation_bounds(
    u_cmd: list[float], max_slew: float, dt: float
) -> None:
    """Proves strict valve saturation [u_min, u_max] and slew-rate limit |Delta u / dt| <= S_max."""
    limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=max_slew)
    valve = ValveActuator(limits=limits, initial_position=100.0)

    prev_u = 100.0
    for desired in u_cmd:
        u_app, _ = valve.apply(u_desired=desired, dt=dt)
        assert 0.0 <= u_app <= 300.0
        slew_rate = abs(u_app - prev_u) / dt
        assert slew_rate <= max_slew + 1e-5
        prev_u = u_app


@settings(max_examples=25, deadline=None)
@given(
    c_a=st.floats(min_value=0.05, max_value=0.90),
    t_low=st.floats(min_value=310.0, max_value=340.0),
    delta_t=st.floats(min_value=5.0, max_value=35.0),
)
def test_property_van_heerden_monotonicity_with_temperature(
    c_a: float, t_low: float, delta_t: float
) -> None:
    """Proves Van Heerden heat generation slope increases monotonically with T."""
    base_state: CstrSupervisorState = {
        "time": 0.0,
        "setpoint": 344.16,
        "temperature": t_low,
        "c_a": c_a,
        "t_j": 330.0,
        "heat_generation_slope": 0.0,
        "heat_removal_slope": 0.0,
        "stability_margin": 0.0,
        "regime": "nominal",
        "recommended_controller": "pid_simc",
        "control_action": 100.0,
        "audit_message": "",
    }
    high_state = dict(base_state)
    high_state["temperature"] = t_low + delta_t

    res_low = audit_van_heerden_criterion(base_state)
    res_high = audit_van_heerden_criterion(high_state)  # type: ignore[arg-type]

    assert float(res_high["heat_generation_slope"]) > float(res_low["heat_generation_slope"])
    assert float(res_high["stability_margin"]) < float(res_low["stability_margin"])


@settings(max_examples=25, deadline=None)
@given(
    err_scale=st.floats(min_value=0.0, max_value=20.0),
    u_Step=st.floats(min_value=-50.0, max_value=50.0),
    kp=st.floats(min_value=-40.0, max_value=-1.0),
    ti=st.floats(min_value=0.2, max_value=5.0),
)
def test_property_metrics_non_negativity_and_ms_bound(
    err_scale: float, u_Step: float, kp: float, ti: float
) -> None:
    """Proves IAE, ITAE, ISE, TV >= 0 and sensitivity peak Ms >= 1.0."""
    t = np.linspace(0.0, 5.0, 25)
    sp = np.full_like(t, 345.0)
    y = 345.0 - err_scale * np.exp(-t)
    u = 100.0 + u_Step * np.sin(t)

    m = evaluate_performance(t=t, y=y, setpoint=sp, u=u)
    assert m.iae >= 0.0
    assert m.itae >= 0.0
    assert m.ise >= 0.0
    assert m.tv >= 0.0
    assert m.overshoot_pct >= 0.0

    foptd = FOPTDModel(k_p=-0.15, tau=1.2, theta=0.25)
    gains = PIDGains(kp=kp, ti=ti, td=0.05)
    ms = calculate_maximum_sensitivity_foptd(foptd, gains, n_freqs=200)
    assert ms >= 1.0 - 1e-6


def test_pandera_and_pydantic_contracts() -> None:
    """Verifies runtime validation of CSTR parameters, trajectories, and benchmark tables."""
    with pytest.raises(ValidationError):
        CSTRParameters(V=-10.0)

    t = np.linspace(0.0, 1.0, 5)
    states = np.column_stack(
        [
            np.full(5, 0.2),
            np.full(5, 345.0),
            np.full(5, 330.0),
        ]
    )
    q_j = np.full(5, 100.0)
    df_traj = validate_trajectory_dataframe(t, states, q_j)
    assert len(df_traj) == 5

    # Non-monotonic time must fail CstrTrajectorySchema
    bad_t = np.array([0.0, 0.5, 0.2, 0.8, 1.0])
    with pytest.raises(pa.errors.SchemaError):
        validate_trajectory_dataframe(bad_t, states, q_j)

    m = evaluate_performance(t=t, y=states[:, 1], setpoint=states[:, 1] - 1.0, u=q_j)
    df_bench = m.to_validated_dataframe(method="SIMC", ms=1.45)
    assert float(df_bench["ms"].iloc[0]) == pytest.approx(1.45)

    with pytest.raises(pa.errors.SchemaError):
        validate_benchmark_dataframe(
            pd.DataFrame(
                [
                    {
                        "method": "Bad",
                        "iae": -1.0,
                        "itae": 1.0,
                        "ise": 1.0,
                        "tv": 1.0,
                        "overshoot_pct": 0.0,
                        "ms": 1.2,
                    }
                ]
            )
        )


def test_subspace_identification_and_python_control_gang_of_4() -> None:
    """Tests PRBS excitation, SIPPY identification, and python-control Gang of 4."""
    u_prbs = generate_prbs_signal(n_samples=80, u_nominal=100.0, delta_plus=15.0, delta_minus=10.0)
    assert u_prbs.shape == (80,)
    assert np.all((u_prbs >= 0.0) & (u_prbs <= 300.0))

    t = np.arange(80) * 0.05
    foptd = FOPTDModel(k_p=-0.12, tau=0.8, theta=0.10)
    # Generate synthetic 2nd-order response to PRBS
    y = np.full(80, 344.16, dtype=np.float64)
    for k in range(1, 80):
        y[k] = 344.16 + 0.85 * (y[k - 1] - 344.16) - 0.02 * (u_prbs[k - 1] - 100.0)

    res_n4sid = identify_subspace_or_armax(
        u_prbs, y, method="N4SID", order=2, u_baseline=100.0, y_baseline=344.16
    )
    assert res_n4sid.rmse < 0.05
    assert res_n4sid.A is not None and res_n4sid.A.shape == (2, 2)

    comp = compare_foptd_vs_subspace(t, u_prbs, y, foptd, u_nominal=100.0, y_nominal=344.16)
    assert set(comp.keys()) == {"FOPTD", "N4SID", "MOESP", "ARMAX"}

    gains = PIDGains(kp=-12.0, ti=0.6, td=0.05)
    g4 = analyze_loop_margins_and_gang_of_4(foptd, gains, pade_order=3, n_freqs=100)
    assert g4["gm"] > 1.0
    assert g4["pm_deg"] > 20.0
    assert g4["ms_exact"] >= 1.0
    assert len(g4["mag_S"]) == 100


def test_mhe_estimator_and_conditioned_pinn_and_dpc() -> None:
    """Tests online MHE/EKF, Picard-Lindelöf PINN IC conditioning, Controlled NODE, and DPC."""
    estimator = AugmentedCstrStateEstimator(horizon_length=5)
    for _ in range(5):
        x_hat = estimator.step(u_prev=110.0, t_meas=343.5, t_j_meas=328.0, dt=0.05)
    assert x_hat.shape == (4,)
    assert 0.0 <= x_hat[0] <= 1.0
    assert 0.4 <= x_hat[3] <= 1.2

    # NMPC in output-feedback mode (full_state=None) using online MHE
    nmpc = CstrNmpcController(horizon_steps=4, t_step_min=0.05, solver_mode="sqp_rti")
    u_cmd, diag = nmpc.compute(setpoint=342.0, measurement=343.5, dt=0.05, full_state=None)
    assert 0.0 <= u_cmd <= 300.0
    assert "alpha_ua_hat" in diag

    # PINN exact initial condition verification: x_hat(t=0, q_j, x0) == x0
    pinn = CstrPhysicsInformedNet(hidden_dim=16)
    x0_custom = torch.tensor([[0.45, 360.0, 315.0], [0.20, 340.0, 305.0]], dtype=torch.float32)
    t0_and_u = torch.tensor([[0.0, 120.0], [0.0, 80.0]], dtype=torch.float32)
    pred_at_t0 = pinn(t0_and_u, x0=x0_custom)
    assert torch.allclose(pred_at_t0, x0_custom, atol=1e-6)

    # Controlled Neural ODE sensitivity to exogenous control u
    node = CstrNeuralOdePredictor(solver="rk4", hidden_dim=16)
    x0_node = torch.tensor([0.2, 345.0, 330.0], dtype=torch.float32)
    t_grid = torch.linspace(0.0, 0.5, 5)
    traj_low_u = node.forward_trajectory(x0_node, t_grid, u=50.0)
    traj_high_u = node.forward_trajectory(x0_node, t_grid, u=250.0)
    assert not torch.allclose(traj_low_u[-1], traj_high_u[-1])

    # NeuroMANCER DPC rollout with Van Heerden barrier
    dpc = NeuromancerDpcPolicy(hidden_dim=16)
    dpc_losses = dpc.compute_dpc_van_heerden_loss(
        x0=x0_custom,
        setpoint=torch.tensor([[342.0], [342.0]], dtype=torch.float32),
        horizon_steps=4,
    )
    assert dpc_losses["total_dpc_loss"].item() >= 0.0

    # NeuroPidController with DPC blend and bumpless transfer
    npid = NeuroPidController(
        base_gains=PIDGains(kp=-25.0, ti=0.5, td=0.03),
        use_dpc_blend=True,
        dpc_blend_weight=0.3,
    )
    npid.bumpless_transfer(target_u=135.0, current_error=-1.0)
    u_npid, _ = npid.compute(setpoint=343.0, measurement=344.0, dt=0.05)
    assert 0.0 <= u_npid <= 300.0


def test_pymoo_nsga3_and_salib_sobol_and_plot_helpers() -> None:
    """Tests pymoo NSGA-III, Hypervolume, SALib Sobol sensitivity, tueplots, and adjustText."""
    foptd = FOPTDModel(k_p=-0.12, tau=0.8, theta=0.10)
    front = optimize_pid_nsga3_pymoo(foptd, n_generations=3, pop_size=8, ms_threshold=1.8)
    assert len(front) >= 1
    hv = compute_hypervolume_pymoo(
        [ParetoPoint(iae=2.0, tv=50.0, ms=1.4, label="A")],
        ref_point=(10.0, 300.0, 2.0),
    )
    assert hv > 0.0

    sobol_res = run_sobol_global_sensitivity(
        eval_func=lambda p: (
            2.0 / p["alpha_ua"] + 0.5 * p["C_Af"],
            50.0 * p["e_over_r_scale"] + 0.1 * p["T_f"],
        ),
        n_base_samples=4,
    )
    assert len(sobol_res["iae_sobol"]["ST"]) == 4

    rc = get_tueplots_rcparams()
    assert rc["pdf.fonttype"] == 42

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    texts = apply_repulsive_annotations(ax, [(0.2, 0.2, "Pt1"), (0.21, 0.21, "Pt2")])
    assert len(texts) == 2
    plt.close(fig)
