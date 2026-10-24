# -*- coding: utf-8 -*-
"""IC-T23 / IC-T24 (Paper 2, CCE): offset-free NMPC, de-confounding, mismatch Monte Carlo.

Stages (all outputs go to papers/02_computers_chemical_engineering/{tables,figures} and results/):
    ua       UA_crit at T_sp = T_ss - 2 K (thermodynamic limit of the 60 % UA scenario).
    offset   Table 5 regenerated with offset-free NMPC (integrating disturbances d_T, d_C).
    horizon  N in {30, 50, 75, 100} sweep + predicted-vs-realised horizon trajectories.
    deconf   Fouling transient: every PID rule, gain-scheduled PID, NMPC ablations, symmetric TV.
    mc       Latin-hypercube Monte Carlo (N = 28) of NMPC-model parametric mismatch, joblib-parallel.

Usage: python -m experiments.exp_07_cce_remediation [stage ...]   (default: all stages)
"""

from __future__ import annotations

import logging
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import brentq
from scipy.stats import qmc

from experiments import exp_02_robustness_campaign as exp02
from experiments.exp_02_robustness_campaign import (
    BENCHMARK_LIMITS,
    OPT_ITAE,
    export_latex_table,
    make_factories,
    run_load_disturbance_campaign,
    setup_controllers,
)
from src.classical_control.closed_loop import ClosedLoopResult, ClosedLoopSimulator
from src.classical_control.pid_controller import PIDController, PIDGains
from src.controllers.optimal.nmpc_controller import AugmentedCstrStateEstimator, CstrNmpcController
from src.evaluation.plot_styles import IEEE_PALETTE, get_figure_dimensions, setup_ieee_style
from src.sim_core.cstr_plant import CSTRParameters, CSTRPlant

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("exp_07_cce")

PAPER_DIR = PROJECT_ROOT / "papers" / "02_computers_chemical_engineering"
TABLES_DIR, FIGURES_DIR = PAPER_DIR / "tables", PAPER_DIR / "figures"
DT = 0.02
Q_J_SS = 100.0
DIST_GAIN = 0.1  # L of the integrating disturbance estimator (Oracle and MHE)
PID_FILTER_TAU = 0.05  # [min] first-order measurement filter of the symmetric-noise comparison
NOISE_STD = 0.05
UA_FOULED, T_FOUL = 0.70, 4.0
HORIZONS = (30, 50, 75, 100)
MC_SAMPLES, MC_BAND, MC_SEED = 28, 0.10, 20260
MC_PARAMS = ("E_over_R", "k_0", "delta_H", "T_f", "C_Af")
PID_RULES = ("Ziegler-Nichols", "Cohen-Coon", "Tyreus-Luyben", "AMIGO", "Skogestad SIMC", OPT_ITAE)


# --------------------------------------------------------------------------- controllers
class FilteredMeasurement:
    """Wraps a controller with a first-order filter y_f+ = y_f + dt/(tau+dt) (y - y_f)."""

    def __init__(self, inner: Any, tau: float = PID_FILTER_TAU) -> None:
        """Wraps `inner`; `tau` is the filter time constant [min]."""
        self.inner, self.tau = inner, float(tau)
        self._y: float | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def reset(self, *args: Any, **kwargs: Any) -> None:
        """Clears the filter state and resets the wrapped controller."""
        self._y = None
        self.inner.reset(*args, **kwargs)

    def compute(self, setpoint: float, measurement: float, dt: float, **kw: Any) -> tuple[float, dict]:
        """Filters the measurement, then calls the wrapped controller."""
        self._y = measurement if self._y is None else self._y + dt / (self.tau + dt) * (measurement - self._y)
        return self.inner.compute(setpoint=setpoint, measurement=self._y, dt=dt, **kw)


