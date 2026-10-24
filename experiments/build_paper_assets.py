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

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
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
    ("Amp.+rate direct. (Eq.~13)", AW.CLAMPING),
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
            "Table~\\ref{tab:classical_benchmark}); each cell reports IAE (K$\\cdot$min) / overshoot (\\%). "
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
N_SEEDS = 30
NAME_EXACT = "Optimal ITAE ($M_s^{\\mathrm{lin}} \\leq 1.6$)"
NAME_JOINT_FOPTD = "Joint 2-DOF ITAE ($M_s^{\\mathrm{FOPTD}} \\leq 1.6$)"
NAME_JOINT_EXACT = "Joint 2-DOF ITAE ($M_s^{\\mathrm{lin}} \\leq 1.6$)"


def _one_dof(gains: dict) -> dict:
    """The six distinct feedback loops (2-DOF variants share L(s) with their 1-DOF twin)."""
    return {n: g for n, g in gains.items() if not n.startswith("2-DOF")}


def _step_run(plant, ss, g, aw=AW.CLAMPING, step=-2.0, t_end=10.0, **kw):
    """Closed-loop setpoint step on the benchmark valve."""
    pid = exp02.PIDController(g, exp02.BENCHMARK_LIMITS, aw, u_bias=100.0, y_ss=ss.T)
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


def run_aw_tt_sweep(plant, ss, gains: dict, tables_dir: Path) -> None:
    """Back-calculation IAE for T_t x {0.1, 1, 10} against the directional rule, three steps."""
    rows = []
    for name, g in _one_dof(gains).items():
        row = {"Method": name, "\\(T_t\\) (min)": f"{g.tt:.3f}"}
        for step in (-2.0, -5.0, 5.0):
            for scale in (0.1, 1.0, 10.0):
                res = _step_run(plant, ss, replace(g, tt=g.tt * scale), AW.BACK_CALCULATION, step)
                row[f"{step:+g} K, $\\times {scale:g}$"] = f"{res.metrics.iae:.2f}"
            row[f"{step:+g} K, dir."] = f"{_step_run(plant, ss, g, AW.CLAMPING, step).metrics.iae:.2f}"
        rows.append(row)
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "antiwindup_tt_sweep.tex",
        caption=(
            "IAE (K$\\cdot$min) of back-calculation with the tracking time constant scaled by $0.1$, "
            "$1$ (Eq.~\\eqref{eq:back_calculation}) and $10$, against the directional rule "
            "(``dir.'', Eq.~\\eqref{eq:clamping_antiwindup}), on three setpoint steps."
        ),
        label="tab:antiwindup_tt_sweep",
    )


def _itae6(plant, ss, g) -> float:
    """Design objective: ITAE of the -2 K step over 6 min on the benchmark valve."""
    return _step_run(plant, ss, g, step=-2.0, t_end=6.0).metrics.itae


def _ms_lin(plant, ss, g) -> float:
    """M_s of the Jacobian loop with the half-sample zero-order-hold delay."""
    return linearized_robustness(plant, ss, 100.0, g, theta=SIM_DT / 2.0)["ms"]


def _multistart(plant, ss, starts, feasible, **kw):
    """Best feasible Nelder-Mead optimum over `starts`, restarted once from the winner."""

    def tune(g0):
        return tune_by_optimization(
            plant=plant, nominal_state=ss, q_j_ss=100.0, target_dT=-2.0, initial_gains=g0,
            criterion=OptimizationCriterion.ITAE, max_ms=1.6, t_sim=6.0, dt=SIM_DT,
            limits=exp02.BENCHMARK_LIMITS, **kw,
        )

    best = None
    for round_starts in (starts, None):
        pool = [tune(g0) for g0 in (round_starts if round_starts is not None else [best])]
        pool = [g for g in pool if feasible(g)] + ([best] if best else [])
        best = min(pool, key=lambda g: _itae6(plant, ss, g))
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
        res = _step_run(plant, ss, g, noise_std=sigma, seed=500 + seed)
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
    """Sobol campaign plus a direct test of the heat-removal-margin explanation.

    u_req is the steady coolant flow that holds the new setpoint on the perturbed plant
    (closed form); the explanation predicts that IAE rises with u_req towards u_max.
    """
    limits = exp02.BENCHMARK_LIMITS
    raw: dict = {}
    exp02.run_sobol_uncertainty_campaign(gains, 100.0, limits, figures_dir, tables_dir, raw=raw)
    nom, target = CSTRParameters(), ss.T - 2.0

    def plant_of(x):
        return exp02.CSTRPlant(CSTRParameters(
            E_over_R=nom.E_over_R * float(x[0]), UA=nom.UA * float(x[1]), C_Af=float(x[2])
        ))

    samples = next(iter(raw.values()))[0]
    u_req = np.array([plant_of(x).required_coolant_flow(target) for x in samples])
    rows = []
    for name, (_, outs) in raw.items():
        rho = {m: scipy_stats.spearmanr(u_req, [o[m] for o in outs]) for m in ("IAE", "TV")}
        rows.append({
            "Method": name,
            "\\(\\rho_s\\)(IAE, \\(u_{\\mathrm{req}}\\))": f"{rho['IAE'].statistic:+.2f}",
            "\\(\\rho_s\\)(TV, \\(u_{\\mathrm{req}}\\))": f"{rho['TV'].statistic:+.2f}",
            "\\(u_{\\mathrm{req}} > u_{\\max}\\) (\\%)": f"{100.0 * np.mean(u_req > limits.u_max):.1f}",
        })
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "sobol_margin_test.tex",
        caption=(
            "Spearman rank correlation, over the Sobol samples, between the closed-loop metrics and "
            "the steady coolant flow $u_{\\mathrm{req}}$ that the perturbed plant needs at the new "
            "setpoint (heat-removal demand); last column: share of samples with $u_{\\mathrm{req}}$ "
            "above the valve stop."
        ),
        label="tab:sobol_margin",
    )
    names = exp02.CSTR_UNCERTAINTY_PROBLEM["names"]
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
            f"needed at the $-2$~K setpoint when one factor sits at a bound and the others are nominal "
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
    run_aw_tt_sweep(plant, ss, gains, tables_dir)
    run_exact_robustness(plant, ss, foptd, gains, tables_dir)
    stage("cost of the design-model constraint + joint 2-DOF")
    extra = run_robust_constraint_cost(plant, ss, foptd, gains, tables_dir)
    for name, g in extra.items():
        logger.info("TUNING %s: %s", name, g)
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
