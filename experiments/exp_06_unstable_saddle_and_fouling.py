# -*- coding: utf-8 -*-
"""ChERD campaign: open-loop unstable saddle, SISO vs cascade, and dynamic jacket fouling.

With the nominal feed (T_f = 350 K) the heat balance of the benchmark CSTR has a single,
stable root for every q_j in [0, 300] L/min and every UA, so no unstable operating point
exists there. Steady-state multiplicity appears when the feed is cooled; the campaign
therefore uses T_f = 320 K, where the middle (saddle) branch passes through T = 345 K.

Steps:
1. Steady-state branches (Van Heerden), saddle location and Jacobian spectrum.
2. SIMC for the unstable reduced model, k e^{-theta s} / (tau_u s - 1), versus a
   sequential-SIMC cascade (T -> T_j -> q_j), with and without static utility feedforward.
3. Shocks Delta T_jf = +10 K and Delta T_f = +5 K on the saddle.
4. Fouling d(UA)/dt = -kappa r_A (UA - UA_min) at the nominal point and at the saddle,
   time to valve saturation and to loss of thermal regulation.

Outputs: tables/figures/numbers.tex in the ChERD paper folder; CSV mirrors in results/cherd/.
"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from src.classical_control.cascade_controller import CascadePIDController, CascadePIDGains
from src.classical_control.foptd import FOPTDModel, identify_foptd
from src.classical_control.pid_controller import PIDController, PIDGains
from src.classical_control.tuning_analytical import TuningRule, tune_analytical
from src.evaluation.plot_styles import (
    IEEE_DOUBLE_COL_WIDTH_INCHES,
    IEEE_SINGLE_COL_WIDTH_INCHES,
    setup_ieee_style,
)
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRParameters, CSTRPlant, CSTRState
from src.sim_core.schemas import validate_trajectory_dataframe

logger = logging.getLogger("exp_06_saddle_fouling")

PAPER_DIR = PROJECT_ROOT / "Artigos_Rascunhos" / "03_Chemical_Engineering_Research_Design"
RESULTS_DIR = PROJECT_ROOT / "results" / "cherd"

DT = 0.02  # control period [min]
LIMITS = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)
Q_J_NOMINAL = 100.0
T_F_SADDLE = 320.0  # cooled feed that creates steady-state multiplicity [K]
T_SADDLE = 345.0
TAU_C_SISO_SADDLE = 0.10  # inside the PI stabilizing interval (see tau_c sweep)
KAPPA_FOUL = 0.10  # fouling rate constant [L/mol]
UA_MIN_FRAC = 0.30  # asymptotic UA_min / UA_0
RUNAWAY_BAND = 5.0  # loss of regulation: T - T_sp above this [K]
SHOCK_TIME = 2.0
SHOCK_HORIZON = 60.0
FOULING_HORIZON = 80.0
ARCH_LABELS = {
    "siso": "SISO SIMC",
    "cascade": "Cascade",
    "cascade_ff": "Cascade + FF",
}
ARCH_COLORS = {"siso": "#D95F02", "cascade": "#1B9E77", "cascade_ff": "#7570B3"}


@dataclass(frozen=True)
class OperatingPoint:
    """Plant, equilibrium and coolant flow defining one operating point."""

    name: str
    plant: CSTRPlant
    ss: CSTRState
    q_j: float


@dataclass(frozen=True)
class ControllerDesign:
    """Gains of the SISO and cascade loops plus the models they were derived from."""

    siso: PIDGains
    slave: PIDGains
    master: PIDGains
    siso_model: tuple[float, float, float]  # (k, tau, theta); tau < 0 flags tau_u
    slave_model: FOPTDModel
    master_model: FOPTDModel


# %% [Steady states and heat balance]
def _heat_balance(p: CSTRParameters, T: float, q_j: float) -> tuple[float, float, float]:
    """C_A(T), T_j(T) from the mass and jacket balances, and the reactor energy residual."""
    k = p.k_0 * np.exp(-p.E_over_R / T)
    c_a = p.q * p.C_Af / (p.q + p.V * k)
    a = p.UA / p.rho_j_cp_j
    t_j = (q_j * p.T_jf + a * T) / (q_j + a)
    residual = (
        p.q / p.V * (p.T_f - T) - p.delta_H / p.rho_cp * k * c_a
        - p.UA / (p.V * p.rho_cp) * (T - t_j)
    )
    return c_a, t_j, residual


def heat_generation(p: CSTRParameters, T: np.ndarray) -> np.ndarray:
    """Q_g(T) = (-dH) V r_A(C_A(T), T) on the steady mass balance [cal/min]."""
    k = p.k_0 * np.exp(-p.E_over_R / T)
    return -p.delta_H * p.V * k * p.q * p.C_Af / (p.q + p.V * k)


def heat_removal(p: CSTRParameters, T: np.ndarray, q_j: float) -> np.ndarray:
    """Q_r(T, q_j) = q rho c_p (T - T_f) + UA (T - T_j(q_j, T)) [cal/min]."""
    a = p.UA / p.rho_j_cp_j
    t_j = (q_j * p.T_jf + a * T) / (q_j + a)
    return p.q * p.rho_cp * (T - p.T_f) + p.UA * (T - t_j)


def steady_state_branches(
    plant: CSTRPlant, q_j: float, t_grid: Optional[np.ndarray] = None
) -> list[tuple[CSTRState, float]]:
    """All equilibria at a given q_j and the largest real part of each Jacobian spectrum."""
    grid = np.linspace(290.0, 470.0, 3601) if t_grid is None else t_grid
    res = np.array([_heat_balance(plant.params, T, q_j)[2] for T in grid])
    branches = []
    for i in np.where(np.diff(np.sign(res)) != 0)[0]:
        T = brentq(lambda x: _heat_balance(plant.params, x, q_j)[2], grid[i], grid[i + 1])
        c_a, t_j, _ = _heat_balance(plant.params, T, q_j)
        ss = CSTRState(C_A=c_a, T=T, T_j=t_j)
        eig = np.linalg.eigvals(plant.linearize(ss, q_j)[0])
        branches.append((ss, float(eig.real.max())))
    return branches


def nominal_point() -> OperatingPoint:
    """Benchmark point: T_f = 350 K, q_j = 100 L/min."""
    plant = CSTRPlant()
    return OperatingPoint("nominal", plant, plant.find_steady_state(Q_J_NOMINAL), Q_J_NOMINAL)


def find_saddle_point(
    t_target: float = T_SADDLE, t_f: float = T_F_SADDLE, ua_frac: float = 1.0,
    t_jf: float = CSTRParameters().T_jf,
) -> OperatingPoint:
    """Coolant flow that places an equilibrium at t_target, confirmed by root finding.

    ua_frac scales UA (frozen fouling level); t_jf moves the coolant supply temperature.

    Raises:
        ValueError: If the equilibrium is not open-loop unstable or q_j leaves the valve range.
    """
    plant = CSTRPlant(CSTRParameters(T_f=t_f, UA=CSTRParameters().UA * ua_frac, T_jf=t_jf))
    p = plant.params
    k = p.k_0 * np.exp(-p.E_over_R / t_target)
    c_a = p.q * p.C_Af / (p.q + p.V * k)
    # Reactor energy balance gives T_j; jacket balance then gives q_j
    t_j = t_target - p.V * p.rho_cp / p.UA * (
        p.q / p.V * (p.T_f - t_target) - p.delta_H / p.rho_cp * k * c_a
    )
    q_j = p.UA / p.rho_j_cp_j * (t_target - t_j) / (t_j - p.T_jf)
    if not LIMITS.u_min < q_j < LIMITS.u_max:
        raise ValueError(f"Equilibrium at {t_target} K needs q_j = {q_j:.2f} L/min")
    ss = plant.find_steady_state(q_j, initial_guess=CSTRState(c_a, t_target, t_j))
    eig = np.linalg.eigvals(plant.linearize(ss, q_j)[0])
    if np.sum(eig.real > 0.0) != 1:
        raise ValueError(f"Equilibrium at {t_target} K is not a saddle: eigenvalues {eig}")
    return OperatingPoint("saddle", plant, ss, float(q_j))


def critical_ua_fraction(op: OperatingPoint) -> float:
    """UA/UA_0 at which holding T_ss needs exactly q_j = u_max (closed form).

    With T and C_A fixed, the heat to be removed through the wall, Q_load, does not depend
    on UA; T_j = T - Q_load/UA and q_j = Q_load / (rho_j c_pj (T_j - T_jf)).
    """
    p, ss = op.plant.params, op.ss
    q_load = p.V * p.rho_cp * (
        p.q / p.V * (p.T_f - ss.T) + op.plant.reaction_rate(ss.C_A, ss.T) * -p.delta_H / p.rho_cp
    )
    return q_load / (ss.T - p.T_jf - q_load / (p.rho_j_cp_j * LIMITS.u_max)) / p.UA


def predicted_saturation_time(op: OperatingPoint, kappa: float, ua_min_frac: float) -> float:
    """Quasi-steady time at which UA(t) = UA_min + (UA_0 - UA_min) e^{-kappa r_A t} hits UA_crit."""
    f_crit = critical_ua_fraction(op)
    if f_crit <= ua_min_frac:
        return float("inf")
    r_a = op.plant.reaction_rate(op.ss.C_A, op.ss.T)
    return float(np.log((1.0 - ua_min_frac) / (f_crit - ua_min_frac)) / (kappa * r_a))


# %% [Controller design]
def unstable_model(op: OperatingPoint) -> tuple[float, float, float]:
    """Reduce G(s) = C(sI - A)^{-1}B to k e^{-theta s} / (tau_u s - 1).

    G(s) = b_3 a_23 (s - a_11) / prod(s - p_i): the zero T_0 = -1/a_11 is merged with the
    slower stable lag, (T_0 s + 1)/(tau_a s + 1) ~ 1/((tau_a - T_0) s + 1), and with no stable
    dominant lag left to absorb it, every remaining lag plus half a sample goes into theta.
    """
    A, B = op.plant.linearize(op.ss, op.q_j)
    eig = np.linalg.eigvals(A).real
    tau_u = 1.0 / eig.max()
    tau_a, tau_b = sorted((-1.0 / e for e in eig if e < 0.0), reverse=True)
    t_0 = -1.0 / A[0, 0]
    if tau_a <= t_0:
        raise ValueError(f"Lead T_0 = {t_0:.3f} exceeds the slower stable lag {tau_a:.3f}")
    C = np.array([[0.0, 1.0, 0.0]])
    g0 = float((C @ np.linalg.solve(-A, B))[0, 0])
    return -g0, float(tau_u), float(tau_a - t_0 + tau_b + DT / 2.0)


def simc_unstable_pi(k: float, tau_u: float, theta: float, tau_c: float) -> PIDGains:
    """SIMC PI for k e^{-theta s}/(tau_u s - 1), integrating approximation k' = k/tau_u.

    K_c = tau_u / (k (tau_c + theta)), tau_I = 4 (tau_c + theta). |K_c k| > 1, the minimum gain
    that moves the unstable pole, is equivalent to tau_c < tau_u - theta.

    Raises:
        ValueError: If tau_c >= tau_u - theta.
    """
    if tau_c >= tau_u - theta:
        raise ValueError(f"tau_c = {tau_c} violates tau_c < tau_u - theta = {tau_u - theta:.4f}")
    return PIDGains(kp=tau_u / (k * (tau_c + theta)), ti=4.0 * (tau_c + theta))


def _pi_loop(
    A: np.ndarray, B: np.ndarray, C: np.ndarray, gains: PIDGains
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Closed loop of (A, B, C) under continuous PI from reference r to C x."""
    a_cl = np.block([[A - gains.kp * B @ C, gains.kp / gains.ti * B], [-C, np.zeros((1, 1))]])
    b_cl = np.vstack([gains.kp * B, np.ones((1, 1))])
    return a_cl, b_cl, np.hstack([C, np.zeros((1, 1))])