class GainScheduledPID:
    """PID with K_p(alpha_hat) = K_p0 / alpha_hat; alpha_hat from the NMPC's augmented estimator."""

    supports_full_state = True

    def __init__(self, gains: PIDGains, y_ss: float, tj_noise_std: float, seed: int | None) -> None:
        """Builds the PID, its estimator and the jacket-sensor noise generator."""
        self.base = gains
        self.inner = PIDController(gains, BENCHMARK_LIMITS, u_bias=Q_J_SS, y_ss=y_ss)
        self.estimator = AugmentedCstrStateEstimator(q_j_ss=Q_J_SS)
        self.u_bias, self._noise, self._seed = Q_J_SS, float(tj_noise_std), seed
        self._rng = np.random.default_rng(seed)
        self._alpha = 1.0

    def reset(self, initial_measurement: float, initial_u: float | None = None) -> None:
        """Resets estimator, gains and PID state."""
        self._rng = np.random.default_rng(self._seed)
        self.estimator.reset(t_meas=float(initial_measurement))
        self._alpha = 1.0
        self.inner.gains = self.base
        self.inner.reset(initial_measurement, initial_u)

    def compute(self, setpoint: float, measurement: float, dt: float, full_state: Any = None):
        """Estimates alpha_UA, rescales K_p and returns the PID action and diagnostics."""
        t_j = None if full_state is None else float(full_state[2]) + self._rng.normal(0.0, self._noise)
        self._alpha = float(self.estimator.step(self.inner._last_u_applied, measurement, t_j, dt)[3])
        self.inner.gains = replace(self.base, kp=self.base.kp / self._alpha)
        u, diag = self.inner.compute(setpoint, measurement, dt)
        return u, {**diag, "alpha_ua_hat": self._alpha}


class SlewClipped:
    """Plans without the rate limit (internal slew 1e4) and lets the actuator clip the move."""

    supports_full_state = True

    def __init__(self, inner: CstrNmpcController, slew: float) -> None:
        """Wraps an NMPC whose planner ignores the slew limit; `slew` is the actuator limit [L/min^2]."""
        self.inner, self.max_move = inner, slew * inner.t_step_min

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def compute(self, *args: Any, **kwargs: Any) -> tuple[float, dict]:
        """Runs the NMPC and clips its move to the actuator slew limit."""
        prev = self.inner._last_u
        u, diag = self.inner.compute(*args, **kwargs)
        u = float(np.clip(u, prev - self.max_move, prev + self.max_move))
        self.inner._last_u = u  # the OCP must start from the position the valve really reached
        return u, diag


def nmpc(
    mode: str,
    noise: float = 0.0,
    seed: int | None = None,
    horizon: int = exp02.NMPC_HORIZON,
    offset_free: bool = False,
    params: CSTRParameters | None = None,
    frozen_alpha: float | None = None,
    slew_aware: bool = True,
) -> Any:
    """NMPC factory with the Table 7 settings; flags select the ablation variants."""
    ctrl = CstrNmpcController(
        horizon_steps=horizon,
        t_step_min=DT,
        u_bias=Q_J_SS,
        feedback_mode=mode,  # type: ignore[arg-type]
        max_slew_rate=BENCHMARK_LIMITS.max_slew_rate if slew_aware else 1e4,
        u_min=BENCHMARK_LIMITS.u_min,
        u_max=BENCHMARK_LIMITS.u_max,
        tj_noise_std=noise,
        seed=seed,
        params=params,
        true_alpha_ua=frozen_alpha,
        disturbance_gain=DIST_GAIN if offset_free else 0.0,
    )
    return ctrl if slew_aware else SlewClipped(ctrl, BENCHMARK_LIMITS.max_slew_rate)


# --------------------------------------------------------------------------- scenarios
def run_fouling(ctrl: Any, plant: CSTRPlant | None = None) -> ClosedLoopResult:
    """Table 7 protocol: -2 K step at 0.5 min, fouling to 70 % UA at 4 min, sigma = 0.05 K."""
    plant = plant or CSTRPlant()
    ss = plant.find_steady_state(q_j=Q_J_SS)
    ua = UA_FOULED * CSTRPlant().params.UA
    return ClosedLoopSimulator().run(
        plant=plant, controller=ctrl, initial_state=ss, t_span=(0.0, 10.0), dt=DT,
        setpoint_func=lambda t: ss.T - 2.0 if t >= 0.5 else ss.T,
        disturbance_func=lambda t: {"UA": ua} if t >= T_FOUL else {},
        noise_std=NOISE_STD, seed=42,
    )


