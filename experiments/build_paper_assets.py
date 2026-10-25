# -*- coding: utf-8 -*-
"""Builds the tables and figures of the split Elsevier papers (Wave 4) from the validated runs.

Artigo 1 (Journal of Process Control) is PID-only: the campaigns that contained NMPC rows or
curves are re-run with ``include_nmpc=False`` (deterministic, identical PID numbers), and the
PID-only tables are re-rendered from their validated CSV mirrors in ``results/``. CSV mirrors of
the paper tables go to ``results/<paper>/`` so that ``results/*.csv`` of the base manuscript are
never overwritten.

Artigo 2 (Computers & Chemical Engineering) duels NMPC with the two best robust PID tunings
only (AMIGO, 1-DOF Optimal ITAE): every campaign is re-run with that controller subset.

Usage:
    .venv/bin/python experiments/build_paper_assets.py jpc|jpc-remediation|cace
"""

import logging
import re
import shutil
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from matplotlib.ticker import NullFormatter
from scipy import stats as scipy_stats

import experiments.exp_01_classical_benchmark as exp01
import experiments.exp_02_robustness_campaign as exp02
from experiments.exp_01_classical_benchmark import run_benchmark
from experiments.exp_01b_nmpc_oracle_comparison import (
    run_mhe_tuning_sensitivity,
    run_nmpc_oracle_benchmark,
)
from src.classical_control.tuning_optimization import (
    OptimizationCriterion,
    calculate_maximum_sensitivity_foptd,
    linearized_robustness,
    loop_gain_linearized,
    phase_margin_deg,
    tune_by_optimization,
)
from src.evaluation.plot_styles import setup_ieee_style
from src.sim_core.cstr_plant import CSTRParameters

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("build_paper_assets")

ARTICLES = PROJECT_ROOT / "Artigos_Rascunhos"
BASE = ARTICLES / "Artigo_01_Classic_Methods" / "overleaf"


def rerender_from_csv(stem: str, tables_dir: Path) -> None:
    """Re-renders a validated base-manuscript table in the current float environment."""
    tex = (BASE / "tables" / f"{stem}.tex").read_text()
    caption = tex[tex.index("\\caption{") + len("\\caption{") : tex.index("}\n\\label{")]
    label = re.search(r"\\label\{(.*?)\}", tex).group(1)
    df = pd.read_csv(PROJECT_ROOT / "results" / f"{stem}.csv", dtype=str, keep_default_na=False)
    exp02.export_latex_table(df.to_dict("records"), tables_dir / f"{stem}.tex", caption, label)


AW = exp02.AntiWindupMethod
ABLATION_VARIANTS = (
    ("None", AW.NONE),
    ("Back-calc.", AW.BACK_CALCULATION),
    ("Sign-blind amp.", AW.CLAMPING_NAIVE),
    ("Amp. uncond.", AW.CLAMPING_POS_AGNOSTIC),
    ("Amp.+rate uncond.", AW.CLAMPING_RATE_AGNOSTIC),
    ("Amp. direct.", AW.CLAMPING_POS_DIRECTIONAL),
    ("Amp.+rate direct. (Eq.~\\ref{eq:clamping_antiwindup})", AW.CLAMPING),
)
MEASUREMENT_TAU_F = 0.05  # min
NOISE_LEVELS = (0.0, 0.01, 0.05, 0.10)  # K
OOS_STEPS = (-5.0, -2.0, -1.0, 1.0, 2.0, 5.0)  # K; -2 K is the ITAE design (in-sample) step


def run_antiwindup_ablation(
    plant: "exp02.CSTRPlant", ss: "exp02.CSTRState", gains: dict, tables_dir: Path
) -> None:
    """Nominal -2 K step: none / back-calculation / sign-blind amplitude clamping / 2x2 clamping factorial.

    The 2x2 factors are the trigger (amplitude only vs amplitude + slew rate) and the sign
    awareness (unconditional freeze vs directional (u_raw - u_act)(Kp e) > 0). A second table
    exposes the windup mechanism of the reverse-acting loop for the high-gain rules.
    """
    sim = exp02.ClosedLoopSimulator()
    rows, mech_rows = [], []
    for name, g in gains.items():
        if name.startswith("2-DOF"):
            continue  # ablation reported on the six distinct feedback loops (1-DOF)
        row = {"Method": name}
        for label, method in ABLATION_VARIANTS:
            pid = exp02.PIDController(g, exp02.BENCHMARK_LIMITS, method, u_bias=100.0, y_ss=ss.T)
            res = sim.run(plant, pid, ss, (0.0, 10.0), 0.02, setpoint_func=lambda t: ss.T - 2.0)
            m = res.metrics
            row[label] = f"{m.iae:.2f} / {m.overshoot_pct:.1f}"
            if name in ("Ziegler-Nichols", "Cohen-Coon") and method in (
                AW.NONE, AW.CLAMPING_NAIVE, AW.CLAMPING
            ):
                t_valve_max = float(np.sum(res.u_applied >= exp02.BENCHMARK_LIMITS.u_max - 1e-9)) * 0.02
                mech_rows.append({
                    "Method": name,
                    "Anti-windup": label,
                    "\\(T_{\\min}\\) (K)": f"{res.states[:, 1].min():.1f}",
                    "Time at \\(u_{\\max}\\) (min)": f"{t_valve_max:.2f}",
                    "\\(T(t_f)-T_{sp}\\) (K)": f"{res.states[-1, 1] - (ss.T - 2.0):+.2f}",
                    "\\(\\max|u_{\\mathrm{raw}}-u_{\\mathrm{act}}|\\) (L/min)": f"{np.max(np.abs(res.u_unconstrained - res.u_applied)):.0f}",
                })
        rows.append(row)
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "antiwindup_ablation.tex",
        caption=(
            "Anti-windup ablation on the nominal $-2$~K step (same gains, valve and protocol as "
            "Table~\\ref{tab:testbed}); each cell reports IAE (K$\\cdot$min) / overshoot (\\%). "
            "The last four columns are the $2\\times 2$ clamping factorial (trigger: amplitude only or "
            "amplitude + slew rate; sign awareness: unconditional or directional); the last column is "
            "Eq.~\\eqref{eq:clamping_antiwindup}. ``Sign-blind amp.'' freezes the integrator when "
            "$u_{\\text{raw}} \\ge u_{\\max} \\wedge e>0$ or $u_{\\text{raw}} \\le u_{\\min} \\wedge e<0$, "
            "the sign convention of direct-acting loops."
        ),
        label="tab:antiwindup_ablation",
    )
    exp02.export_latex_table(
        data=mech_rows,
        output_path=tables_dir / "antiwindup_mechanism.tex",
        caption=(
            "Windup mechanism of the empirical rules on the $-2$~K step: lowest reactor temperature, "
            "time with the valve at its upper stop, final tracking error and largest "
            "command--valve discrepancy $\\max|u_{\\text{raw}}-u_{\\text{act}}|$."
        ),
        label="tab:antiwindup_mechanism",
    )


def run_exact_robustness(
    plant: "exp02.CSTRPlant", ss: "exp02.CSTRState", foptd: "exp02.FOPTDModel", gains: dict,
    tables_dir: Path,
) -> None:
    """Plant-exact ||S||, ||T||, ||CS|| (3-state Jacobian + half-sample ZOH) and K_hf."""
    rows = []
    for name, g in gains.items():
        if name.startswith("2-DOF"):
            continue  # same L(s) as the 1-DOF loop
        rob = linearized_robustness(plant, ss, 100.0, g, theta=0.02 / 2.0)
        rows.append({
            "Method": name,
            "\\(M_s\\) (FOPTD)": f"{calculate_maximum_sensitivity_foptd(foptd, g):.2f}",
            "\\(\\|S\\|_\\infty\\) (lin.)": f"{rob['ms']:.2f}",
            "\\(\\|T\\|_\\infty\\) (lin.)": f"{rob['mt']:.2f}",
            "\\(\\|CS\\|_\\infty\\) (L/min/K)": f"{rob['cs_inf']:.1f}",
            "\\(K_{\\mathrm{hf}}=|K_p|(1+N)\\) (L/min/K)": f"{rob['k_hf']:.1f}",
        })
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "exact_robustness_table.tex",
        caption=(
            "Plant-exact robustness of the six feedback loops on the Jacobian linearization at "
            "$\\mathbf{x}_{ss}$ with the half-sample zero-order-hold delay, and the high-frequency "
            "controller gain that maps measurement noise into valve movement."
        ),
        label="tab:exact_robustness",
    )


