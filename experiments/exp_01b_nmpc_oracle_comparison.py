# -*- coding: utf-8 -*-
"""NMPC-Oracle vs NMPC-MHE vs modern robust PID under a fouling event and sensor noise.

Scenario (10 min, dt = 0.02 min): -2 K setpoint step at t = 0.5 min, abrupt jacket fouling
to 70 % UA at t = 4 min, Gaussian thermocouple noise sigma = 0.05 K on T (and on T_j for
the MHE). The Oracle receives the true [C_A, T, T_j]; the MHE variant reconstructs
[C_A, T, T_j, alpha_UA] from (T, T_j) only. Both NMPCs respect the 80 L/min^2 valve slew.

Outputs: overleaf/tables/nmpc_oracle_benchmark.tex, overleaf/figures/
fig_nmpc_oracle_comparison.pdf, results/nmpc_oracle_vs_mhe_summary.csv.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments.exp_02_robustness_campaign import (
    BENCHMARK_LIMITS,
    OPT_ITAE,
    OPT_ITAE_2DOF,
    OVERLEAF_DIR,
    RESULTS_DIR,
    export_latex_table,
    make_factories,
    setup_controllers,
)
from src.classical_control.closed_loop import ClosedLoopSimulator
from src.evaluation.plot_styles import (
    IEEE_LINESTYLES,
    IEEE_PALETTE,
    get_figure_dimensions,
    setup_ieee_style,
)
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRPlant

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("exp_01b_nmpc")

COMPARED = ("AMIGO", "Skogestad SIMC", OPT_ITAE, OPT_ITAE_2DOF, "NMPC-Oracle", "NMPC-MHE")
NOISE_STD = 0.05
UA_FOULED = 0.70
T_FOUL = 4.0


def run_nmpc_oracle_benchmark(
    figures_dir: Path = OVERLEAF_DIR / "figures",
    tables_dir: Path = OVERLEAF_DIR / "tables",
    results_dir: Path = RESULTS_DIR,
    compared: tuple[str, ...] = COMPARED,
) -> pd.DataFrame:
    """Runs the controller comparison and writes table, CSV and figure.

    Args:
        figures_dir: Output folder for the figure.
        tables_dir: Output folder for the LaTeX table.
        results_dir: Output folder for the raw summary CSV.
        compared: Controller names to simulate; must include "NMPC-Oracle".
    """
    plant = CSTRPlant()
    q_j_ss = 100.0
    ss = plant.find_steady_state(q_j=q_j_ss)
    dt = 0.02
    limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)
    gains, _ = setup_controllers(plant, ss, q_j_ss)
    factories = make_factories(gains, q_j_ss, limits, dt=dt, y_ss=ss.T)

    target_T = ss.T - 2.0
    ua_fouled = UA_FOULED * plant.params.UA
    sim = ClosedLoopSimulator()
    results, rows = {}, []
    for name in compared:
        ctrl = factories[name](sensor_noise_std=NOISE_STD, seed=7)
        t0 = time.perf_counter()
        res = sim.run(
            plant=plant,
            controller=ctrl,
            initial_state=ss,
            t_span=(0.0, 10.0),
            dt=dt,
            setpoint_func=lambda t: target_T if t >= 0.5 else ss.T,
            disturbance_func=lambda t: {"UA": ua_fouled} if t >= T_FOUL else {},
            noise_std=NOISE_STD,
            seed=42,
        )
        wall_ms = 1e3 * (time.perf_counter() - t0) / len(res.t)
        results[name] = res
        alpha_hat = getattr(ctrl, "_estimated_alpha_ua", float("nan"))
        rows.append({
            "controller": name,
            "iae": res.metrics.iae,
            "itae": res.metrics.itae,
            "tv": res.metrics.tv,
            "overshoot_pct": res.metrics.overshoot_pct,
            "alpha_ua_hat_final": alpha_hat,
            "step_time_ms": wall_ms,
        })

    df = pd.DataFrame(rows)
    iae_oracle = float(df.loc[df.controller == "NMPC-Oracle", "iae"].iloc[0])
    df["iae_gap_vs_oracle_pct"] = 100.0 * (df["iae"] - iae_oracle) / iae_oracle
    results_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(results_dir / "nmpc_oracle_vs_mhe_summary.csv", index=False)

    table_rows = [
        {
            "Controller": r.controller,
            "IAE": f"{r.iae:.3f}",
            r"\(\Delta\)IAE vs Oracle (\%)": f"{r.iae_gap_vs_oracle_pct:+.1f}",
            "ITAE": f"{r.itae:.3f}",
            "TV (L/min)": f"{r.tv:.1f}",
            r"\(M_p\) (\%)": f"{r.overshoot_pct:.1f}",
            r"\(\hat\alpha_{UA}(t_f)\)": (
                "--" if pd.isna(r.alpha_ua_hat_final) else f"{r.alpha_ua_hat_final:.3f}"
            ),
            "Step time (ms)": f"{r.step_time_ms:.2f}",
        }
        for r in df.itertuples()
    ]
    export_latex_table(
        data=table_rows,
        output_path=tables_dir / "nmpc_oracle_benchmark.tex",
        caption=(
            "Output-feedback gap: NMPC with true-state access (Oracle) vs NMPC with augmented "
            "MHE (thermal measurements only) vs $M_s$-constrained PID. $-2$~K step at "
            f"$t=0.5$~min, jacket fouling to ${int(UA_FOULED * 100)}\\%\\,UA$ at "
            f"$t={T_FOUL:.0f}$~min, sensor noise $\\sigma={NOISE_STD}$~K. Both NMPCs: "
            "$N=50$ ($1.0$~min), $|\\Delta q_j| \\le 80\\,\\Delta t$. Step time is the mean "
            "wall-clock time per sample (controller + plant integration; hardware dependent)."
        ),
        label="tab:nmpc_oracle_benchmark",
    )

    setup_ieee_style(single_column=True)
    fig_w, fig_h = get_figure_dimensions(columns=1, height_override=4.2)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(fig_w, fig_h), sharex=True, dpi=300)
    sample = next(iter(results.values()))
    ax1.plot(sample.t, sample.setpoint, color=IEEE_PALETTE["Setpoint"],
             linestyle=IEEE_LINESTYLES["Setpoint"], label="Setpoint")
    for name, res in results.items():
        style = {"color": IEEE_PALETTE[name], "linestyle": IEEE_LINESTYLES[name], "linewidth": 1.1}
        ax1.plot(res.t, res.states[:, 1], label=name, **style)
        ax2.plot(res.t, res.u_applied, **style)
    for ax in (ax1, ax2):
        ax.axvline(T_FOUL, color="#777777", linestyle="--", linewidth=0.7)
        ax.grid(True)
    ax1.text(T_FOUL + 0.1, 0.04, f"UA $\\rightarrow$ {int(UA_FOULED * 100)}%", fontsize=6.5,
             transform=ax1.get_xaxis_transform())
    ax1.set_ylabel("True Reactor Temp. $T$ (K)")
    ax2.set_ylabel(r"Coolant Flow $q_j$ (L/min)")
    ax2.set_xlabel("Time $t$ (min)")
    h, lab = ax1.get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=5.8,
               columnspacing=0.5)
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.88])
    fig.savefig(figures_dir / "fig_nmpc_oracle_comparison.pdf")
    fig.savefig(figures_dir / "fig_nmpc_oracle_comparison.png", dpi=300)
    plt.close(fig)
    return df


class _DiagRecorder:
    """Forwards to a controller and keeps (C_A_hat, alpha_UA_hat) of every sample."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.log: list[tuple[float, float]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def compute(self, *args: Any, **kwargs: Any) -> tuple[float, dict]:
        u, diag = self.inner.compute(*args, **kwargs)
        self.log.append((diag["c_a_hat"], diag["alpha_ua_hat"]))
        return u, diag