def run_feed_disturbance(ctrl: Any, t_end: float = 15.0) -> ClosedLoopResult:
    """Table 5 protocol: +5 K T_f at 2 min, +20 % C_Af at 8 min, regulation at T_ss."""
    plant = CSTRPlant()
    ss, p = plant.find_steady_state(q_j=Q_J_SS), plant.params

    def dist(t: float) -> dict[str, float]:
        d = {"T_f": p.T_f + 5.0} if t >= 2.0 else {}
        return {**d, "C_Af": p.C_Af + 0.2} if t >= 8.0 else d

    return ClosedLoopSimulator().run(
        plant=plant, controller=ctrl, initial_state=ss, t_span=(0.0, t_end), dt=DT,
        setpoint_func=lambda t: ss.T, disturbance_func=dist, noise_std=NOISE_STD, seed=42,
    )


def _save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIGURES_DIR / f"{stem}.pdf")
    fig.savefig(FIGURES_DIR / f"{stem}.png", dpi=300)
    plt.close(fig)


# --------------------------------------------------------------------------- ua
def required_flow(plant_params: CSTRParameters, t_sp: float) -> float:
    """Coolant flow q_j [L/min] holding T = t_sp at steady state (exact algebraic balance)."""
    p = plant_params
    k = p.k_0 * np.exp(-p.E_over_R / t_sp)
    heat = (p.q / p.V) * (p.T_f - t_sp) + (-p.delta_H / p.rho_cp) * k * p.q * p.C_Af / (p.q + p.V * k)
    t_j = t_sp - heat * p.V * p.rho_cp / p.UA  # jacket temperature that removes exactly `heat`
    return float(p.V_j * p.UA / (p.V_j * p.rho_j_cp_j) * (t_sp - t_j) / (t_j - p.T_jf))


def run_ua_critical() -> pd.DataFrame:
    """UA_crit(T_sp, q_j,max) and the equilibrium temperature at 60 % UA with full cooling."""
    p = CSTRPlant().params
    t_sp = CSTRPlant().find_steady_state(q_j=Q_J_SS).T - 2.0

    def residual(ua_frac: float, t: float, q_j: float = BENCHMARK_LIMITS.u_max) -> float:
        k = p.k_0 * np.exp(-p.E_over_R / t)
        ua = ua_frac * p.UA
        t_j = (q_j / p.V_j * p.T_jf + ua / (p.V_j * p.rho_j_cp_j) * t) / (
            q_j / p.V_j + ua / (p.V_j * p.rho_j_cp_j))
        return float((p.q / p.V) * (p.T_f - t) + (-p.delta_H / p.rho_cp) * k * p.q * p.C_Af / (p.q + p.V * k)
                      - ua / (p.V * p.rho_cp) * (t - t_j))

    ua_crit = brentq(lambda f: residual(f, t_sp), 0.3, 1.0)
    grid = np.linspace(300.0, 500.0, 40001)
    rows = []
    for frac in (1.0, 0.9, 0.8, 0.7, ua_crit, 0.6):
        r = np.array([residual(frac, t) for t in grid])
        eq = grid[:-1][np.sign(r[:-1]) != np.sign(r[1:])]
        rows.append({
            r"\(UA/UA_{\mathrm{nom}}\)": rf"{100 * frac:.2f}\%" + (r" (\(UA_{\mathrm{crit}}\))" if frac == ua_crit else ""),
            r"Equilibrium \(T\) at \(q_j = 300\) (K)": ", ".join(f"{t:.2f}" for t in eq),
            r"Reaches \(T_{sp}\)?": "yes" if frac >= ua_crit - 1e-9 else "no",
        })
    export_latex_table(
        rows, TABLES_DIR / "ua_critical_table.tex",
        caption=(rf"Steady states with the valve fully open ($q_j = 300$~L/min) as a function of $UA$; "
                 rf"$T_{{sp}} = {t_sp:.2f}$~K and $UA_{{\mathrm{{crit}}}} = {100 * ua_crit:.2f}\%$, the root of "
                 r"the steady-state energy balance at $T=T_{sp}$."),
        label="tab:ua_critical",
    )
    logger.info("UA_crit = %.4f (T_sp = %.3f K)", ua_crit, t_sp)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- offset (Table 5)