def run_out_of_sample(
    plant: "exp02.CSTRPlant", ss: "exp02.CSTRState", gains: dict, tables_dir: Path,
    base: tuple[str, ...],
) -> None:
    """ITAE of every tuning on setpoint steps; Optimal ITAE was designed on -2 K only.

    `base` names the benchmark tunings among which the rank of Optimal ITAE is computed.
    """
    sim = exp02.ClosedLoopSimulator()
    names = list(gains)
    itae = {n: {} for n in names}
    for n, g in gains.items():
        for step in OOS_STEPS:
            pid = exp02.PIDController(g, exp02.BENCHMARK_LIMITS, AW.CLAMPING, u_bias=100.0, y_ss=ss.T)
            itae[n][step] = sim.run(
                plant, pid, ss, (0.0, 10.0), 0.02, setpoint_func=lambda t, d=step: ss.T + d
            ).metrics.itae
    rows = [
        {"Method": n} | {f"{d:+g} K": f"{itae[n][d]:.3f}" for d in OOS_STEPS} for n in names
    ]
    ranks = {d: 1 + sum(itae[n][d] < itae[exp02.OPT_ITAE][d] for n in base) for d in OOS_STEPS}
    rows.append({"Method": "Rank of Optimal ITAE among the eight benchmark tunings (1 = best)"} | {f"{d:+g} K": str(ranks[d]) for d in OOS_STEPS})
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "out_of_sample_itae.tex",
        caption=(
            "ITAE (K$\\cdot$min$^2$) of every tuning on setpoint steps of different size and sign. "
            "The Optimal ITAE gains were fitted on the $-2$~K step only (in-sample column); all other "
            "columns are out-of-sample. Same valve, directional anti-windup and $10$~min horizon."
        ),
        label="tab:out_of_sample",
    )


SIM_DT = 0.02  # min
LOAD_DT_F, LOAD_DC_FRAC = 2.0, 0.1  # K, relative
LOAD_SIGMA = 0.05  # K
SECOND_OP_Q_J = 150.0  # L/min
SOBOL_T_FINAL = 10.5  # min: 0.5 min before the step (delay line fill) + the 10 min of the benchmark
N_SEEDS = 30
NAME_EXACT = "Optimal ITAE ($M_s^{\\mathrm{lin}} \\leq 1.6$)"
NAME_JOINT_FOPTD = "Joint 2-DOF ITAE ($M_s^{\\mathrm{FOPTD}} \\leq 1.6$)"
NAME_JOINT_EXACT = "Joint 2-DOF ITAE ($M_s^{\\mathrm{lin}} \\leq 1.6$)"


def _one_dof(gains: dict) -> dict:
    """The six distinct feedback loops (2-DOF variants share L(s) with their 1-DOF twin)."""
    return {n: g for n, g in gains.items() if not n.startswith("2-DOF")}


def _step_run(plant, ss, g, aw=AW.CLAMPING, step=-2.0, t_end=10.0, limits=None, q_j=100.0, **kw):
    """Closed-loop setpoint step on the benchmark valve (or on `limits`)."""
    pid = exp02.PIDController(
        g, limits or exp02.BENCHMARK_LIMITS, aw, u_bias=q_j, y_ss=ss.T
    )
    return exp02.ClosedLoopSimulator().run(
        plant, pid, ss, (0.0, t_end), SIM_DT, setpoint_func=lambda t: ss.T + step, **kw
    )


def _ci95(v) -> float:
    """Half-width of the 95 % t-interval of the mean."""
    n = len(v)
    return float(scipy_stats.t.ppf(0.975, n - 1) * np.std(v, ddof=1) / np.sqrt(n))


def run_aw_scenarios(plant, ss, gains: dict, tables_dir: Path) -> None:
    """IAE of the seven integrator policies on the -5 K and +5 K steps and on the load profile.

    The load run is deterministic (no noise), so the table separates the policies without
    sampling uncertainty.
    """
    sim = exp02.ClosedLoopSimulator()
    load = exp02.load_disturbance_profile(plant, LOAD_DT_F, LOAD_DC_FRAC)
    scenarios = (("$-5$ K step", -5.0), ("$+5$ K step", 5.0), ("Load (deterministic)", None))
    rows = []
    for label, step in scenarios:
        for k, (name, g) in enumerate(_one_dof(gains).items()):
            row = {"Scenario": label if k == 0 else "", "Method": name}
            for vlabel, method in ABLATION_VARIANTS:
                if step is None:
                    pid = exp02.PIDController(
                        g, exp02.BENCHMARK_LIMITS, method, u_bias=100.0, y_ss=ss.T
                    )
                    res = sim.run(
                        plant, pid, ss, (0.0, 15.0), SIM_DT,
                        setpoint_func=lambda t: ss.T, disturbance_func=load,
                    )
                else:
                    res = _step_run(plant, ss, g, method, step)
                row[vlabel] = f"{res.metrics.iae:.2f}"
            rows.append(row)
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "antiwindup_scenarios.tex",
        caption=(
            "IAE (K$\\cdot$min) of the seven integrator policies of Table~\\ref{tab:antiwindup_ablation} "
            "on a $-5$~K step, a $+5$~K step ($10$~min) and the noise-free load profile of "
            "Section~\\ref{subsec:load_results} ($15$~min)."
        ),
        label="tab:antiwindup_scenarios",
    )


SMAX_GRID = (20.0, 30.0, 45.0, 60.0, 80.0, 120.0, 160.0, 240.0, 320.0)  # L/min^2
TT_STEPS = (-2.0, -5.0, 5.0)


def run_smax_map(plant, ss, gains: dict, tables_dir: Path, figures_dir: Path) -> None:
    """Regime map: IAE of the -2 K step against the slew-rate limit S_max, five integrator policies.

    The gains stay those designed at S_max = 80 L/min^2. The map shows where the slew-rate
    trigger matters (IAE of amplitude-only clamping over IAE of the rate-aware rule) and where
    sign-blind clamping latches (final error near -16.7 K).
    """
    policies = (
        ("None", AW.NONE),
        ("Back-calc.", AW.BACK_CALCULATION),
        ("Sign-blind amp.", AW.CLAMPING_NAIVE),
        ("Amp. direct.", AW.CLAMPING_POS_DIRECTIONAL),
        ("Amp.+rate direct.", AW.CLAMPING),
    )
    base = _one_dof(gains)
    out: dict = {}
    for name, g in base.items():
        for label, method in policies:
            for smax in SMAX_GRID:
                lim = replace(exp02.BENCHMARK_LIMITS, max_slew_rate=smax)
                res = _step_run(plant, ss, g, method, limits=lim)
                out[(name, label, smax)] = (res.metrics.iae, res.states[-1, 1] - (ss.T - 2.0))
    cols = {s_: f"$S_{{\\max}}={s_:g}$" for s_ in SMAX_GRID}
    rows = []
    for name in base:
        iae = lambda lab, s_: out[(name, lab, s_)][0]  # noqa: E731
        rows.append({"Method": name, "Quantity": "$\\mathrm{IAE}_{\\mathrm{amp}}/\\mathrm{IAE}_{\\mathrm{rate}}$"}
                    | {cols[s_]: f"{iae('Amp. direct.', s_) / iae('Amp.+rate direct.', s_):.1f}" for s_ in SMAX_GRID})
        rows.append({"Method": "", "Quantity": "IAE rate-aware (K$\\cdot$min)"}
                    | {cols[s_]: f"{iae('Amp.+rate direct.', s_):.2f}" for s_ in SMAX_GRID})
        rows.append({"Method": "", "Quantity": "Sign-blind $T(t_f)-T_{sp}$ (K)"}
                    | {cols[s_]: f"{out[(name, 'Sign-blind amp.', s_)][1]:+.1f}" for s_ in SMAX_GRID})
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "smax_regime_map.tex",
        caption=(
            "Regime map over the valve slew-rate limit ($-2$~K step, gains designed at "
            "$S_{\\max} = 80$~L/min$^2$). First row of each tuning: IAE of amplitude-only "
            "directional clamping over IAE of the rate-aware rule (values near $1$: the rate "
            "trigger is irrelevant); second: IAE of the rate-aware rule; third: final error of "
            "sign-blind clamping ($\\approx -16.7$~K: valve latched at full cooling)."
        ),
        label="tab:smax_map",
    )
    setup_ieee_style(single_column=False)
    fig_w, _ = exp02.get_figure_dimensions(columns=2)
    fig, axes = plt.subplots(2, 3, figsize=(fig_w, 4.2), sharex=True, dpi=300)
    for ax, name in zip(axes.flat, base):
        for label, _ in policies:
            ax.plot(SMAX_GRID, [out[(name, label, s_)][0] for s_ in SMAX_GRID], marker="o",
                    markersize=2.5, linewidth=1.0, label=label)
        ax.axvline(80.0, color="gray", linestyle=":", linewidth=0.8)
        ax.set_xscale("log")
        ax.set_xticks([20, 40, 80, 160, 320], ["20", "40", "80", "160", "320"])
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_yscale("log")
        ax.set_title(name.split(" (")[0], fontsize=8.0)
        ax.grid(True, which="both", linestyle=":", alpha=0.5)
    for ax in axes[1]:
        ax.set_xlabel(r"$S_{\max}$ (L/min$^2$)")
    for ax in axes[:, 0]:
        ax.set_ylabel(r"IAE (K$\cdot$min)")
    h, lab = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=5, fontsize=6.5, columnspacing=0.8)
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.93])
    exp02.save_grouped(fig, figures_dir / "fig_smax_map")