MHE_TUNING_VARIANTS = (
    ("Nominal", 1.0, 1.0),
    (r"\(R_e \times 0.1\)", 0.1, 1.0),
    (r"\(R_e \times 10\)", 10.0, 1.0),
    (r"\(Q_{\alpha} \times 0.1\)", 1.0, 0.1),
    (r"\(Q_{\alpha} \times 10\)", 1.0, 10.0),
)


def run_mhe_tuning_sensitivity(
    alpha_band: float = 0.02, tables_dir: Path = OVERLEAF_DIR / "tables"
) -> pd.DataFrame:
    """NMPC-MHE on the Table 7 scenario with the measurement and fouling covariances rescaled.

    Reports IAE, TV, RMS C_A estimation error, final alpha_UA estimate and the time after the
    fouling event at which alpha_UA_hat enters and stays in +/- alpha_band around the true value.
    """
    plant = CSTRPlant()
    q_j_ss = 100.0
    ss = plant.find_steady_state(q_j=q_j_ss)
    dt = 0.02
    gains, _ = setup_controllers(plant, ss, q_j_ss)
    factories = make_factories(gains, q_j_ss, BENCHMARK_LIMITS, dt=dt, y_ss=ss.T)
    target_T = ss.T - 2.0
    ua_fouled = UA_FOULED * plant.params.UA
    rows = []
    for label, r_scale, q_scale in MHE_TUNING_VARIANTS:
        ctrl = _DiagRecorder(factories["NMPC-MHE"](sensor_noise_std=NOISE_STD, seed=7))
        ctrl.estimator.R = ctrl.estimator.R * r_scale
        ctrl.estimator.Q[3, 3] *= q_scale
        res = ClosedLoopSimulator().run(
            plant=plant,
            controller=ctrl,
            initial_state=ss,
            t_span=(0.0, 10.0),
            dt=dt,
            setpoint_func=lambda t: target_T if t >= 0.5 else ss.T,
            disturbance_func=lambda t: {"UA": ua_fouled} if t >= T_FOUL else {},
            noise_std=NOISE_STD,
            seed=42,
        )
        c_a_hat, alpha_hat = (np.array(v) for v in zip(*ctrl.log))
        alpha_true = np.where(res.t >= T_FOUL, UA_FOULED, 1.0)
        outside = np.where((res.t >= T_FOUL) & (np.abs(alpha_hat - alpha_true) > alpha_band))[0]
        if len(outside) == 0:
            t_settle = 0.0
        elif outside[-1] == len(res.t) - 1:
            t_settle = float("nan")  # still outside the band at t_f
        else:
            t_settle = float(res.t[outside[-1] + 1] - T_FOUL)
        rows.append({
            "Covariance scaling": label,
            "IAE": f"{res.metrics.iae:.3f}",
            "TV (L/min)": f"{res.metrics.tv:.1f}",
            r"RMS \(\hat C_A - C_A\) (mol/L)": f"{np.sqrt(np.mean((c_a_hat - res.states[:, 0]) ** 2)):.2e}",
            r"\(\hat\alpha_{UA}(t_f)\)": f"{alpha_hat[-1]:.3f}",
            r"\(\alpha\) settling (min)": "not settled" if np.isnan(t_settle) else f"{t_settle:.2f}",
        })
    export_latex_table(
        data=rows,
        output_path=tables_dir / "mhe_tuning_sensitivity.tex",
        caption=(
            "Sensitivity of NMPC-MHE to the estimator covariances on the scenario of "
            "Table~\\ref{tab:nmpc_oracle_benchmark} (fouling to $70\\%\\,UA$ at $t = 4$~min, "
            f"$\\sigma = {NOISE_STD}$~K). $R_e$ is scaled as a whole, $Q_{{\\alpha}}$ is the "
            "fouling random-walk variance. Settling: time after the fouling event from which "
            f"$|\\hat\\alpha_{{UA}} - \\alpha_{{UA}}| \\le {alpha_band}$ holds until $t_f$."
        ),
        label="tab:mhe_tuning",
    )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    logger.info("\n%s", run_nmpc_oracle_benchmark().to_string())
    logger.info("\n%s", run_mhe_tuning_sensitivity().to_string())