def _inner_loop(op: OperatingPoint, slave: PIDGains) -> tuple[np.ndarray, ...]:
    """Linear map T_j,sp -> T with the slave PI closed (output row selects T)."""
    A, B = op.plant.linearize(op.ss, op.q_j)
    a_i, b_i, _ = _pi_loop(A, B, np.array([[0.0, 0.0, 1.0]]), slave)
    return a_i, b_i, np.array([[0.0, 1.0, 0.0, 0.0]])


def closed_loop_abscissa(op: OperatingPoint, design: ControllerDesign, arch: str) -> float:
    """Largest real part of the linear closed-loop spectrum (continuous PI, exact Jacobian)."""
    if arch == "siso":
        A, B = op.plant.linearize(op.ss, op.q_j)
        a_cl = _pi_loop(A, B, np.array([[0.0, 1.0, 0.0]]), design.siso)[0]
    else:
        a_i, b_i, c_i = _inner_loop(op, design.slave)
        a_cl = _pi_loop(a_i, b_i, c_i, design.master)[0]
    return float(np.linalg.eigvals(a_cl).real.max())


def stability_boundary(design: ControllerDesign, arch: str, f_low: float) -> float:
    """UA/UA_0 below which the fixed-gain loop no longer stabilizes the 345 K saddle.

    Each frozen UA has its own equilibrium q_j; the gains stay those designed at UA_0.
    """
    return float(brentq(
        lambda f: closed_loop_abscissa(find_saddle_point(ua_frac=f), design, arch), f_low, 1.0
    ))