def run_tt_curve(plant, ss, gains: dict, tables_dir: Path, figures_dir: Path) -> None:
    """IAE of back-calculation against T_t over [0.1 T_d, 10 T_i]; physical range [T_d, T_i].

    The discrete update multiplies I by (1 - dt/T_t): it over-corrects for T_t < dt and diverges
    below dt/2, so the grid starts at 0.525 dt (plus the 0.1 T_t point of the earlier scan). The directional rule is the horizontal reference.
    """
    base = _one_dof(gains)
    rows, summary, curves, direct, tvmp = [], [], {}, {}, []
    for name, g in base.items():
        grid = np.unique(np.concatenate([
            # lower end: below ~dt/2 the discrete update (1 - dt/T_t) I diverges (no IAE)
            np.geomspace(max(0.1 * g.td, 0.525 * SIM_DT), 10.0 * g.ti, 21),
            [g.td, g.tt, g.ti, SIM_DT, 0.1 * g.tt],
        ]))
        for step in TT_STEPS:
            curves[(name, step)] = (grid, np.array([
                _step_run(plant, ss, replace(g, tt=float(t)), AW.BACK_CALCULATION, step).metrics.iae
                for t in grid
            ]))
            direct[(name, step)] = _step_run(plant, ss, g, AW.CLAMPING, step).metrics.iae
        inside = (grid >= g.td - 1e-12) & (grid <= g.ti + 1e-12)
        ratio = np.array([curves[(name, st)][1] / direct[(name, st)] for st in TT_STEPS])  # 3 x n
        k_mm = int(np.argmin(np.where(inside, ratio.max(axis=0), np.inf)))  # minimax over steps
        k_cv = int(np.argmin(np.where(inside, ratio[0], np.inf)))  # chosen on the -2 K design step
        k_sq, k_ti = int(np.argmin(np.abs(grid - g.tt))), int(np.argmin(np.abs(grid - g.ti)))
        k_free = int(np.argmin(ratio[0]))  # design-step choice without the [T_d, T_i] restriction
        for i, step in enumerate(TT_STEPS):
            bc = _step_run(plant, ss, replace(g, tt=float(grid[k_cv])), AW.BACK_CALCULATION, step).metrics
            dr = _step_run(plant, ss, g, AW.CLAMPING, step).metrics
            tvmp.append({
                "Method": name if i == 0 else "",
                "Step": f"${step:+g}$ K",
                "IAE dir.": f"{dr.iae:.2f}", "IAE BC": f"{bc.iae:.2f}",
                "TV dir. (L/min)": f"{dr.tv:.1f}", "TV BC (L/min)": f"{bc.tv:.1f}",
                "\\(M_p\\) dir. (\\%)": f"{dr.overshoot_pct:.1f}",
                "\\(M_p\\) BC (\\%)": f"{bc.overshoot_pct:.1f}",
            })
        for i, step in enumerate(TT_STEPS):
            rows.append({
                "Method": name if i == 0 else "",
                "Step": f"${step:+g}$ K",
                "IAE dir.": f"{direct[(name, step)]:.2f}",
                "IAE $T_t^{\\mathrm{mm}}$": f"{curves[(name, step)][1][k_mm]:.2f}",
                "IAE $\\sqrt{T_iT_d}$": f"{curves[(name, step)][1][k_sq]:.2f}",
                "IAE $T_t=T_i$": f"{curves[(name, step)][1][k_ti]:.2f}",
                "IAE $T_t^{\\mathrm{cv}}$": f"{curves[(name, step)][1][k_cv]:.2f}",
            })
        summary.append({
            "Method": name,
            "\\([T_d, T_i]\\)": f"[{g.td:.3f}, {g.ti:.3f}]",
            "\\(T_t^{\\mathrm{cv}}\\)": f"{grid[k_cv]:.3f}",
            "cv: \\(\\pm 5\\)~K": f"{ratio[1:, k_cv].max():.2f}",
            "free \\(T_t^{\\mathrm{cv}}\\)": f"{grid[k_free]:.3f}",
            "in range": "yes" if inside[k_free] else "no",
            "free: \\(\\pm 5\\)~K": f"{ratio[1:, k_free].max():.2f}",
            "\\(T_t^{\\mathrm{mm}}\\)": f"{grid[k_mm]:.3f}",
            "mm": f"{ratio[:, k_mm].max():.2f}",
            "\\(\\sqrt{T_iT_d}\\)": f"{ratio[:, k_sq].max():.2f}",
            "\\(T_i\\)": f"{ratio[:, k_ti].max():.2f}",
        })
    exp02.export_latex_table(
        data=summary,
        output_path=tables_dir / "antiwindup_tt_summary.tex",
        caption=(
            "One tracking constant per loop (times in min). Ratios are the worst IAE of "
            "back-calculation over that of the directional rule (Eq.~\\eqref{eq:clamping_antiwindup}); "
            "above $1$, back-calculation is worse. $T_t^{\\mathrm{cv}}$: chosen inside $[T_d, T_i]$ on "
            "the $-2$~K design step, judged on $\\pm 5$~K; free: the same choice without the range "
            "restriction; $T_t^{\\mathrm{mm}}$: minimax over the $-2$, $-5$ and $+5$~K steps inside "
            "$[T_d, T_i]$; last two columns: worst ratio over the three steps with the defaults "
            "$T_t = \\sqrt{T_iT_d}$ and $T_t = T_i$."
        ),
        label="tab:antiwindup_tt_summary",
    )
    exp02.export_latex_table(
        data=tvmp,
        output_path=tables_dir / "antiwindup_tt_tvmp.tex",
        caption=(
            "Back-calculation with $T_t^{\\mathrm{cv}}$ (BC) against the directional rule (dir., "
            "Eq.~\\eqref{eq:clamping_antiwindup}) on the three steps: IAE (K$\\cdot$min), valve travel "
            "TV and overshoot $M_p$."
        ),
        label="tab:antiwindup_tt_tvmp",
    )
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "antiwindup_tt_sweep.tex",
        caption=(
            "IAE (K$\\cdot$min) of the directional rule (``dir.'') and of back-calculation with "
            "$T_t^{\\mathrm{mm}}$ and $T_t^{\\mathrm{cv}}$ (Table~\\ref{tab:antiwindup_tt_summary}), "
            "$T_t = \\sqrt{T_iT_d}$ and $T_t = T_i$ (the value associated with conditioning "
            "techniques \\cite{peng1996nonlinear}). The full curves are in Fig.~\\ref{fig:tt_curve}."
        ),
        label="tab:antiwindup_tt_sweep",
    )
    setup_ieee_style(single_column=False)
    fig_w, _ = exp02.get_figure_dimensions(columns=2)
    fig, axes = plt.subplots(2, 3, figsize=(fig_w, 4.2), dpi=300)
    colors = {-2.0: "#0072B2", -5.0: "#D55E00", 5.0: "#009E73"}
    for ax, (name, g) in zip(axes.flat, base.items()):
        ax.axvspan(g.td, g.ti, color="#dddddd", alpha=0.6, linewidth=0)
        ax.axvline(SIM_DT, color="gray", linestyle=":", linewidth=0.8)
        for step in TT_STEPS:
            grid, iae = curves[(name, step)]
            ax.plot(grid, iae, color=colors[step], marker="o", markersize=2.2, linewidth=1.0,
                    label=f"back-calc., {step:+g} K")
            ax.axhline(direct[(name, step)], color=colors[step], linestyle="--", linewidth=0.8)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(name.split(" (")[0], fontsize=8.0)
        ax.grid(True, which="both", linestyle=":", alpha=0.5)
    for ax in axes[1]:
        ax.set_xlabel(r"$T_t$ (min)")
    for ax in axes[:, 0]:
        ax.set_ylabel(r"IAE (K$\cdot$min)")
    h, lab = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=3, fontsize=6.5)
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.93])
    exp02.save_grouped(fig, figures_dir / "fig_tt_curve")


