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
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

import experiments.exp_01_classical_benchmark as exp01
import experiments.exp_02_robustness_campaign as exp02
from experiments.exp_01_classical_benchmark import run_benchmark
from experiments.exp_01b_nmpc_oracle_comparison import (
    run_mhe_tuning_sensitivity,
    run_nmpc_oracle_benchmark,
)
from src.classical_control.tuning_optimization import (
    calculate_maximum_sensitivity_foptd,
    linearized_robustness,
)

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
    ("Textbook", AW.CLAMPING_NAIVE),
    ("Pos.-only agnostic", AW.CLAMPING_POS_AGNOSTIC),
    ("Pos.+rate agnostic", AW.CLAMPING_RATE_AGNOSTIC),
    ("Pos.-only directional", AW.CLAMPING_POS_DIRECTIONAL),
    ("Directional (proposed)", AW.CLAMPING),
)
MEASUREMENT_TAU_F = 0.05  # min
NOISE_LEVELS = (0.0, 0.01, 0.05, 0.10)  # K
OOS_STEPS = (-5.0, -2.0, -1.0, 1.0, 2.0, 5.0)  # K; -2 K is the ITAE design (in-sample) step


def run_antiwindup_ablation(
    plant: "exp02.CSTRPlant", ss: "exp02.CSTRState", gains: dict, tables_dir: Path
) -> None:
    """Nominal -2 K step: none / back-calculation / textbook / 2x2 clamping factorial.

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
            "Eq.~\\eqref{eq:clamping_antiwindup}. ``Textbook'' is the amplitude-only rule "
            "$u_{\\text{raw}} \\ge u_{\\max} \\wedge e>0$ of direct-acting loops."
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
    plant: "exp02.CSTRPlant", ss: "exp02.CSTRState", gains: dict, tables_dir: Path
) -> None:
    """ITAE of every tuning on setpoint steps; Optimal ITAE was designed on -2 K only."""
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
    ranks = {d: 1 + sum(itae[n][d] < itae[exp02.OPT_ITAE][d] for n in names) for d in OOS_STEPS}
    rows.append({"Method": "Rank of Optimal ITAE (1 = best)"} | {f"{d:+g} K": str(ranks[d]) for d in OOS_STEPS})
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


def remediate_jpc() -> Path:
    """IC-T21/IC-T22 assets of Artigo 1 written in place to papers/01_journal_of_process_control."""
    root = PROJECT_ROOT / "papers" / "01_journal_of_process_control"
    figures_dir, tables_dir = root / "figures", root / "tables"
    exp02.RESULTS_DIR = PROJECT_ROOT / "results" / "jpc"
    exp02.TABLE_FLOAT_ENV = "table*"

    plant = exp02.CSTRPlant()
    ss = plant.find_steady_state(q_j=100.0)
    gains, foptd = exp02.setup_controllers(plant, ss, 100.0)
    pids = exp02.make_factories(
        gains, 100.0, exp02.BENCHMARK_LIMITS, dt=0.02, y_ss=ss.T, include_nmpc=False
    )
    run_antiwindup_ablation(plant, ss, gains, tables_dir)
    run_exact_robustness(plant, ss, foptd, gains, tables_dir)
    run_out_of_sample(plant, ss, gains, tables_dir)
    exp02.run_noise_and_pareto_campaign(
        plant, ss, 100.0, pids, exp02.BENCHMARK_LIMITS, figures_dir, tables_dir,
        noise_levels=NOISE_LEVELS, filter_taus=(0.0, MEASUREMENT_TAU_F),
    )
    for f in tables_dir.glob("*.tex"):
        if "NMPC" in f.read_text():
            raise ValueError(f"NMPC content leaked into Artigo 1 table {f.name}")
    logger.info("Artigo 1 remediation assets written to %s", root)
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