def p_only_abscissa(op: OperatingPoint, kp: float) -> float:
    """Largest real part of the linear spectrum under proportional feedback T -> q_j."""
    A, B = op.plant.linearize(op.ss, op.q_j)
    return float(np.linalg.eigvals(A - kp * B @ np.array([[0.0, 1.0, 0.0]])).real.max())


def design_controllers(op: OperatingPoint, tau_c_siso: Optional[float] = None) -> ControllerDesign:
    """SISO SIMC and sequential-SIMC cascade for one operating point.

    SISO: unstable reduced model at a saddle, open-loop reaction curve otherwise
    (tau_c = theta when tau_c_siso is None). Slave: jacket row of the Jacobian,
    tau_c2 = tau_2. Master: FOPTD fitted to the reaction curve of the linear closed
    inner loop, tau_c1 = theta_1.
    """
    A, B = op.plant.linearize(op.ss, op.q_j)
    if np.linalg.eigvals(A).real.max() > 0.0:
        k, tau_u, theta = unstable_model(op)
        siso = simc_unstable_pi(k, tau_u, theta, TAU_C_SISO_SADDLE if tau_c_siso is None else tau_c_siso)
        siso_model = (k, -tau_u, theta)
    else:
        from experiments import exp_02_robustness_campaign as exp02

        foptd = exp02.identify_nominal_foptd(op.plant, op.ss, op.q_j)
        siso = tune_analytical(
            foptd, TuningRule.SKOGESTAD_SIMC_PI,
            tau_c=foptd.theta if tau_c_siso is None else tau_c_siso,
        )
        siso_model = (foptd.k_p, foptd.tau, foptd.theta)

    slave_model = FOPTDModel(k_p=float(-B[2, 0] / A[2, 2]), tau=float(-1.0 / A[2, 2]), theta=DT)
    slave = tune_analytical(slave_model, TuningRule.SKOGESTAD_SIMC_PI, tau_c=slave_model.tau)

    a_i, b_i, c_i = _inner_loop(op, slave)
    t = np.arange(0.0, 20.0 + 1e-9, DT)
    _, y = signal.step(signal.StateSpace(a_i, b_i, c_i, np.zeros((1, 1))), T=t)
    master_model, rmse = identify_foptd(t, y, delta_u=1.0, y0=0.0)
    master = tune_analytical(master_model, TuningRule.SKOGESTAD_SIMC_PI, tau_c=master_model.theta)
    logger.info(
        "[%s] SISO %s | slave %s | master %s (FOPTD %s, RMSE %.3f K)",
        op.name, siso, slave, master, master_model, rmse,
    )
    return ControllerDesign(siso, slave, master, siso_model, slave_model, master_model)


def inner_loop_gains(op: OperatingPoint) -> dict[str, float]:
    """Master-loop static gain: open-loop ratio G(0)/K_2 versus exact sub-block A_12."""
    A, B = op.plant.linearize(op.ss, op.q_j)
    g0 = float((np.array([[0.0, 1.0, 0.0]]) @ np.linalg.solve(-A, B))[0, 0])
    k2 = float(-B[2, 0] / A[2, 2])
    a12 = A[:2, :2]
    k1 = float((np.array([[0.0, 1.0]]) @ np.linalg.solve(-a12, A[:2, 2:3]))[0, 0])
    return {
        "G0": g0, "K2": k2, "ratio": g0 / k2, "K1": k1,
        "det": float(np.linalg.det(a12)), "trace": float(np.trace(a12)),
        "a12_abscissa": float(np.linalg.eigvals(a12).real.max()),
    }


def feedforward_flow(op: OperatingPoint, t_jf: float) -> float:
    """Static utility feedforward: q_j that keeps the nominal wall heat flow when T_jf moves."""
    p, ss = op.plant.params, op.ss
    den = ss.T_j - t_jf
    if den <= 0.0:
        return LIMITS.u_max  # coolant warmer than the jacket target: no flow can cool
    return float(min(LIMITS.u_max, p.UA / p.rho_j_cp_j * (ss.T - ss.T_j) / den))


# %% [Closed-loop simulation with fouling state]
def _augmented_rhs(
    plant: CSTRPlant, y: np.ndarray, q_j: float, dist: dict[str, float],
    kappa: float, ua_min: float,
) -> np.ndarray:
    """[C_A, T, T_j, UA]: plant balances with UA from the state, plus the fouling law."""
    dx = plant.derivatives(0.0, y[:3], q_j, disturbances={**dist, "UA": y[3]})
    d_ua = -kappa * plant.reaction_rate(y[0], y[1]) * (y[3] - ua_min)
    return np.append(dx, d_ua)


def _make_controller(
    op: OperatingPoint, design: Optional[ControllerDesign], arch: str
) -> Callable[[np.ndarray, float], tuple[float, float]]:
    """Return step(x, T_jf measured) -> (q_j, T_j,sp)."""
    ss = op.ss
    if arch == "open_loop":
        return lambda x, t_jf: (op.q_j, float("nan"))
    if design is None:
        raise ValueError(f"Architecture {arch} needs a ControllerDesign")
    if arch == "siso":
        pid = PIDController(gains=design.siso, actuator_limits=LIMITS, u_bias=op.q_j)
        pid.reset(initial_measurement=ss.T, initial_u=op.q_j)
        return lambda x, t_jf: (pid.compute(setpoint=ss.T, measurement=x[1], dt=DT)[0], float("nan"))
    if arch not in ("cascade", "cascade_ff"):
        raise ValueError(f"Unknown architecture {arch}")
    casc = CascadePIDController(
        gains=CascadePIDGains(master_gains=design.master, slave_gains=design.slave),
        actuator_limits=LIMITS, u_bias=op.q_j, t_j_bias=ss.T_j,
    )
    casc.reset(initial_t=ss.T, initial_tj=ss.T_j, initial_u=op.q_j)

    def step(x: np.ndarray, t_jf: float) -> tuple[float, float]:
        if arch == "cascade_ff":
            casc.slave_controller.u_bias = feedforward_flow(op, t_jf)
        q_j, diag = casc.compute(t_sp=ss.T, t_pv=x[1], tj_pv=x[2], dt=DT)
        return q_j, diag["tj_sp"]

    return step