class _Tap:
    """Delegating controller that records the PID diagnostics (P, I, D, u_raw) at every sample."""

    def __init__(self, pid) -> None:
        self.pid, self.u_bias, self.rows = pid, pid.u_bias, []

    def reset(self, *args, **kwargs) -> None:
        self.pid.reset(*args, **kwargs)

    def compute(self, setpoint, measurement, dt):
        u, diag = self.pid.compute(setpoint=setpoint, measurement=measurement, dt=dt)
        self.rows.append((diag["i"], diag["u_unconstrained"]))
        return u, diag


def plot_mechanism(plant, ss, gains: dict, figures_dir: Path) -> None:
    """u_raw, u_act, e and the integrator state of ZN on the -2 K step under three policies."""
    g = gains["Ziegler-Nichols"]
    policies = (("No anti-windup", AW.NONE), ("Sign-blind amp.", AW.CLAMPING_NAIVE),
                ("Directional rate-aware", AW.CLAMPING))
    setup_ieee_style(single_column=False)
    fig_w, _ = exp02.get_figure_dimensions(columns=2)
    fig, axes = plt.subplots(3, 3, figsize=(fig_w, 4.8), sharex=True, sharey="row", dpi=300)
    for col, (title, method) in enumerate(policies):
        tap = _Tap(exp02.PIDController(g, exp02.BENCHMARK_LIMITS, method, u_bias=100.0, y_ss=ss.T))
        res = exp02.ClosedLoopSimulator().run(
            plant, tap, ss, (0.0, 10.0), SIM_DT, setpoint_func=lambda t: ss.T - 2.0
        )
        i_state = np.array([r[0] for r in tap.rows])
        u_raw = np.array([r[1] for r in tap.rows])
        axes[0, col].plot(res.t, u_raw, color="#D55E00", linewidth=1.0, label=r"$u_{\mathrm{raw}}$")
        axes[0, col].plot(res.t, res.u_applied, color="#0072B2", linewidth=1.0, label=r"$u_{\mathrm{act}}$")
        axes[1, col].plot(res.t, (ss.T - 2.0) - res.states[:, 1], color="#333333", linewidth=1.0)
        axes[2, col].plot(res.t, i_state, color="#009E73", linewidth=1.0)
        axes[0, col].set_title(title, fontsize=8.0)
        axes[2, col].set_xlabel("Time $t$ (min)")
    axes[0, 0].set_yscale("symlog", linthresh=300.0)
    axes[2, 0].set_yscale("symlog", linthresh=300.0)
    axes[0, 0].set_ylabel("Valve command (L/min)")
    axes[1, 0].set_ylabel(r"Error $e = T_{sp}-T$ (K)")
    axes[2, 0].set_ylabel(r"Integrator $I$ (L/min)")
    axes[0, 0].legend(fontsize=6.0, loc="upper left")
    for ax in axes.flat:
        ax.grid(True, which="both", linestyle=":", alpha=0.5)
    fig.tight_layout()
    exp02.save_grouped(fig, figures_dir / "fig_mechanism")


def run_second_operating_point(q_j: float, tables_dir: Path) -> None:
    """Ablation of the seven integrator policies at a second operating point (re-identified, re-tuned)."""
    plant = exp02.CSTRPlant()
    ss2 = plant.find_steady_state(q_j=q_j)
    foptd2 = exp02.identify_nominal_foptd(plant, ss2, q_j)
    analytical = {
        "Ziegler-Nichols": exp02.tune_analytical(foptd2, rule=exp02.TuningRule.ZIEGLER_NICHOLS_PID),
        "Cohen-Coon": exp02.tune_analytical(foptd2, rule=exp02.TuningRule.COHEN_COON_PID),
        "Tyreus-Luyben": exp02.tune_analytical(foptd2, rule=exp02.TuningRule.TYREUS_LUYBEN),
        "AMIGO": exp02.tune_analytical(foptd2, rule=exp02.TuningRule.AMIGO),
        "Skogestad SIMC": exp02.tune_analytical(foptd2, rule=exp02.TuningRule.SKOGESTAD_SIMC_PID, tau_c=0.4),
    }
    rows = []
    for name, g in analytical.items():
        row = {"Method": name, "\\(K_p\\)": f"{g.kp:.2f}"}
        for label, method in ABLATION_VARIANTS:
            m = _step_run(plant, ss2, g, method, q_j=q_j).metrics
            row[label] = f"{m.iae:.2f} / {m.overshoot_pct:.1f}"
        rows.append(row)
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "antiwindup_second_op.tex",
        caption=(
            f"Anti-windup ablation at a second operating point ($q_{{j,ss}} = {q_j:g}$~L/min, "
            f"$T_{{ss}} = {ss2.T:.2f}$~K; FOPTD $K = {foptd2.k_p:.4f}$~K/(L/min), "
            f"$\\tau = {foptd2.tau:.3f}$~min, $\\theta = {foptd2.theta:.4f}$~min, re-identified; "
            "analytical rules re-tuned). $-2$~K step, same valve; IAE (K$\\cdot$min) / overshoot (\\%)."
        ),
        label="tab:antiwindup_second_op",
    )


def _loop_polys(plant, ss, g, k_scale: float, t_scale: float, extra_delay: float):
    """Polynomials of L(s) = k G(t_scale s) C(s) P(s): exact 3-state plant, PID, Pade-4 delay.

    t_scale > 1 slows every plant pole and zero (all time constants, tau included); the
    half-sample zero-order-hold delay plus `extra_delay` is a 4th-order Pade approximation.
    Returns (num, den, parts) with numpy polynomial coefficients, highest power first.
    """
    from math import factorial

    from scipy.signal import ss2tf

    a, b = plant.linearize(ss, 100.0)
    num_p, den_p = ss2tf(a, b, np.array([[0.0, 1.0, 0.0]]), np.zeros((1, 1)))
    num_p = np.trim_zeros(num_p[0], "f") * k_scale
    scale = lambda c: c * t_scale ** np.arange(len(c) - 1, -1, -1)  # noqa: E731
    num_p, den_p = scale(num_p), scale(den_p)
    tau_f = g.td / g.n_filter if g.td > 0 else 0.0
    # C(s) = Kp [(Ti s)(tau_f s + 1) + (tau_f s + 1) + Ti Td s^2] / (Ti s (tau_f s + 1))
    num_c = g.kp * np.polyadd(np.polyadd(np.polymul([g.ti, 0.0], [tau_f, 1.0]), [tau_f, 1.0]),
                              [g.ti * g.td, 0.0, 0.0])
    den_c = np.polymul([g.ti, 0.0], [tau_f, 1.0])
    theta = SIM_DT / 2.0 + extra_delay
    n = 4  # diagonal Pade: sum_k c_k (-theta s)^k / sum_k c_k (theta s)^k
    c = [factorial(2 * n - k) * factorial(n) / (factorial(2 * n) * factorial(k) * factorial(n - k))
         for k in range(n + 1)]
    num_d = np.array([c[k] * (-theta) ** k for k in range(n, -1, -1)])
    den_d = np.array([c[k] * theta ** k for k in range(n, -1, -1)])
    return (num_p, den_p), (num_c, den_c), (num_d, den_d), theta