def run_offset_table() -> None:
    """Regenerates Table 5 / Fig. 2: PIDs, original NMPC and the two offset-free NMPCs."""
    plant = CSTRPlant()
    ss = plant.find_steady_state(q_j=Q_J_SS)
    gains, _ = setup_controllers(plant, ss, Q_J_SS)
    base = make_factories(gains, Q_J_SS, BENCHMARK_LIMITS, dt=DT, y_ss=ss.T)
    ctrls = {k: base[k] for k in ("AMIGO", OPT_ITAE, "NMPC-Oracle", "NMPC-MHE")}
    ctrls["NMPC-Oracle (OF)"] = lambda sensor_noise_std=0.0, seed=None: nmpc("oracle", sensor_noise_std, seed, offset_free=True)
    ctrls["NMPC-MHE (OF)"] = lambda sensor_noise_std=0.0, seed=None: nmpc("mhe", sensor_noise_std, seed, offset_free=True)
    run_load_disturbance_campaign(plant, ss, Q_J_SS, ctrls, BENCHMARK_LIMITS, FIGURES_DIR, TABLES_DIR)


# --------------------------------------------------------------------------- horizon
class _PredictionRecorder:
    """Keeps the predicted T trajectory of the OCP at the requested sample indices."""

    def __init__(self, inner: CstrNmpcController, at: set[int]) -> None:
        self.inner, self.at, self.k = inner, at, 0
        self.pred: dict[int, np.ndarray] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def compute(self, *a: Any, **kw: Any) -> tuple[float, dict]:
        out = self.inner.compute(*a, **kw)
        if self.k in self.at:
            self.pred[self.k] = np.asarray(self.inner.mpc.opt_x_num["_x", :, 0, 0, "T"], dtype=float).ravel()
        self.k += 1
        return out


def _horizon_case(n: int, offset_free: bool, record_at: tuple[float, ...]) -> dict[str, Any]:
    ctrl = _PredictionRecorder(nmpc("oracle", horizon=n, offset_free=offset_free), {round(t / DT) for t in record_at})
    res = run_feed_disturbance(ctrl)
    ss_t = CSTRPlant().find_steady_state(q_j=Q_J_SS).T
    e = res.states[:, 1] - ss_t
    return {
        "N": n, "offset_free": offset_free, "t": res.t, "T": res.states[:, 1], "u": res.u_applied,
        "e_ss": float(e[-50:].mean()), "u_end": float(res.u_applied[-1]), "iae": res.metrics.iae,
        "peak": float(np.abs(e[res.t >= 2.0]).max()), "pred": ctrl.pred,
    }


def run_horizon_sweep() -> list[dict[str, Any]]:
    """N-sweep of the original and offset-free Oracle NMPC + prediction-vs-realised figure."""
    record_at = (9.0, 12.0, 14.0)
    cases = Parallel(n_jobs=-1)(
        delayed(_horizon_case)(n, of, record_at) for of in (False, True) for n in HORIZONS)
    p = CSTRPlant().params
    ss_t = CSTRPlant().find_steady_state(q_j=Q_J_SS).T
    plant_dist = replace(p, T_f=p.T_f + 5.0, C_Af=p.C_Af + 0.2)
    u_nom, u_dist = required_flow(p, ss_t), required_flow(plant_dist, ss_t)
    rows = [{
        "Variant": "Offset-free" if c["offset_free"] else "Original (no disturbance model)",
        r"\(N\)": c["N"], r"Horizon (min)": f"{c['N'] * DT:.1f}",
        r"\(T(t_f)-T_{sp}\) (K)": f"{c['e_ss']:+.3f}", "Valve at \\(t_f\\) (L/min)": f"{c['u_end']:.1f}",
        "IAE (K$\\cdot$min)": f"{c['iae']:.2f}", "Peak dev. (K)": f"{c['peak']:.2f}",
    } for c in cases]
    export_latex_table(
        rows, TABLES_DIR / "horizon_sweep_table.tex",
        caption=(f"Prediction-horizon sweep of NMPC-Oracle on the feed-disturbance scenario of "
                 f"Table~\\ref{{tab:load_disturbance}}. Steady-state energy balance at $T_{{sp}}$: "
                 f"$q_j^\\star = {u_nom:.1f}$~L/min for the nominal feed and ${u_dist:.1f}$~L/min with "
                 f"$\\Delta T_f=+5$~K and $\\Delta C_{{Af}}=+20\\%$; $T(t_f)-T_{{sp}}$ is the mean over the last minute."),
        label="tab:horizon_sweep",
    )
    # predicted vs realised: original NMPC, N = 50, offset after the C_Af step
    orig = next(c for c in cases if c["N"] == 50 and not c["offset_free"])
    of50 = next(c for c in cases if c["N"] == 50 and c["offset_free"])
    setup_ieee_style(single_column=True)
    w, h = get_figure_dimensions(columns=1, height_override=3.4)
    fig, ax = plt.subplots(figsize=(w, h), dpi=300)
    ax.axhline(ss_t, color=IEEE_PALETTE["Setpoint"], linestyle=":", label=r"$T_{sp}$")
    ax.plot(orig["t"], orig["T"], color="black", linewidth=1.1, label="Realised $T$ (original)")
    ax.plot(of50["t"], of50["T"], color=IEEE_PALETTE["NMPC-Oracle (OF)"], linewidth=1.1, label="Realised $T$ (offset-free)")
    for i, (k, tr) in enumerate(sorted(orig["pred"].items())):
        tt = k * DT + DT * np.arange(len(tr))
        ax.plot(tt, tr, color="#D55E00", linestyle="--", linewidth=0.9, label="Predicted (original)" if i == 0 else None)
    ax.set_xlabel("Time $t$ (min)")
    ax.set_ylabel("Reactor temperature $T$ (K)")
    ax.set_xlim(7.0, 15.5)
    ax.set_ylim(ss_t - 1.0, ss_t + 10.5)
    ax.grid(True)
    ax.legend(fontsize=5.8, loc="upper center", ncol=2)
    fig.tight_layout()
    _save(fig, "fig_horizon_predicted_vs_realised")
    return cases


