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
    .venv/bin/python experiments/build_paper_assets.py jpc|cace
"""

import logging
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

import experiments.exp_01_classical_benchmark as exp01
import experiments.exp_02_robustness_campaign as exp02
from experiments.exp_01_classical_benchmark import run_benchmark
from experiments.exp_01b_nmpc_oracle_comparison import (
    run_mhe_tuning_sensitivity,
    run_nmpc_oracle_benchmark,
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


def run_antiwindup_ablation(
    plant: "exp02.CSTRPlant", ss: "exp02.CSTRState", gains: dict, tables_dir: Path
) -> None:
    """Nominal -2 K step with the naive (amplitude-only, sign-blind) vs directional clamping."""
    sim = exp02.ClosedLoopSimulator()
    rows = []
    for name, g in gains.items():
        if name.startswith("2-DOF"):
            continue  # ablation reported on the six distinct feedback loops (1-DOF)
        row = {"Method": name}
        for label, method in (
            ("naive", exp02.AntiWindupMethod.CLAMPING_NAIVE),
            ("directional", exp02.AntiWindupMethod.CLAMPING),
        ):
            pid = exp02.PIDController(g, exp02.BENCHMARK_LIMITS, method, u_bias=100.0, y_ss=ss.T)
            m = sim.run(plant, pid, ss, (0.0, 10.0), 0.02, setpoint_func=lambda t: ss.T - 2.0).metrics
            row[f"IAE ({label})"] = f"{m.iae:.3f}"
            row[f"\\(M_p\\) {label} (\\%)"] = f"{m.overshoot_pct:.1f}"
            row[f"TV {label} (L/min)"] = f"{m.tv:.1f}"
        rows.append(row)
    exp02.export_latex_table(
        data=rows,
        output_path=tables_dir / "antiwindup_ablation.tex",
        caption=(
            "Anti-windup ablation on the nominal $-2$~K step (same gains, valve and protocol as "
            "Table~\\ref{tab:classical_benchmark}): amplitude-only, sign-blind clamping (naive) "
            "versus the directional amplitude- and rate-aware rule of Eq.~\\eqref{eq:clamping_antiwindup}."
        ),
        label="tab:antiwindup_ablation",
    )


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
    builders = {"jpc": build_jpc, "cace": build_cace}
    builders[sys.argv[1]]()