def _stability_and_ms(plant, ss, g, k_scale, t_scale, extra_delay):
    """(stable?, M_s) of one perturbed exact loop; M_s is meaningful only if stable."""
    (np_, dp), (nc, dc), (nd, dd), theta = _loop_polys(plant, ss, g, k_scale, t_scale, extra_delay)
    char = np.polyadd(np.polymul(np.polymul(dp, dc), dd), np.polymul(np.polymul(np_, nc), nd))
    stable = bool(np.max(np.roots(char).real) < -1e-9)
    w = np.logspace(-3, 3, 4000)
    s = 1j * w
    loop = (np.polyval(np_, s) / np.polyval(dp, s)) * (np.polyval(nc, s) / np.polyval(dc, s)) * np.exp(-s * theta)
    return stable, float(np.max(np.abs(1.0 / (1.0 + loop))))


def run_model_error_test(plant, ss, foptd, gains: dict, extra: dict, tables_dir: Path) -> None:
    """Same exact plant, same perturbations for every tuning: stability of each corner and M_s.

    Corners: loop gain x {0.8, 1, 1.2}, all plant time constants (tau included) x {0.8, 1, 1.2}
    and an extra delay of {0, 0.2 theta_FOPTD}; 18 loops per tuning. M_s is reported only over
    the stable corners.
    """
    designs = {**_one_dof(gains), NAME_EXACT: extra[NAME_EXACT]}
    rows = []
    for name, g in designs.items():
        res = [
            _stability_and_ms(plant, ss, g, k, t, d)
            for k in (0.8, 1.0, 1.2) for t in (0.8, 1.0, 1.2) for d in (0.0, 0.2 * foptd.theta)
        ]
        ms_stable = [m for ok, m in res if ok]
        rows.append({
            "Tuning": name,
            "\\(M_s^{\\mathrm{lin}}\\) nominal": f"{_ms_lin(plant, ss, g):.2f}",
            "unstable corners (of 18)": str(sum(not ok for ok, _ in res)),
            "worst \\(M_s\\), stable corners": f"{max(ms_stable):.2f}" if ms_stable else "--",
        })
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "model_error_ms.tex",
        caption=(
            "Robustness to model error on the exact plant, identical for every tuning: loop gain, "
            "all plant time constants ($\\tau$ included) scaled by $0.8$, $1$ and $1.2$ and an extra "
            "delay of $0$ or $0.2\\,\\theta_{\\mathrm{FOPTD}}$ ($18$ loops each). Stability is decided by "
            "the roots of the closed-loop polynomial (4th-order Pad\\'e delay); $M_s$ is reported over "
            "the stable corners only. Deadband and stiction are not part of this test."
        ),
        label="tab:model_error",
    )


class _Deadband:
    """Valve backlash between controller and plant.

    The position follows the command only after the command has moved by more than half the
    band; the anti-windup still sees the command, not the position.
    """

    def __init__(self, pid, band: float) -> None:
        self.pid, self.band, self.u_bias = pid, band, pid.u_bias
        self.pos = pid.u_bias

    def reset(self, *args, **kwargs) -> None:
        self.pid.reset(*args, **kwargs)
        self.pos = self.pid.u_bias

    def compute(self, setpoint, measurement, dt):
        u, diag = self.pid.compute(setpoint=setpoint, measurement=measurement, dt=dt)
        half = 0.5 * self.band
        if u > self.pos + half:
            self.pos = u - half
        elif u < self.pos - half:
            self.pos = u + half
        return self.pos, diag


def run_deadband_test(plant, ss, gains: dict, tables_dir: Path) -> None:
    """IAE of the seven policies on the -2 K step with a valve deadband of 0, 3 and 6 L/min."""
    sim = exp02.ClosedLoopSimulator()
    rows = []
    for band in (0.0, 3.0, 6.0):
        for k, (name, g) in enumerate(_one_dof(gains).items()):
            row = {"Deadband (L/min)": f"{band:g}" if k == 0 else "", "Method": name}
            for label, method in ABLATION_VARIANTS:
                pid = exp02.PIDController(g, exp02.BENCHMARK_LIMITS, method, u_bias=100.0, y_ss=ss.T)
                res = sim.run(
                    plant, _Deadband(pid, band), ss, (0.0, 10.0), SIM_DT,
                    setpoint_func=lambda t: ss.T - 2.0,
                )
                row[label] = f"{res.metrics.iae:.2f}"
            rows.append(row)
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "antiwindup_deadband.tex",
        caption=(
            "IAE (K$\\cdot$min) of the seven integrator policies on the $-2$~K step with a valve "
            "deadband (backlash) of $0$, $3$ and $6$~L/min between the controller and the plant; "
            "the anti-windup logic sees the command, not the backlash position. Stiction is not modelled."
        ),
        label="tab:antiwindup_deadband",
    )


def run_smax_retuned(plant, ss, foptd, gains: dict, tables_dir: Path) -> None:
    """Optimal ITAE re-optimized at every S_max: does the rate trigger still matter?"""
    opt = gains[exp02.OPT_ITAE]
    ok = lambda g: calculate_maximum_sensitivity_foptd(foptd, g) <= 1.6 + 1e-3  # noqa: E731
    rows = []
    for smax in SMAX_GRID:
        lim = replace(exp02.BENCHMARK_LIMITS, max_slew_rate=smax)
        g = _multistart(plant, ss, [opt, None], ok, limits=lim, foptd=foptd, ms_model="foptd")
        amp = _step_run(plant, ss, g, AW.CLAMPING_POS_DIRECTIONAL, limits=lim).metrics.iae
        rate = _step_run(plant, ss, g, AW.CLAMPING, limits=lim).metrics.iae
        rows.append({
            "\\(S_{\\max}\\) (L/min$^2$)": f"{smax:g}",
            "\\(K_p\\)": f"{g.kp:.1f}", "\\(T_i\\) (min)": f"{g.ti:.3f}", "\\(T_d\\) (min)": f"{g.td:.3f}",
            "IAE amp.-only": f"{amp:.2f}", "IAE rate-aware": f"{rate:.2f}",
            "ratio": f"{amp / rate:.1f}",
        })
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "smax_retuned.tex",
        caption=(
            "Optimal ITAE ($M_s^{\\mathrm{FOPTD}} \\le 1.6$) re-optimized at each slew-rate limit "
            "(multi-start from the $S_{\\max} = 80$ optimum and the default guess, one restart): "
            "gains and IAE ($-2$~K step) of amplitude-only directional clamping and of the rate-aware "
            "rule. Compare with the fixed-gain map of Table~\\ref{tab:smax_map}."
        ),
        label="tab:smax_retuned",
    )


def _shapley_effects(x: np.ndarray, y: np.ndarray, seed: int = 0) -> tuple[np.ndarray, float]:
    """Shapley effects of dependent inputs from given data (random-forest conditional means).

    v(S) = cross-validated R^2 of E[Y | X_S] (an estimate of Var(E[Y|X_S])/Var(Y), biased low),
    exact Shapley weights over the 2^d subsets, normalized by v(all). Returns (effects, v(all)).
    """
    from itertools import combinations
    from math import factorial

    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import cross_val_predict

    d = x.shape[1]
    var = float(np.var(y))
    v: dict[tuple, float] = {(): 0.0}
    for r in range(1, d + 1):
        for sub in combinations(range(d), r):
            model = RandomForestRegressor(
                n_estimators=60, min_samples_leaf=5, random_state=seed, n_jobs=-1
            )
            pred = cross_val_predict(model, x[:, sub], y, cv=5)
            v[sub] = max(0.0, 1.0 - float(np.mean((y - pred) ** 2)) / var)
    phi = np.zeros(d)
    for i in range(d):
        others = [j for j in range(d) if j != i]
        for r in range(d):
            w = factorial(r) * factorial(d - r - 1) / factorial(d)
            for sub in combinations(others, r):
                phi[i] += w * (v[tuple(sorted((*sub, i)))] - v[tuple(sorted(sub))])
    return phi / v[tuple(range(d))], v[tuple(range(d))]


def _itae6(plant, ss, g, limits=None) -> float:
    """Design objective: ITAE of the -2 K step over 6 min on the benchmark valve."""
    return _step_run(plant, ss, g, step=-2.0, t_end=6.0, limits=limits).metrics.itae