# --------------------------------------------------------------------------- deconfounding
def _deconf_case(name: str, gains: dict[str, PIDGains]) -> dict[str, Any]:
    ss_t = CSTRPlant().find_steady_state(q_j=Q_J_SS).T
    pid = lambda g: PIDController(g, BENCHMARK_LIMITS, u_bias=Q_J_SS, y_ss=ss_t)  # noqa: E731
    seed = 7
    if name.endswith("(raw)"):
        ctrl = pid(gains[name.removesuffix(" (raw)")])
    elif name.endswith("+ filter"):
        ctrl = FilteredMeasurement(pid(gains[name.removesuffix(" + filter")]))
    elif name == "AMIGO + gain scheduling":
        ctrl = FilteredMeasurement(GainScheduledPID(gains["AMIGO"], ss_t, NOISE_STD, seed))
    elif name == "NMPC-MHE (alpha frozen = 1)":
        ctrl = nmpc("mhe", NOISE_STD, seed, frozen_alpha=1.0)
    elif name == "NMPC-MHE (slew-unaware planner)":
        ctrl = nmpc("mhe", NOISE_STD, seed, slew_aware=False)
    elif name == "NMPC-MHE (offset-free)":
        ctrl = nmpc("mhe", NOISE_STD, seed, offset_free=True)
    elif name == "NMPC-Oracle":
        ctrl = nmpc("oracle", NOISE_STD, seed)
    else:
        ctrl = nmpc("mhe", NOISE_STD, seed)
    res = run_fouling(ctrl)
    return {"name": name, "iae": res.metrics.iae, "itae": res.metrics.itae, "tv": res.metrics.tv,
            "mp": res.metrics.overshoot_pct, "T": res.states[:, 1], "t": res.t}