def simulate(
    op: OperatingPoint,
    design: Optional[ControllerDesign],
    arch: str,
    t_end: float,
    disturbance: Optional[Callable[[float], dict[str, float]]] = None,
    kappa: float = 0.0,
    ua_min_frac: float = UA_MIN_FRAC,
    x0_offset_T: float = 0.0,
) -> pd.DataFrame:
    """Sampled-data simulation (ZOH, DT) of the plant with the fouling state UA.

    Returns:
        Trajectory validated by CstrTrajectorySchema, plus columns UA and T_j_sp.
    """
    plant = op.plant
    ctrl = _make_controller(op, design, arch)
    ua_min = ua_min_frac * plant.params.UA
    x = np.array([op.ss.C_A, op.ss.T + x0_offset_T, op.ss.T_j, plant.params.UA])
    t_grid = np.arange(0.0, t_end + 1e-9, DT)
    xs, us, sps = np.empty((len(t_grid), 4)), np.empty(len(t_grid)), np.empty(len(t_grid))
    for i, t in enumerate(t_grid):
        dist = disturbance(t) if disturbance else {}
        q_j, tj_sp = ctrl(x, dist.get("T_jf", plant.params.T_jf))
        xs[i], us[i], sps[i] = x, q_j, tj_sp
        sol = solve_ivp(
            lambda _t, y: _augmented_rhs(plant, y, q_j, dist, kappa, ua_min),
            (t, t + DT), x, method="RK45", rtol=1e-8, atol=1e-10,
        )
        if not sol.success:
            raise RuntimeError(f"ODE integration failed at t = {t:.2f} min: {sol.message}")
        x = sol.y[:, -1]
    df = validate_trajectory_dataframe(t_grid, xs[:, :3], us, np.full(len(t_grid), op.ss.T))
    return df.assign(UA=xs[:, 3], T_j_sp=sps)


def first_time(df: pd.DataFrame, mask: pd.Series) -> float:
    """First time at which mask holds, NaN if never."""
    hits = df.loc[mask, "t"]
    return float(hits.iloc[0]) if len(hits) else float("nan")


def shock_metrics(df: pd.DataFrame, t_shock: float) -> dict[str, float]:
    """IAE, peak deviation, valve travel and late peak-to-peak T after t_shock."""
    post = df[df["t"] >= t_shock]
    err = (post["T"] - post["setpoint"]).abs()
    return {
        "IAE": float(err.sum() * DT),
        "peak": float(err.max()),
        "TV": float(post["q_j"].diff().abs().sum()),
        "q_max": float(post["q_j"].max()),
        # peak-to-peak of T over the last 20 min: separates settling from a limit cycle
        "p2p": float(np.ptp(df.loc[df["t"] >= df["t"].iloc[-1] - 20.0, "T"])),
    }


# %% [Export helpers]
def _fmt(x: float, nd: int) -> str:
    return "--" if not np.isfinite(x) else f"{x:.{nd}f}"


def _export(rows: list[dict[str, str]], name: str, caption: str, label: str, wide: bool) -> None:
    from experiments import exp_02_robustness_campaign as exp02

    exp02.RESULTS_DIR = RESULTS_DIR
    exp02.TABLE_FLOAT_ENV = "table*" if wide else "table"
    exp02.export_latex_table(rows, PAPER_DIR / "tables" / f"{name}.tex", caption, label)


def _save(fig: plt.Figure, name: str) -> None:
    (PAPER_DIR / "figures").mkdir(parents=True, exist_ok=True)
    fig.savefig(PAPER_DIR / "figures" / f"{name}.pdf")
    fig.savefig(RESULTS_DIR / f"{name}.png", dpi=200)
    plt.close(fig)


def write_numbers(numbers: dict[str, str]) -> None:
    """Every number quoted in the prose, as LaTeX macros (and a CSV mirror)."""
    lines = [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in numbers.items()]
    (PAPER_DIR / "tables" / "numbers.tex").write_text(
        "% Generated by experiments/exp_06_unstable_saddle_and_fouling.py\n" + "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    pd.DataFrame({"macro": list(numbers), "value": list(numbers.values())}).to_csv(
        RESULTS_DIR / "numbers.csv", index=False
    )