def _ms_lin(plant, ss, g) -> float:
    """M_s of the Jacobian loop with the half-sample zero-order-hold delay."""
    return linearized_robustness(plant, ss, 100.0, g, theta=SIM_DT / 2.0)["ms"]


def _multistart(plant, ss, starts, feasible, limits=None, **kw):
    """Best feasible Nelder-Mead optimum over `starts`, restarted once from the winner."""

    def tune(g0):
        return tune_by_optimization(
            plant=plant, nominal_state=ss, q_j_ss=100.0, target_dT=-2.0, initial_gains=g0,
            criterion=OptimizationCriterion.ITAE, max_ms=1.6, t_sim=6.0, dt=SIM_DT,
            limits=limits or exp02.BENCHMARK_LIMITS, **kw,
        )

    best = None
    for round_starts in (starts, None):
        pool = [tune(g0) for g0 in (round_starts if round_starts is not None else [best])]
        pool = [g for g in pool if feasible(g)] + ([best] if best else [])
        best = min(pool, key=lambda g: _itae6(plant, ss, g, limits))
    return best


def run_robust_constraint_cost(plant, ss, foptd, gains: dict, tables_dir: Path) -> dict:
    """Cost of imposing M_s <= 1.6 on the FOPTD instead of the exact loop, and joint 2-DOF optima.

    Returns the extra tunings (name -> gains) for reuse in the out-of-sample table.
    """
    foptd_ok = lambda g: calculate_maximum_sensitivity_foptd(foptd, g) <= 1.6 + 1e-3  # noqa: E731
    lin_ok = lambda g: _ms_lin(plant, ss, g) <= 1.6 + 1e-3  # noqa: E731
    base = _one_dof(gains)
    opt = gains[exp02.OPT_ITAE]
    starts = [None] + [g for g in base.values() if lin_ok(g)]
    exact = _multistart(plant, ss, starts, lin_ok, foptd=foptd, ms_model="exact")
    w0 = lambda g: replace(g, beta=0.5, gamma=0.0)  # noqa: E731
    joint_f = _multistart(
        plant, ss, [w0(opt), opt], foptd_ok, foptd=foptd, ms_model="foptd", optimize_weights=True
    )
    joint_e = _multistart(
        plant, ss, [w0(exact), exact, w0(opt)], lin_ok, foptd=foptd, ms_model="exact",
        optimize_weights=True,
    )
    rows = []
    designs = (
        (exp02.OPT_ITAE, opt), (exp02.OPT_ITAE_2DOF, gains[exp02.OPT_ITAE_2DOF]),
        (NAME_JOINT_FOPTD, joint_f), (NAME_EXACT, exact), (NAME_JOINT_EXACT, joint_e),
    )
    for name, g in designs:
        m = _step_run(plant, ss, g).metrics
        rob = linearized_robustness(plant, ss, 100.0, g, theta=SIM_DT / 2.0)
        w = np.logspace(-2, 3, 4000)
        pm = phase_margin_deg(loop_gain_linearized(plant, ss, 100.0, g, w, theta=SIM_DT / 2.0), w)
        rows.append({
            "Tuning": name,
            "\\(K_p\\)": f"{g.kp:.2f}", "\\(T_i\\) (min)": f"{g.ti:.3f}", "\\(T_d\\) (min)": f"{g.td:.3f}",
            "\\(\\beta\\)": f"{g.beta:.2f}", "\\(\\gamma\\)": f"{g.gamma:.2f}",
            "\\(M_s^{\\mathrm{FOPTD}}\\)": f"{calculate_maximum_sensitivity_foptd(foptd, g):.2f}",
            "\\(M_s^{\\mathrm{lin}}\\)": f"{rob['ms']:.2f}",
            "PM$^{\\mathrm{lin}}$ ($^\\circ$)": f"{pm:.1f}",
            "\\(K_{\\mathrm{hf}}\\)": f"{rob['k_hf']:.0f}",
            "IAE": f"{m.iae:.3f}", "ITAE": f"{m.itae:.3f}",
            "\\(M_p\\) (\\%)": f"{m.overshoot_pct:.1f}", "TV": f"{m.tv:.1f}",
            "ITAE $-5$ K": f"{_step_run(plant, ss, g, step=-5.0).metrics.itae:.3f}",
            "ITAE $+5$ K": f"{_step_run(plant, ss, g, step=5.0).metrics.itae:.3f}",
        })
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "robust_constraint_cost.tex",
        caption=(
            "Cost of the design-model constraint. Each tuning minimizes the ITAE of the $-2$~K "
            "step ($6$~min) subject to $M_s \\le 1.6$ evaluated on the dead-time FOPTD "
            "($M_s^{\\mathrm{FOPTD}}$) or on the exact Jacobian loop with the half-sample "
            "zero-order hold ($M_s^{\\mathrm{lin}}$); ``joint'' rows optimize $(K_p, T_i, T_d, \\beta, \\gamma)$ "
            "together, the 2-DOF row with $\\beta = 0.5$ is the fixed-weight variant of "
            "Table~\\ref{tab:classical_benchmark}. ITAE in K$\\cdot$min$^2$, IAE in K$\\cdot$min, "
            "TV in L/min, $K_{\\mathrm{hf}}$ in L/min/K, PM at the highest gain crossover."
        ),
        label="tab:constraint_cost",
    )
    return {NAME_EXACT: exact, NAME_JOINT_FOPTD: joint_f, NAME_JOINT_EXACT: joint_e}


def run_load_replicated(plant, ss, pids: dict, tables_dir: Path) -> None:
    """Load profile with N_SEEDS noise realizations, without and with the measurement filter."""
    load = exp02.load_disturbance_profile(plant, LOAD_DT_F, LOAD_DC_FRAC)
    ceiling = exp02.BENCHMARK_LIMITS.max_slew_rate * 15.0

    def one(name: str, tau: float, seed: int):
        res = exp02.ClosedLoopSimulator().run(
            plant, pids[name](), ss, (0.0, 15.0), SIM_DT, setpoint_func=lambda t: ss.T,
            disturbance_func=load, noise_std=LOAD_SIGMA, seed=300 + seed, meas_filter_tau=tau,
        )
        dev = np.abs(res.states[:, 1] - ss.T)
        return name, tau, res.metrics.iae, float(dev[res.t >= 2.0].max()), res.metrics.tv

    taus = (0.0, MEASUREMENT_TAU_F)
    out = Parallel(n_jobs=-1)(
        delayed(one)(n, tau, k) for n in pids for tau in taus for k in range(N_SEEDS)
    )
    rows = []
    for name in pids:
        for tau in taus:
            sel = [o for o in out if o[0] == name and o[1] == tau]
            iae, peak, tv = (np.array([o[i] for o in sel]) for i in (2, 3, 4))
            rows.append({
                "Method": name, "\\(\\tau_m\\) (min)": f"{tau:.2f}",
                "IAE": f"{iae.mean():.2f} $\\pm$ {_ci95(iae):.2f}",
                "Peak dev. (K)": f"{peak.mean():.2f} $\\pm$ {_ci95(peak):.2f}",
                "TV (L/min)": f"{tv.mean():.0f} $\\pm$ {_ci95(tv):.0f}",
                "TV/ceiling (\\%)": f"{100.0 * tv.mean() / ceiling:.0f}",
            })
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "load_replicated.tex",
        caption=(
            f"Load profile of Section~\\ref{{subsec:load_results}} with {N_SEEDS} independent noise "
            f"realizations ($\\sigma = {LOAD_SIGMA:g}$~K), without ($\\tau_m = 0$) and with "
            f"($\\tau_m = {MEASUREMENT_TAU_F:g}$~min) measurement filter: mean $\\pm$ half-width of the "
            f"$95\\%$ $t$-interval. Errors are measured on the true temperature; the TV ceiling is "
            f"$S_{{\\max}}t_f = {ceiling:.0f}$~L/min."
        ),
        label="tab:load_replicated",
    )