def run_deconfounding(gains: dict[str, PIDGains]) -> pd.DataFrame:
    """Fouling transient: all PID rules (raw + filtered), gain scheduling, NMPC ablation ladder."""
    names = [f"{r} + filter" for r in PID_RULES] + ["AMIGO (raw)", OPT_ITAE + " (raw)", "AMIGO + gain scheduling",
             "NMPC-MHE (alpha frozen = 1)", "NMPC-MHE (slew-unaware planner)", "NMPC-MHE", "NMPC-MHE (offset-free)", "NMPC-Oracle"]
    out = {c["name"]: c for c in Parallel(n_jobs=-1)(delayed(_deconf_case)(n, gains) for n in names)}
    best_pid = "AMIGO + filter"  # a-priori reference of the paper; ZN has lower IAE but M_p = 37.5 %
    df = pd.DataFrame([{k: v for k, v in c.items() if k not in ("T", "t")} for c in out.values()])
    df.to_csv(PROJECT_ROOT / "results" / "deconfounding_fouling.csv", index=False)

    rows = [{
        "Controller": c["name"].replace("alpha", r"\(\alpha\)").replace("Optimal ITAE ($M_s \\leq 1.6$)", "Opt.\\ ITAE"),
        "IAE": f"{c['iae']:.3f}", "TV (L/min)": f"{c['tv']:.1f}", r"\(M_p\) (\%)": f"{c['mp']:.1f}",
        r"TV vs filtered AMIGO (\%)": "--" if "NMPC-MHE" not in c["name"] else f"{100 * (out[best_pid]['tv'] - c['tv']) / out[best_pid]['tv']:+.1f}",
    } for c in out.values()]
    export_latex_table(
        rows, TABLES_DIR / "deconfounding_table.tex",
        caption=(f"De-confounded fouling transient ($-2$~K step, $70\\%\\,UA$ at $t={T_FOUL:.0f}$~min, "
                 f"$\\sigma={NOISE_STD}$~K). All PID rules use a first-order measurement filter "
                 f"($\\tau_f={PID_FILTER_TAU}$~min; raw rows for reference); NMPC-MHE sees the same noise. "
                 f"Reference: filtered AMIGO (ZN reaches a lower IAE only with a large overshoot). Gain scheduling: "
                 r"$K_p=K_{p0}/\hat\alpha_{UA}$ with $\hat\alpha_{UA}$ from the NMPC estimator."),
        label="tab:deconfounding",
    )
    # sequential ladder: static PID -> +adaptation -> +nonlinear prediction -> +rate planning
    ladder = [(best_pid, "Static PID (AMIGO, filtered)"),
              ("AMIGO + gain scheduling", "(a) Online adaptation of $\\hat\\alpha_{UA}$ (gain scheduling)"),
              ("NMPC-MHE (slew-unaware planner)", "(b) Nonlinear model-based prediction"),
              ("NMPC-MHE", "(c) Slew-rate constrained planning")]
    total = out[ladder[0][0]]["iae"] - out[ladder[-1][0]]["iae"]
    drows = [{"Step": lab, "IAE after step": f"{out[n]['iae']:.3f}",
              r"\(\Delta\)IAE": "--" if i == 0 else f"{out[ladder[i - 1][0]]['iae'] - out[n]['iae']:+.3f}",
              "Share of total gain (\\%)": "--" if i == 0 else f"{100 * (out[ladder[i - 1][0]]['iae'] - out[n]['iae']) / total:.1f}"}
             for i, (n, lab) in enumerate(ladder)]
    drows.append({"Step": "NMPC-MHE with frozen $\\alpha_{UA}=1$ (adaptation removed from NMPC)",
                  "IAE after step": f"{out['NMPC-MHE (alpha frozen = 1)']['iae']:.3f}",
                  r"\(\Delta\)IAE": f"{out['NMPC-MHE (alpha frozen = 1)']['iae'] - out['NMPC-MHE']['iae']:+.3f}", "Share of total gain (\\%)": "--"})
    export_latex_table(
        drows, TABLES_DIR / "deconfounding_ladder_table.tex",
        caption=("Sequential decomposition of the NMPC gain over the best filtered PID in the fouling transient. "
                 "The shares are order-dependent (ladder), not Shapley values; the last row gives the IAE "
                 "increase when adaptation is removed from the NMPC itself."),
        label="tab:deconfounding_ladder",
    )
    return df


# --------------------------------------------------------------------------- Monte Carlo
def _mc_case(idx: int, theta: np.ndarray, kind: str) -> dict[str, Any]:
    p = CSTRParameters()
    mismatch = {n: getattr(p, n) * (1.0 + th) for n, th in zip(MC_PARAMS, theta) if n != "T_f"}
    mismatch["T_f"] = p.T_f + theta[MC_PARAMS.index("T_f")] * (p.T_f - 273.15)  # +-band of T_f in deg C
    try:
        res = run_fouling(nmpc("mhe", NOISE_STD, 7, offset_free=(kind == "OF"), params=replace(p, **mismatch)))
        e_ss = float(np.mean(res.states[-50:, 1] - (res.setpoint[-1])))
        return {"sample": idx, "kind": kind, "iae": res.metrics.iae, "tv": res.metrics.tv, "e_ss": e_ss, "ok": True}
    except Exception as exc:  # noqa: BLE001 - a failed solve is a Monte Carlo outcome, recorded not hidden
        logger.warning("MC sample %d (%s) failed: %s", idx, kind, exc)
        return {"sample": idx, "kind": kind, "iae": np.nan, "tv": np.nan, "e_ss": np.nan, "ok": False}