# %% [Campaign]
def run_campaign() -> None:
    """Run every scenario, write tables, figures, macros and CSV mirrors."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (PAPER_DIR / "tables").mkdir(parents=True, exist_ok=True)
    setup_ieee_style()
    num: dict[str, str] = {}

    nom, sad = nominal_point(), find_saddle_point()
    p0 = nom.plant.params
    num.update(
        TfNom=_fmt(p0.T_f, 0), TfSad=_fmt(sad.plant.params.T_f, 0), Tjf=_fmt(p0.T_jf, 0),
        umax=_fmt(LIMITS.u_max, 0), slew=_fmt(LIMITS.max_slew_rate, 0), dtCtrl=_fmt(DT, 2),
        qjNom=_fmt(nom.q_j, 0), kappaFoul=_fmt(KAPPA_FOUL, 2), uaMin=_fmt(100 * UA_MIN_FRAC, 0),
        bandRun=_fmt(RUNAWAY_BAND, 0), tShock=_fmt(SHOCK_TIME, 0), tauCsiso=_fmt(TAU_C_SISO_SADDLE, 2),
        horizonShock=_fmt(SHOCK_HORIZON, 0), horizonFoul=_fmt(FOULING_HORIZON, 0),
    )

    # --- 1. Branches and operating points -------------------------------------------------
    points = {"nominal": nom, "saddle": sad}
    op_rows = []
    for key, op in points.items():
        A, _ = op.plant.linearize(op.ss, op.q_j)
        eig = np.sort(np.linalg.eigvals(A).real)[::-1]
        branches = steady_state_branches(op.plant, op.q_j)
        f_crit = critical_ua_fraction(op)
        r_a = op.plant.reaction_rate(op.ss.C_A, op.ss.T)
        tag = "Nom" if key == "nominal" else "Sad"
        num.update({
            f"T{tag}": _fmt(op.ss.T, 2), f"Ca{tag}": _fmt(op.ss.C_A, 4), f"Tj{tag}": _fmt(op.ss.T_j, 2),
            f"qj{tag}": _fmt(op.q_j, 2), f"lamA{tag}": _fmt(eig[0], 4), f"lamB{tag}": _fmt(eig[1], 4),
            f"lamC{tag}": _fmt(eig[2], 4), f"fcrit{tag}": _fmt(100 * f_crit, 1),
            f"rA{tag}": _fmt(r_a, 4), f"nBranch{tag}": str(len(branches)),
            f"conv{tag}": _fmt(100 * (1 - op.ss.C_A / op.plant.params.C_Af), 1),
        })
        op_rows.append({
            "Point": "Nominal" if key == "nominal" else "Saddle",
            "$T_f$ (K)": _fmt(op.plant.params.T_f, 0),
            "$q_j$ (L/min)": _fmt(op.q_j, 2),
            "$T$ (K)": _fmt(op.ss.T, 2),
            "$C_A$ (mol/L)": _fmt(op.ss.C_A, 4),
            "$T_j$ (K)": _fmt(op.ss.T_j, 2),
            "$\\lambda_{1,2,3}$ (min$^{-1}$)": ", ".join(_fmt(e, 3) for e in eig),
            "Equilibria": str(len(branches)),
            "$UA_{\\mathrm{crit}}/UA_0$ (\\%)": _fmt(100 * f_crit, 1),
        })
    low, mid, high = steady_state_branches(sad.plant, sad.q_j)
    num.update(
        TlowSad=_fmt(low[0].T, 2), ThighSad=_fmt(high[0].T, 2), lamLow=_fmt(low[1], 3),
        lamHigh=_fmt(high[1], 3), tauU=_fmt(1.0 / mid[1], 3),
    )
    _export(
        op_rows, "cherd_operating_points",
        "Operating points. Equilibria: number of steady states at the same $q_j$; "
        "$UA_{\\mathrm{crit}}$: heat-transfer capacity below which holding $T$ needs "
        "$q_j > u_{\\max}$ (Eq.~\\eqref{eq:ua_crit}).",
        "tab:operating_points", wide=True,
    )

    # Branch locus T_ss(q_j) for both feeds
    q_grid = np.concatenate([np.linspace(1.0, 20.0, 40), np.linspace(20.5, 300.0, 160)])
    locus = []
    for key, op in points.items():
        for q in q_grid:
            for ss, abscissa in steady_state_branches(op.plant, float(q)):
                locus.append({"point": key, "q_j": q, "T": ss.T, "C_A": ss.C_A, "abscissa": abscissa})
    locus_df = pd.DataFrame(locus)
    locus_df.to_csv(RESULTS_DIR / "steady_state_locus.csv", index=False)
    sad_multi = locus_df[(locus_df["point"] == "saddle")].groupby("q_j").size()
    q_multi = sad_multi[sad_multi == 3].index
    num.update(qMultiLo=_fmt(q_multi.min(), 1), qMultiHi=_fmt(q_multi.max(), 1))
    nom_unstable = int((locus_df[locus_df["point"] == "nominal"]["abscissa"] > 0).sum())
    num.update(nNomUnstable=str(nom_unstable))

    # Thermodynamic limit at the nominal point
    T_sp = nom.ss.T
    for frac, tag in ((1.0, "Full"), (0.60, "Sixty"), (0.55, "FiftyFive")):
        p_f = CSTRParameters(UA=p0.UA * frac)
        a = p_f.UA / p_f.rho_j_cp_j
        t_j_min = (LIMITS.u_max * p_f.T_jf + a * T_sp) / (LIMITS.u_max + a)
        q_r_max = p_f.q * p_f.rho_cp * (T_sp - p_f.T_f) + p_f.UA * (T_sp - t_j_min)
        num[f"QrMax{tag}"] = _fmt(q_r_max / 1e6, 3)
        num[f"TjMin{tag}"] = _fmt(t_j_min, 2)
    num["QgNom"] = _fmt(float(heat_generation(p0, np.array([T_sp]))[0]) / 1e6, 3)

    # Figure 1: Van Heerden diagram, branch locus, thermodynamic limit
    fig, axes = plt.subplots(1, 3, figsize=(IEEE_DOUBLE_COL_WIDTH_INCHES, 2.5))
    T_ax = np.linspace(300.0, 450.0, 600)
    ps = sad.plant.params
    axes[0].plot(T_ax, heat_generation(ps, T_ax) / 1e6, "k-", lw=1.4, label="$Q_g$")
    axes[0].plot(T_ax, heat_removal(ps, T_ax, sad.q_j) / 1e6, color="#1B9E77", lw=1.4,
                 label=f"$Q_r$, $q_j={sad.q_j:.1f}$")
    for ss, ab in (low, mid, high):
        axes[0].plot(ss.T, heat_generation(ps, np.array([ss.T]))[0] / 1e6, "o",
                     mfc="white" if ab > 0 else "k", mec="k", ms=5)
    axes[0].set(xlabel="$T$ (K)", ylabel="$Q$ (Mcal/min)", title=f"(a) $T_f={ps.T_f:.0f}$ K")
    axes[0].legend(fontsize=7, loc="upper left")
    for key, color in (("nominal", "#555555"), ("saddle", "#D95F02")):
        d = locus_df[locus_df["point"] == key]
        st, un = d[d["abscissa"] < 0], d[d["abscissa"] > 0]
        axes[1].plot(st["q_j"], st["T"], ".", color=color, ms=2,
                     label=f"$T_f={points[key].plant.params.T_f:.0f}$ K")
        axes[1].plot(un["q_j"], un["T"], "x", color=color, ms=3)
    axes[1].plot(sad.q_j, sad.ss.T, "o", mfc="white", mec="k", ms=5)
    axes[1].set(xlabel="$q_j$ (L/min)", ylabel="$T_{ss}$ (K)", xscale="log",
                title="(b) branches (x: unstable)")
    axes[1].legend(fontsize=7, loc="upper right")
    T_n = np.linspace(380.0, 420.0, 300)
    axes[2].plot(T_n, heat_generation(p0, T_n) / 1e6, "k-", lw=1.4, label="$Q_g$")
    for frac, ls in ((1.0, "-"), (0.60, "--"), (0.55, ":")):
        p_f = CSTRParameters(UA=p0.UA * frac)
        axes[2].plot(T_n, heat_removal(p_f, T_n, LIMITS.u_max) / 1e6, ls, color="#1B9E77",
                     lw=1.3, label=f"$Q_{{r,\\max}}$, {frac * 100:.0f}% $UA$")
    axes[2].axvline(T_sp, color="gray", ls=":", lw=1.0)
    axes[2].set(xlabel="$T$ (K)", ylabel="$Q$ (Mcal/min)", title="(c) $T_f=350$ K, $q_j=u_{\\max}$")
    axes[2].legend(fontsize=6.5, loc="upper left")
    fig.tight_layout()
    _save(fig, "fig1_van_heerden")

    # Figure 2: open-loop phase portrait at the saddle q_j
    fig, ax = plt.subplots(figsize=(IEEE_SINGLE_COL_WIDTH_INCHES, 2.8))
    portrait = []
    for c0 in np.linspace(0.1, 0.95, 6):
        for T0 in np.linspace(320.0, 375.0, 6):
            sol = solve_ivp(lambda _t, y: sad.plant.derivatives(0.0, y, sad.q_j), (0.0, 20.0),
                            [c0, T0, sad.ss.T_j], method="RK45", rtol=1e-8, atol=1e-10,
                            t_eval=np.linspace(0.0, 20.0, 400))
            if not sol.success:
                raise RuntimeError(sol.message)
            ends_high = sol.y[1, -1] > sad.ss.T
            ax.plot(sol.y[0], sol.y[1], lw=0.7, color="#D95F02" if ends_high else "#1B9E77")
            portrait.append({"C_A0": c0, "T0": T0, "T_end": sol.y[1, -1]})
    for ss, ab in (low, mid, high):
        ax.plot(ss.C_A, ss.T, "o", mfc="white" if ab > 0 else "k", mec="k", ms=6, zorder=5)
    ax.set(xlabel="$C_A$ (mol/L)", ylabel="$T$ (K)")
    fig.tight_layout()
    _save(fig, "fig2_phase_portrait")
    portrait_df = pd.DataFrame(portrait)
    portrait_df.to_csv(RESULTS_DIR / "phase_portrait_endpoints.csv", index=False)
    num["nPortrait"] = str(len(portrait_df))
    num["nIgnite"] = str(int((portrait_df["T_end"] > sad.ss.T).sum()))

    # --- 2. Controller design ------------------------------------------------------------
    k, tau_u, theta = unstable_model(sad)
    A_s, B_s = sad.plant.linearize(sad.ss, sad.q_j)
    num.update(
        kU=_fmt(k, 4), tauUmodel=_fmt(tau_u, 3), thetaU=_fmt(theta, 3), boundU=_fmt(tau_u - theta, 3),
        Tzero=_fmt(-1.0 / A_s[0, 0], 3),
    )
    sweep_rows = []
    tau_c_values = [0.05, TAU_C_SISO_SADDLE, 0.20, 0.30, 0.50, round(theta, 3)]
    for tc in tau_c_values:
        g = simc_unstable_pi(k, tau_u, theta, tc)
        d = ControllerDesign(g, g, g, (k, -tau_u, theta), FOPTDModel(1, 1, 0), FOPTDModel(1, 1, 0))
        sweep_rows.append({
            "$\\tau_c$ (min)": _fmt(tc, 3),
            "$K_c$ (L/(min K))": _fmt(g.kp, 3),
            "$\\tau_I$ (min)": _fmt(g.ti, 3),
            "$|K_c k|$": _fmt(abs(g.kp * k), 3),
            "$\\max\\Re\\lambda$, P": _fmt(p_only_abscissa(sad, g.kp), 3),
            "$\\max\\Re\\lambda$, PI": _fmt(closed_loop_abscissa(sad, d, "siso"), 3),
        })

    def pi_abscissa(tc: float) -> float:
        g = simc_unstable_pi(k, tau_u, theta, tc)
        d = ControllerDesign(g, g, g, (k, -tau_u, theta), FOPTDModel(1, 1, 0), FOPTDModel(1, 1, 0))
        return closed_loop_abscissa(sad, d, "siso")

    tc_max_pi = brentq(pi_abscissa, 0.01, tau_u - theta - 1e-6)
    # k = -G(0) of the full model, so P action crosses the imaginary axis exactly at |K_c k| = 1
    if abs(p_only_abscissa(sad, 1.0 / k)) > 1e-8:
        raise RuntimeError("P-only boundary is not at |K_c k| = 1")
    num.update(tcMaxPI=_fmt(tc_max_pi, 3))
    _export(
        sweep_rows, "cherd_simc_sweep",
        "SIMC PI for the unstable reduced model at the saddle: spectral abscissa of the "
        "linearized closed loop for proportional-only (P) and PI action. The last row is the "
        "default SIMC choice $\\tau_c=\\theta$.",
        "tab:simc_sweep", wide=True,
    )

    designs = {key: design_controllers(op) for key, op in points.items()}
    ds = designs["saddle"]
    num.update(
        KcSiso=_fmt(ds.siso.kp, 3), TiSiso=_fmt(ds.siso.ti, 3),
        Ktwo=_fmt(ds.slave_model.k_p, 4), tauTwo=_fmt(ds.slave_model.tau, 4),
        KcSlave=_fmt(ds.slave.kp, 3), TiSlave=_fmt(ds.slave.ti, 4),
        KoneFit=_fmt(ds.master_model.k_p, 3), tauOneFit=_fmt(ds.master_model.tau, 3),
        thetaOneFit=_fmt(ds.master_model.theta, 3), KcMaster=_fmt(ds.master.kp, 3),
        TiMaster=_fmt(ds.master.ti, 3),
        absSiso=_fmt(closed_loop_abscissa(sad, ds, "siso"), 3),
        absCasc=_fmt(closed_loop_abscissa(sad, ds, "cascade"), 3),
        absInner=_fmt(float(np.linalg.eigvals(_inner_loop(sad, ds.slave)[0]).real.max()), 3),
        ffSad=_fmt(feedforward_flow(sad, p0.T_jf + 10.0), 2),
    )
    gain_rows = []
    for key, op in points.items():
        g = inner_loop_gains(op)
        tag = "Nom" if key == "nominal" else "Sad"
        err = 100.0 * (g["ratio"] - g["K1"]) / g["K1"]
        num.update({
            f"Gzero{tag}": _fmt(g["G0"], 4), f"Ktwo{tag}": _fmt(g["K2"], 4),
            f"ratio{tag}": _fmt(g["ratio"], 3), f"Kone{tag}": _fmt(g["K1"], 3),
            f"det{tag}": _fmt(g["det"], 3), f"trace{tag}": _fmt(g["trace"], 3),
            f"absA{tag}": _fmt(g["a12_abscissa"], 3), f"gainErr{tag}": _fmt(err, 1),
        })
        gain_rows.append({
            "Point": "Nominal" if key == "nominal" else "Saddle",
            "$G(0)$ (K/(L/min))": _fmt(g["G0"], 4),
            "$K_2$ (K/(L/min))": _fmt(g["K2"], 4),
            "$G(0)/K_2$ (K/K)": _fmt(g["ratio"], 3),
            "$K_{1}$ exact (K/K)": _fmt(g["K1"], 3),
            "Error (\\%)": _fmt(err, 1),
            "$\\max\\Re\\lambda(\\mathbf{A}_{12})$": _fmt(g["a12_abscissa"], 3),
        })
    _export(
        gain_rows, "cherd_inner_loop_gain",
        "Static gain seen by the master loop: open-loop ratio approximation versus the exact "
        "closed-inner-loop sub-block $\\mathbf{A}_{12}$ (Eq.~\\eqref{eq:k1_exact}).",
        "tab:inner_gain", wide=True,
    )

    # --- 3. Shocks on the saddle ---------------------------------------------------------
    shocks = {
        "Tjf": ("$\\Delta T_{jf}=+10$ K", lambda t: {"T_jf": p0.T_jf + (10.0 if t >= SHOCK_TIME else 0.0)}),
        "Tf": ("$\\Delta T_f=+5$ K", lambda t: {"T_f": T_F_SADDLE + (5.0 if t >= SHOCK_TIME else 0.0)}),
    }
    shocked = {"Tjf": find_saddle_point(t_jf=p0.T_jf + 10.0), "Tf": find_saddle_point(t_f=T_F_SADDLE + 5.0)}
    for s_key, op_s in shocked.items():
        num[f"qjShock{s_key}"] = _fmt(op_s.q_j, 2)
        num[f"bThreeShock{s_key}"] = _fmt(float(op_s.plant.linearize(op_s.ss, op_s.q_j)[1][2, 0]), 3)
        for arch in ("siso", "cascade"):
            num[f"absShock{s_key}{arch.capitalize()}"] = _fmt(closed_loop_abscissa(op_s, ds, arch), 3)
    shock_rows, traj = [], {}
    for s_key, (s_label, dist) in shocks.items():
        for arch in ARCH_LABELS:
            df = simulate(sad, ds, arch, SHOCK_HORIZON, disturbance=dist)
            df.to_csv(RESULTS_DIR / f"saddle_shock_{s_key}_{arch}.csv", index=False)
            traj[(s_key, arch)] = df
            m = shock_metrics(df, SHOCK_TIME)
            tag = f"{s_key}{arch.replace('_', '').capitalize()}"
            num.update({f"iae{tag}": _fmt(m["IAE"], 2), f"peak{tag}": _fmt(m["peak"], 2),
                        f"tv{tag}": _fmt(m["TV"], 1), f"qmax{tag}": _fmt(m["q_max"], 1),
                        f"ptp{tag}": _fmt(m["p2p"], 2)})
            shock_rows.append({
                "Shock": s_label, "Architecture": ARCH_LABELS[arch],
                "IAE (K min)": _fmt(m["IAE"], 2), "Peak $|e|$ (K)": _fmt(m["peak"], 2),
                "TV (L/min)": _fmt(m["TV"], 1), "$\\max q_j$ (L/min)": _fmt(m["q_max"], 1),
                "$T$ p-p, last 20 min (K)": _fmt(m["p2p"], 2),
            })
    for s_key in shocks:
        base, casc = (float(num[f"iae{s_key}{a}"]) for a in ("Siso", "Cascade"))
        num[f"iaeRed{s_key}"] = _fmt(100.0 * (1.0 - casc / base), 1)
    num["iaeRedFF"] = _fmt(100.0 * (1.0 - float(num["iaeTjfCascadeff"]) / float(num["iaeTjfCascade"])), 1)
    _export(
        shock_rows, "cherd_saddle_shocks",
        f"Regulation at the open-loop unstable saddle ($T_{{sp}}={sad.ss.T:.0f}$ K) after shocks at "
        f"$t={SHOCK_TIME:.0f}$ min; metrics over $t\\ge {SHOCK_TIME:.0f}$ min.",
        "tab:saddle_shocks", wide=True,
    )
    fig, axes = plt.subplots(2, 2, figsize=(IEEE_DOUBLE_COL_WIDTH_INCHES, 4.0), sharex=True)
    for col, (s_key, (s_label, _)) in enumerate(shocks.items()):
        for arch in ARCH_LABELS:
            df = traj[(s_key, arch)]
            axes[0, col].plot(df["t"], df["T"], color=ARCH_COLORS[arch], lw=1.3, label=ARCH_LABELS[arch])
            axes[1, col].plot(df["t"], df["q_j"], color=ARCH_COLORS[arch], lw=1.3)
        axes[0, col].axhline(sad.ss.T, color="k", ls=":", lw=0.9)
        axes[0, col].set(ylabel="$T$ (K)", title=s_label)
        axes[1, col].set(xlabel="$t$ (min)", ylabel="$q_j$ (L/min)")
    axes[0, 0].legend(fontsize=7)
    fig.tight_layout()
    _save(fig, "fig3_saddle_shocks")

    # --- 4. Dynamic fouling --------------------------------------------------------------
    f_crit_sad = critical_ua_fraction(sad)
    stab_rows = []
    f_grid = np.linspace(1.0, f_crit_sad + 0.01, 40)
    for f in f_grid:
        op_f = find_saddle_point(ua_frac=float(f))
        stab_rows.append({
            "ua_frac": f, "q_j": op_f.q_j,
            "b3": float(op_f.plant.linearize(op_f.ss, op_f.q_j)[1][2, 0]),
            "open_loop": float(np.linalg.eigvals(op_f.plant.linearize(op_f.ss, op_f.q_j)[0]).real.max()),
            "siso": closed_loop_abscissa(op_f, ds, "siso"),
            "cascade": closed_loop_abscissa(op_f, ds, "cascade"),
        })
    stab_df = pd.DataFrame(stab_rows)
    stab_df.to_csv(RESULTS_DIR / "frozen_ua_stability.csv", index=False)
    for arch in ("siso", "cascade"):
        f_stab = stability_boundary(ds, arch, f_crit_sad + 0.01)
        op_b = find_saddle_point(ua_frac=f_stab)
        num[f"fstab{arch.capitalize()}"] = _fmt(100 * f_stab, 1)
        num[f"qstab{arch.capitalize()}"] = _fmt(op_b.q_j, 1)
    b3_0, b3_c = stab_df["b3"].iloc[0], stab_df["b3"].iloc[-1]
    num.update(bThreeNom=_fmt(b3_0, 3), bThreeCrit=_fmt(b3_c, 3), bThreeRatio=_fmt(b3_0 / b3_c, 1))
    fig, ax = plt.subplots(figsize=(IEEE_SINGLE_COL_WIDTH_INCHES, 2.5))
    ax.plot(100 * stab_df["ua_frac"], stab_df["siso"], color=ARCH_COLORS["siso"], lw=1.3,
            label=ARCH_LABELS["siso"])
    ax.plot(100 * stab_df["ua_frac"], stab_df["cascade"], color=ARCH_COLORS["cascade"], lw=1.3,
            label=ARCH_LABELS["cascade"])
    ax.axhline(0.0, color="k", lw=0.8)
    ax.axvline(100 * f_crit_sad, color="gray", ls="--", lw=0.9)
    ax.set(xlabel="$UA/UA_0$ (%)", ylabel="$\\max\\Re\\lambda_{cl}$ (min$^{-1}$)")
    ax.invert_xaxis()
    ax.legend(fontsize=7)
    fig.tight_layout()
    _save(fig, "fig5_frozen_ua_stability")

    foul_rows, foul_traj = [], {}
    for key, op in points.items():
        t_pred = predicted_saturation_time(op, KAPPA_FOUL, UA_MIN_FRAC)
        for arch in ("siso", "cascade"):
            df = simulate(op, designs[key], arch, FOULING_HORIZON, kappa=KAPPA_FOUL,
                          ua_min_frac=UA_MIN_FRAC)
            df.to_csv(RESULTS_DIR / f"fouling_{key}_{arch}.csv", index=False)
            foul_traj[(key, arch)] = df
            t_sat = first_time(df, df["q_j"] >= LIMITS.u_max - 1e-6)
            t_run = first_time(df, df["T"] - op.ss.T > RUNAWAY_BAND)
            ua_sat = float(np.interp(t_sat, df["t"], df["UA"])) / op.plant.params.UA
            tag = ("Nom" if key == "nominal" else "Sad") + arch.capitalize()
            num.update({f"tsat{tag}": _fmt(t_sat, 2), f"trun{tag}": _fmt(t_run, 2),
                        f"Tend{tag}": _fmt(df["T"].iloc[-1], 2), f"uaSat{tag}": _fmt(100 * ua_sat, 1)})
            foul_rows.append({
                "Point": "Nominal" if key == "nominal" else "Saddle",
                "Architecture": ARCH_LABELS[arch],
                "$t_{\\mathrm{pred}}$ (min)": _fmt(t_pred, 2),
                "$t_{\\mathrm{sat}}$ (min)": _fmt(t_sat, 2),
                "$UA(t_{\\mathrm{sat}})/UA_0$ (\\%)": _fmt(100 * ua_sat, 1),
                "$t_{\\mathrm{runaway}}$ (min)": _fmt(t_run, 2),
                f"$T({FOULING_HORIZON:.0f}$ min) (K)": _fmt(df["T"].iloc[-1], 2),
            })
        num[f"tpred{'Nom' if key == 'nominal' else 'Sad'}"] = _fmt(t_pred, 2)
    _export(
        foul_rows, "cherd_fouling",
        f"Continuous fouling $d(UA)/dt=-\\kappa_{{\\mathrm{{foul}}}} r_A (UA-UA_{{\\min}})$ with "
        f"$\\kappa_{{\\mathrm{{foul}}}}={KAPPA_FOUL}$ L/mol and $UA_{{\\min}}={UA_MIN_FRAC:.2f}\\,UA_0$. "
        f"$t_{{\\mathrm{{pred}}}}$: quasi-steady prediction (Eq.~\\eqref{{eq:t_pred}}); "
        f"$t_{{\\mathrm{{sat}}}}$: first $q_j=u_{{\\max}}$; $t_{{\\mathrm{{runaway}}}}$: first "
        f"$T-T_{{sp}}>{RUNAWAY_BAND:.0f}$ K.",
        "tab:fouling", wide=True,
    )
    fig, axes = plt.subplots(3, 2, figsize=(IEEE_DOUBLE_COL_WIDTH_INCHES, 4.8), sharex=True)
    for col, (key, op) in enumerate(points.items()):
        for arch in ("siso", "cascade"):
            df = foul_traj[(key, arch)]
            axes[0, col].plot(df["t"], df["UA"] / op.plant.params.UA, color=ARCH_COLORS[arch], lw=1.3,
                              label=ARCH_LABELS[arch])
            axes[1, col].plot(df["t"], df["T"], color=ARCH_COLORS[arch], lw=1.3)
            axes[2, col].plot(df["t"], df["q_j"], color=ARCH_COLORS[arch], lw=1.3)
        t_pred = predicted_saturation_time(op, KAPPA_FOUL, UA_MIN_FRAC)
        for ax in axes[:, col]:
            ax.axvline(t_pred, color="gray", ls=":", lw=1.0)
        axes[0, col].axhline(critical_ua_fraction(op), color="k", ls="--", lw=0.8)
        axes[0, col].set(ylabel="$UA/UA_0$", title=f"{op.name.capitalize()} point")
        axes[1, col].set(ylabel="$T$ (K)")
        axes[2, col].set(ylabel="$q_j$ (L/min)", xlabel="$t$ (min)")
    axes[0, 0].legend(fontsize=7)
    fig.tight_layout()
    _save(fig, "fig4_fouling_runaway")

    # Parameter table (inputs, not results)
    _export(
        [
            {"Symbol": "$q$, $V$, $V_j$", "Value": f"{p0.q:.0f} L/min, {p0.V:.0f} L, {p0.V_j:.0f} L"},
            {"Symbol": "$k_0$, $E/R$", "Value": f"{p0.k_0:.1e} min$^{{-1}}$, {p0.E_over_R:.0f} K"},
            {"Symbol": "$-\\Delta H$", "Value": f"{-p0.delta_H:.1e} cal/mol"},
            {"Symbol": "$\\rho c_p$, $\\rho_j c_{pj}$", "Value": f"{p0.rho_cp:.0f}, {p0.rho_j_cp_j:.0f} cal/(L K)"},
            {"Symbol": "$UA_0$", "Value": f"{p0.UA:.1e} cal/(min K)"},
            {"Symbol": "$C_{Af}$, $T_{jf}$", "Value": f"{p0.C_Af:.1f} mol/L, {p0.T_jf:.0f} K"},
            {"Symbol": "$T_f$ (nominal / cooled)", "Value": f"{p0.T_f:.0f} / {T_F_SADDLE:.0f} K"},
            {"Symbol": "$[u_{\\min}, u_{\\max}]$, slew", "Value": f"[{LIMITS.u_min:.0f}, {LIMITS.u_max:.0f}] L/min, {LIMITS.max_slew_rate:.0f} L/min$^2$"},
            {"Symbol": "$\\Delta t$", "Value": f"{DT} min"},
        ],
        "cherd_parameters", "Model, actuator and sampling parameters.", "tab:parameters", wide=True,
    )
    write_numbers(num)
    logger.info("Campaign done: %d macros, outputs in %s and %s", len(num), PAPER_DIR, RESULTS_DIR)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_campaign()