def run_n_design_sweep(plant, ss, gains: dict, tables_dir: Path) -> None:
    """Derivative-filter coefficient N as a design variable for ZN and CC."""
    sigmas = (0.01, 0.05)

    def noisy(g, sigma, seed):
        res = _step_run(plant, ss, g, noise_std=sigma, seed=100 + seed)  # seeds of the noise campaign
        return res.metrics.iae, res.metrics.tv

    rows = []
    for name in ("Ziegler-Nichols", "Cohen-Coon"):
        for n in (3, 5, 10):
            g = replace(gains[name], n_filter=float(n))
            rob = linearized_robustness(plant, ss, 100.0, g, theta=SIM_DT / 2.0)
            det = _step_run(plant, ss, g).metrics
            row = {
                "Method": name, "\\(N\\)": str(n),
                "\\(K_{\\mathrm{hf}}\\) (L/min/K)": f"{rob['k_hf']:.0f}",
                "IAE (noise-free)": f"{det.iae:.3f}", "\\(M_p\\) (\\%)": f"{det.overshoot_pct:.1f}",
            }
            for sigma in sigmas:
                mc = np.array(
                    Parallel(n_jobs=-1)(delayed(noisy)(g, sigma, k) for k in range(N_SEEDS))
                )
                row[f"IAE ($\\sigma={sigma:g}$)"] = f"{mc[:, 0].mean():.2f} $\\pm$ {_ci95(mc[:, 0]):.2f}"
                row[f"TV ($\\sigma={sigma:g}$)"] = f"{mc[:, 1].mean():.0f} $\\pm$ {_ci95(mc[:, 1]):.0f}"
            rows.append(row)
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "n_design_sweep.tex",
        caption=(
            "Derivative-filter coefficient $N$ ($\\tau_f = T_d/N$) as a design variable for the "
            "empirical rules, $-2$~K step, unfiltered measurement; $K_{\\mathrm{hf}} = |K_p|(1+N)$ equals "
            "$\\|CS\\|_\\infty$ to within $0.3$~L/min/K in every row. Noise columns: mean $\\pm$ $95\\%$ "
            f"half-width over {N_SEEDS} realizations; TV in L/min, IAE in K$\\cdot$min."
        ),
        label="tab:n_design",
    )


def run_sobol_margin_test(plant, ss, gains: dict, figures_dir: Path, tables_dir: Path) -> None:
    """Sobol campaign (benchmark sampling and horizon) plus the heat-removal-margin analyses.

    u_req is the steady coolant flow that holds the new setpoint on the perturbed plant
    (closed form). Samples with u_req > u_max cannot be held by any controller; the first-order
    indices are therefore also estimated on the feasible subset with the given-data RBD-FAST
    estimator (the Saltelli design does not survive the removal of rows).
    """
    from SALib.analyze import rbd_fast

    limits = exp02.BENCHMARK_LIMITS
    raw: dict = {}
    exp02.run_sobol_uncertainty_campaign(
        gains, 100.0, limits, figures_dir, tables_dir, raw=raw, dt=SIM_DT, t_final=SOBOL_T_FINAL
    )
    nom, target = CSTRParameters(), ss.T - 2.0
    names = exp02.CSTR_UNCERTAINTY_PROBLEM["names"]

    def plant_of(x):
        return exp02.CSTRPlant(CSTRParameters(
            E_over_R=nom.E_over_R * float(x[0]), UA=nom.UA * float(x[1]), C_Af=float(x[2])
        ))

    samples = next(iter(raw.values()))[0]
    u_req = np.array([plant_of(x).required_coolant_flow(target) for x in samples])
    feasible = u_req <= limits.u_max
    problem = dict(exp02.CSTR_UNCERTAINTY_PROBLEM)
    rows, rows_feas = [], []
    for name, (_, outs) in raw.items():
        y = {m: np.array([o[m] for o in outs]) for m in ("IAE", "TV")}
        rho = {m: scipy_stats.spearmanr(u_req, y[m]) for m in y}
        rho_f = scipy_stats.spearmanr(u_req[feasible], y["IAE"][feasible])
        rows.append({
            "Method": name,
            "\\(\\rho_s\\)(IAE, \\(u_{\\mathrm{req}}\\))": f"{rho['IAE'].statistic:+.2f}",
            "\\(\\rho_s^2\\)": f"{rho['IAE'].statistic ** 2:.2f}",
            "\\(\\rho_s\\) feasible": f"{rho_f.statistic:+.2f}",
            "\\(\\rho_s\\)(TV, \\(u_{\\mathrm{req}}\\))": f"{rho['TV'].statistic:+.2f}",
            "\\(u_{\\mathrm{req}} > u_{\\max}\\) (\\%)": f"{100.0 * np.mean(~feasible):.1f}",
        })
        for m in y:
            full = rbd_fast.analyze(problem, samples, y[m], seed=2026, print_to_console=False)
            sub = rbd_fast.analyze(
                problem, samples[feasible], y[m][feasible], seed=2026, print_to_console=False
            )
            row = {"Method": name, "Metric": m}
            for i, nm in enumerate(names):
                row[exp02.SOBOL_LABELS[nm] + ": all"] = f"{full['S1'][i]:.2f}"
                row[exp02.SOBOL_LABELS[nm] + ": feasible"] = (
                    f"{sub['S1'][i]:.2f} $\\pm$ {sub['S1_conf'][i]:.2f}"
                )
            rows_feas.append(row)
    rows_shap = []
    for name, (_, outs) in raw.items():
        for m in ("IAE", "TV"):
            phi, r2 = _shapley_effects(samples[feasible], np.array([o[m] for o in outs])[feasible])
            row = {"Method": name, "Metric": m}
            row |= {exp02.SOBOL_LABELS[nm]: f"{phi[i]:.2f}" for i, nm in enumerate(names)}
            row["\\(R^2\\) (all four)"] = f"{r2:.2f}"
            rows_shap.append(row)
    exp02.export_latex_table(
        data=rows_shap,
        output_path=tables_dir / "sobol_shapley.tex",
        caption=(
            "Shapley effects of the four uncertain factors on the feasible region "
            "($u_{\\mathrm{req}} \\le u_{\\max}$), where the truncated box makes the inputs "
            "dependent: shares of the explained variance (sum to one), from cross-validated "
            "random-forest conditional means; the last column is the cross-validated $R^2$ of the "
            "model with all four factors. Single run, no interval."
        ),
        label="tab:sobol_shapley",
    )
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "sobol_margin_test.tex",
        caption=(
            "Spearman rank correlation, over the Sobol samples, between the closed-loop metrics and "
            "the steady coolant flow $u_{\\mathrm{req}}$ that the perturbed plant needs at the new "
            "setpoint (heat-removal demand); $\\rho_s^2$ is the rank-variance share; ``feasible'' "
            "restricts the IAE correlation to samples with $u_{\\mathrm{req}} \\le u_{\\max}$; last "
            "column: share of samples above the valve stop."
        ),
        label="tab:sobol_margin",
    )
    exp02.export_latex_table(
        data=rows_feas,
        output_path=tables_dir / "sobol_feasible.tex",
        caption=(
            "First-order indices from the given-data RBD-FAST estimator ($M = 10$) on all "
            f"{len(u_req)} samples and on the {int(feasible.sum())} samples with "
            "$u_{\\mathrm{req}} \\le u_{\\max}$ (feasible region; $\\pm$: half-width of the $95\\%$ "
            "bootstrap interval). Total-order indices are not defined on the truncated region."
        ),
        label="tab:sobol_feasible",
    )
    bounds = exp02.CSTR_UNCERTAINTY_PROBLEM["bounds"]
    base = [1.0, 1.0, nom.C_Af, 0.0]
    rows = []
    for i, (nm, (lo, hi)) in enumerate(zip(names, bounds)):
        row = {"Factor": exp02.SOBOL_LABELS[nm], "Range": f"[{lo:g}, {hi:g}]"}
        for tag, val in (("low", lo), ("high", hi)):
            x = list(base)
            x[i] = val
            row[f"\\(u_{{\\mathrm{{req}}}}\\), {tag} (L/min)"] = (
                "--" if nm == "theta_sensor" else f"{plant_of(x).required_coolant_flow(target):.1f}"
            )
        rows.append(row)
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "sobol_ranges.tex",
        caption=(
            "Uncertainty box of the Sobol analysis expressed as heat-removal demand: coolant flow "
            "needed at the $-2$~K setpoint when one factor sits at a bound and the others are nominal "
            f"(nominal: ${plant.required_coolant_flow(target):.1f}$~L/min; valve stop $300$~L/min). "
            "Ranges of $E_a/R$ and $UA$ are relative to nominal."
        ),
        label="tab:sobol_ranges",
    )