def run_mismatch_mc(gains: dict[str, PIDGains]) -> pd.DataFrame:
    """LHS (N = 28) over +-10 % NMPC-model mismatch of E/R, k0, dH, T_f, C_Af; joblib-parallel."""
    theta = qmc.scale(qmc.LatinHypercube(d=len(MC_PARAMS), seed=MC_SEED).random(MC_SAMPLES),
                      -MC_BAND, MC_BAND)
    jobs = [(i, th, k) for i, th in enumerate(theta) for k in ("orig", "OF")]
    runs = Parallel(n_jobs=-1)(delayed(_mc_case)(i, th, k) for i, th, k in jobs)
    nominal = {k: _mc_case(-1, np.zeros(len(MC_PARAMS)), k) for k in ("orig", "OF")}
    ss_t = CSTRPlant().find_steady_state(q_j=Q_J_SS).T
    pid = run_fouling(FilteredMeasurement(PIDController(gains["AMIGO"], BENCHMARK_LIMITS, u_bias=Q_J_SS, y_ss=ss_t)))
    df = pd.DataFrame(runs)
    df.to_csv(PROJECT_ROOT / "results" / "mismatch_mc_lhs.csv", index=False)
    rows = []
    for kind, label in (("orig", "NMPC-MHE (original)"), ("OF", "NMPC-MHE (offset-free)")):
        d = df[(df.kind == kind) & df.ok]
        rows.append({
            "Controller": label, "Nominal IAE": f"{nominal[kind]['iae']:.3f}",
            "IAE mean": f"{d.iae.mean():.3f}", "IAE P95": f"{d.iae.quantile(0.95):.3f}", "IAE max": f"{d.iae.max():.3f}",
            r"\(|e_{ss}|\) mean (K)": f"{d.e_ss.abs().mean():.3f}", r"\(|e_{ss}|\) max (K)": f"{d.e_ss.abs().max():.3f}",
            "Converged": f"{len(d)}/{MC_SAMPLES}",
        })
    rows.append({"Controller": "AMIGO + filter (nominal, no model)", "Nominal IAE": f"{pid.metrics.iae:.3f}",
                 "IAE mean": "--", "IAE P95": "--", "IAE max": "--",
                 r"\(|e_{ss}|\) mean (K)": f"{abs(np.mean(pid.states[-50:, 1] - pid.setpoint[-1])):.3f}",
                 r"\(|e_{ss}|\) max (K)": "--", "Converged": "--"})
    export_latex_table(
        rows, TABLES_DIR / "mismatch_mc_table.tex",
        caption=(f"Parametric plant-model mismatch: Latin-hypercube Monte Carlo ($N={MC_SAMPLES}$) of "
                 f"$\\pm{int(100 * MC_BAND)}\\%$ errors of the NMPC internal model in $E_a/R$, $k_0$, $\\Delta H$, "
                 "$C_{Af}$ and $T_f$ (the latter as $\\pm10\\%$ of $T_f-273.15$~K) against the nominal plant, "
                 "fouling scenario of Table~\\ref{tab:deconfounding}."),
        label="tab:mismatch_mc",
    )
    return df


# --------------------------------------------------------------------------- main
STAGES = ("ua", "offset", "horizon", "deconf", "mc")

if __name__ == "__main__":
    wanted = tuple(sys.argv[1:]) or STAGES
    (PROJECT_ROOT / "results").mkdir(exist_ok=True)
    exp02.RESULTS_DIR = PROJECT_ROOT / "results"
    exp02.TABLE_FLOAT_ENV = "table*"  # cas-dc class; the legacy default targets another class
    if "ua" in wanted:
        run_ua_critical()
    if "offset" in wanted:
        run_offset_table()
    if "horizon" in wanted:
        run_horizon_sweep()
    if {"deconf", "mc"} & set(wanted):
        _plant = CSTRPlant()
        _gains, _ = setup_controllers(_plant, _plant.find_steady_state(q_j=Q_J_SS), Q_J_SS)
        if "deconf" in wanted:
            logger.info("\n%s", run_deconfounding(_gains).drop(columns=["itae"]).to_string())
        if "mc" in wanted:
            logger.info("\n%s", run_mismatch_mc(_gains).groupby("kind")[["iae", "e_ss"]].describe().to_string())