def remediate_jpc() -> Path:
    """Assets of Artigo 1 (second-round remediation) written to papers/01_journal_of_process_control."""
    import time

    import experiments.exp_03_pareto_tuning_sweep as exp03

    root = PROJECT_ROOT / "papers" / "01_journal_of_process_control"
    figures_dir, tables_dir = root / "figures", root / "tables"
    exp02.RESULTS_DIR = PROJECT_ROOT / "results" / "jpc"
    exp02.TABLE_FLOAT_ENV = "table*"
    t0 = time.perf_counter()

    def stage(name: str) -> None:
        logger.info("=== STAGE %s (%.0f s elapsed) ===", name, time.perf_counter() - t0)

    plant = exp02.CSTRPlant()
    ss = plant.find_steady_state(q_j=100.0)
    gains, foptd = exp02.setup_controllers(plant, ss, 100.0)
    pids = exp02.make_factories(
        gains, 100.0, exp02.BENCHMARK_LIMITS, dt=SIM_DT, y_ss=ss.T, include_nmpc=False
    )
    stage("nominal benchmark + loop margins")
    run_benchmark(figures_dir, tables_dir, include_nmpc=False)
    stage("anti-windup ablation, scenarios, T_t sweep")
    run_antiwindup_ablation(plant, ss, gains, tables_dir)
    run_aw_scenarios(plant, ss, gains, tables_dir)
    run_tt_curve(plant, ss, gains, tables_dir, figures_dir)
    run_smax_map(plant, ss, gains, tables_dir, figures_dir)
    plot_mechanism(plant, ss, gains, figures_dir)
    run_second_operating_point(SECOND_OP_Q_J, tables_dir)
    run_exact_robustness(plant, ss, foptd, gains, tables_dir)
    stage("cost of the design-model constraint + joint 2-DOF")
    extra = run_robust_constraint_cost(plant, ss, foptd, gains, tables_dir)
    for name, g in extra.items():
        logger.info("TUNING %s: %s", name, g)
    run_model_error_test(plant, ss, foptd, gains, extra, tables_dir)
    run_deadband_test(plant, ss, gains, tables_dir)
    stage("S_max re-optimization")
    run_smax_retuned(plant, ss, foptd, gains, tables_dir)
    stage("out-of-sample steps")
    run_out_of_sample(plant, ss, {**gains, **extra}, tables_dir, base=tuple(gains))
    stage("load disturbance: deterministic and replicated")
    exp02.run_load_disturbance_campaign(
        plant, ss, 100.0, pids, exp02.BENCHMARK_LIMITS, figures_dir, tables_dir,
        dT_f=LOAD_DT_F, dC_frac=LOAD_DC_FRAC, noise_std=0.0,
    )
    run_load_replicated(plant, ss, pids, tables_dir)
    stage("derivative filter N")
    run_n_design_sweep(plant, ss, gains, tables_dir)
    stage("noise campaign")
    exp02.run_noise_and_pareto_campaign(
        plant, ss, 100.0, pids, exp02.BENCHMARK_LIMITS, figures_dir, tables_dir,
        noise_levels=NOISE_LEVELS, filter_taus=(0.0, MEASUREMENT_TAU_F),
    )
    stage("Sobol + heat-removal margin test")
    run_sobol_margin_test(plant, ss, gains, figures_dir, tables_dir)
    stage("Pareto sweep")
    exp03.OVERLEAF_DIR = root  # the sweep writes figure and table below this folder
    (PROJECT_ROOT / "experiments" / ".exp_03_cache.pkl").unlink(missing_ok=True)  # stale labels
    exp03.run_experiment()
    for f in tables_dir.glob("*.tex"):
        if "NMPC" in f.read_text():
            raise ValueError(f"NMPC content leaked into Artigo 1 table {f.name}")
    stage("done")
    return root


def build_jpc() -> Path:
    """Artigo 1 assets: nominal, loop margins, load disturbance, Pareto, noise MC, Sobol."""
    root = ARTICLES / "01_Journal_of_Process_Control"
    figures_dir, tables_dir = root / "figures", root / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    exp02.RESULTS_DIR = PROJECT_ROOT / "results" / "jpc"
    exp02.TABLE_FLOAT_ENV = "table*"

    # Campaigns that contained NMPC: re-run PID-only
    run_benchmark(figures_dir, tables_dir, include_nmpc=False)
    plant = exp02.CSTRPlant()
    ss = plant.find_steady_state(q_j=100.0)
    gains, _ = exp02.setup_controllers(plant, ss, 100.0)
    pids = exp02.make_factories(
        gains, 100.0, exp02.BENCHMARK_LIMITS, dt=0.02, y_ss=ss.T, include_nmpc=False
    )
    exp02.run_load_disturbance_campaign(
        plant, ss, 100.0, pids, exp02.BENCHMARK_LIMITS, figures_dir, tables_dir
    )
    exp02.run_noise_and_pareto_campaign(
        plant, ss, 100.0, pids, exp02.BENCHMARK_LIMITS, figures_dir, tables_dir
    )

    run_antiwindup_ablation(plant, ss, gains, tables_dir)

    # PID-only by construction: re-render tables, copy figures (real files, no symlinks)
    for stem in ("pareto_tradeoff_table", "sobol_sensitivity"):
        rerender_from_csv(stem, tables_dir)
    for fig in ("fig4_pareto_iae_tv.pdf", "fig_sobol_indices.pdf"):
        shutil.copy(BASE / "figures" / fig, figures_dir / fig)

    for f in tables_dir.glob("*.tex"):
        if "NMPC" in f.read_text():
            raise ValueError(f"NMPC content leaked into Artigo 1 table {f.name}")
    logger.info("Artigo 1 assets written to %s", root)
    return root


CACE_PIDS = ("AMIGO", exp02.OPT_ITAE)
CACE_CONTROLLERS = (*CACE_PIDS, "NMPC-Oracle", "NMPC-MHE")


def build_cace() -> Path:
    """Artigo 2 assets: nominal, load disturbance, fouling, noise MC, fouling event, multistep."""
    root = ARTICLES / "02_Computers_Chemical_Engineering"
    figures_dir, tables_dir = root / "figures", root / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    exp02.RESULTS_DIR = PROJECT_ROOT / "results" / "cace"
    exp02.TABLE_FLOAT_ENV = "table*"

    # Fouling event first, on an idle CPU: its table reports wall-clock step times
    run_nmpc_oracle_benchmark(figures_dir, tables_dir, exp02.RESULTS_DIR, CACE_CONTROLLERS)
    run_mhe_tuning_sensitivity(tables_dir=tables_dir)

    # run_benchmark has no controller argument: restrict the gains it builds its loops from
    setup_full = exp01.setup_controllers

    def setup_subset(*args: object) -> tuple[dict, object]:
        gains, foptd = setup_full(*args)
        return {k: g for k, g in gains.items() if k in CACE_PIDS}, foptd

    exp01.setup_controllers = setup_subset
    run_benchmark(figures_dir, tables_dir, include_nmpc=True)
    exp01.setup_controllers = setup_full

    plant = exp02.CSTRPlant()
    ss = plant.find_steady_state(q_j=100.0)
    gains, _ = exp02.setup_controllers(plant, ss, 100.0)
    factories = exp02.make_factories(gains, 100.0, exp02.BENCHMARK_LIMITS, dt=0.02, y_ss=ss.T)
    ctrls = {k: factories[k] for k in CACE_CONTROLLERS}
    for campaign in (
        exp02.run_load_disturbance_campaign,
        exp02.run_fouling_campaign,
        exp02.run_multistep_campaign,
        exp02.run_noise_and_pareto_campaign,
    ):
        campaign(plant, ss, 100.0, ctrls, exp02.BENCHMARK_LIMITS, figures_dir, tables_dir)

    for f in tables_dir.glob("*.tex"):
        if re.search("Ziegler|Cohen|SIMC|Tyreus|2-DOF", f.read_text()):
            raise ValueError(f"Controller outside the Artigo 2 subset in table {f.name}")
    logger.info("Artigo 2 assets written to %s", root)
    return root


if __name__ == "__main__":
    builders = {"jpc": build_jpc, "jpc-remediation": remediate_jpc, "cace": build_cace}
    builders[sys.argv[1]]()
