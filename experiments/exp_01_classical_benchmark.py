# -*- coding: utf-8 -*-
"""Nominal benchmark: -2 K setpoint step on the non-linear CSTR (noise-free).

Controllers: ZN, Cohen-Coon, Tyreus-Luyben, AMIGO, SIMC, Optimal ITAE (1-DOF and 2-DOF,
Ms <= 1.6 on the dead-time FOPTD loop), NMPC-Oracle and NMPC-MHE.

Outputs (overleaf/): tables/benchmark_table.tex, figures/fig1_classical_benchmark.pdf,
figures/fig_sensitivity_magnitude.pdf; results/benchmark_table.csv.
"""

# %% [1. Importações e Configuração de Caminhos]
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import numpy as np

from experiments.exp_02_robustness_campaign import (
    OPT_ITAE_2DOF,
    OVERLEAF_DIR,
    export_latex_table,
    make_factories,
    setup_controllers,
)
from src.classical_control.closed_loop import ClosedLoopSimulator
from src.classical_control.tuning_optimization import (
    calculate_maximum_sensitivity_foptd,
    loop_gain_foptd,
    loop_gain_linearized,
    phase_margin_deg,
    sensitivity_magnitude_foptd,
)
from src.evaluation.plot_styles import (
    IEEE_LINESTYLES,
    IEEE_PALETTE,
    get_figure_dimensions,
    setup_ieee_style,
)
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRPlant

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("exp_01_benchmark")


# %% [2. Função Principal de Execução do Benchmark]
def run_benchmark(
    figures_dir: Path = OVERLEAF_DIR / "figures",
    tables_dir: Path = OVERLEAF_DIR / "tables",
    include_nmpc: bool = True,
) -> None:
    """Runs the deterministic nominal benchmark and writes table + figures.

    Args:
        figures_dir: Output folder for the figures.
        tables_dir: Output folder for the LaTeX tables.
        include_nmpc: If False, only the PID tunings are simulated, tabulated and plotted.
    """
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    plant = CSTRPlant()
    q_j_ss = 100.0
    ss = plant.find_steady_state(q_j=q_j_ss)
    logger.info("Estado estacionário nominal: T=%.2f K, C_A=%.4f mol/L", ss.T, ss.C_A)

    dt = 0.02
    limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)
    gains, foptd = setup_controllers(plant, ss, q_j_ss)
    factories = make_factories(gains, q_j_ss, limits, dt=dt, y_ss=ss.T, include_nmpc=include_nmpc)

    sim = ClosedLoopSimulator()
    target_T = ss.T - 2.0
    sim_results = {}
    table_rows = []
    for name, make in factories.items():
        logger.info("Simulando malha fechada para: %s", name)
        res = sim.run(
            plant=plant,
            controller=make(),
            initial_state=ss,
            t_span=(0.0, 10.0),
            dt=dt,
            setpoint_func=lambda t: target_T,
            noise_std=0.0,  # Benchmark determinístico puro
        )
        sim_results[name] = res
        g = gains.get(name)
        m = res.metrics
        table_rows.append({
            "Method": name,
            r"\(K_p\)": f"{g.kp:.2f}" if g else "--",
            r"\(T_i\text{ (min)}\)": f"{g.ti:.3f}" if g else "--",
            r"\(T_d\text{ (min)}\)": f"{g.td:.3f}" if g else "--",
            r"\(\beta\)": f"{g.beta:.1f}" if g else "--",
            "IAE": f"{m.iae:.3f}",
            "ITAE": f"{m.itae:.3f}",
            "TV (L/min)": f"{m.tv:.1f}",
            r"\(M_p\text{ (\%)}\)": f"{m.overshoot_pct:.1f}",
            r"\(t_s\text{ (min)}\)": (
                f"{m.settling_time:.2f}" if m.settling_time is not None else "N/A"
            ),
            r"\(M_s\)": f"{calculate_maximum_sensitivity_foptd(foptd, g):.2f}" if g else "--",
        })

    export_latex_table(
        data=table_rows,
        output_path=tables_dir / "benchmark_table.tex",
        caption=(
            "Nominal servo benchmark ($-2$~K setpoint step, noise-free) on the non-linear CSTR. "
            f"FOPTD: $K={foptd.k_p:.4f}$~K/(L/min), $\\tau={foptd.tau:.4f}$~min, "
            f"$\\theta={foptd.theta:.4f}$~min. $M_s$ is evaluated on the dead-time FOPTD loop; "
            "TV includes the initial valve move from $\\bar q_j$."
        ),
        label="tab:classical_benchmark",
    )

    # %% [3. Figura 1: resposta temporal]
    setup_ieee_style(single_column=True)
    fig_w, fig_h = get_figure_dimensions(columns=1, height_override=4.4)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(fig_w, fig_h), sharex=True, dpi=300)
    sample = next(iter(sim_results.values()))
    ax1.plot(sample.t, sample.setpoint, color=IEEE_PALETTE["Setpoint"],
             linestyle=IEEE_LINESTYLES["Setpoint"], label="Setpoint ($T_{sp}$)")
    for name, res in sim_results.items():
        style = {"color": IEEE_PALETTE[name], "linestyle": IEEE_LINESTYLES[name], "linewidth": 1.1}
        ax1.plot(res.t, res.t_pv, label=name, **style)
        ax2.plot(res.t, res.u_applied, **style)
    ax1.set_ylabel("Reactor Temp. $T$ (K)")
    ax1.set_ylim(ss.T - 3.0, ss.T + 0.6)
    ax1.grid(True)
    for u_lim in (limits.u_min, limits.u_max):
        ax2.axhline(u_lim, color=IEEE_PALETTE["Constraint"], linestyle=IEEE_LINESTYLES["Constraint"],
                    linewidth=0.9)
    ax2.set_ylabel(r"Coolant Flow $q_j$ (L/min)")
    ax2.set_xlabel("Time $t$ (min)")
    ax2.set_ylim(-15, 335)
    ax2.grid(True)
    h, lab = ax1.get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=5.6,
               columnspacing=0.5, handletextpad=0.3)
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.875])
    fig.savefig(figures_dir / "fig1_classical_benchmark.pdf")
    fig.savefig(figures_dir / "fig1_classical_benchmark.png", dpi=300)
    plt.close(fig)

    # %% [4. Figura: |S(jw)| no laço FOPTD com atraso]
    omegas = np.logspace(-2, 2.5, 3000)
    fig, ax = plt.subplots(figsize=get_figure_dimensions(columns=1, aspect_ratio=0.85), dpi=300)
    for name, g in gains.items():
        if name == OPT_ITAE_2DOF:
            continue  # identical feedback loop L(s) as 1-DOF Optimal ITAE
        mag = sensitivity_magnitude_foptd(foptd, g, omegas)
        ax.loglog(omegas, mag, color=IEEE_PALETTE[name], linestyle=IEEE_LINESTYLES[name],
                  label=f"{name.split(' (')[0]} ($M_s$={mag.max():.2f})", linewidth=1.1)
    ax.axhline(1.6, color=IEEE_PALETTE["Constraint"], linestyle=IEEE_LINESTYLES["Constraint"],
               linewidth=0.9, label="$M_s = 1.6$")
    ax.set_xlabel(r"Frequency $\omega$ (rad/min)")
    ax.set_ylabel(r"$|S(j\omega)|$")
    ax.set_ylim(1e-2, 10.0)
    ax.grid(True, which="both")
    h, lab = ax.get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=5.4,
               columnspacing=0.6, handlelength=1.8)
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.85])
    fig.savefig(figures_dir / "fig_sensitivity_magnitude.pdf")
    fig.savefig(figures_dir / "fig_sensitivity_magnitude.png", dpi=300)
    plt.close(fig)
    # %% [5. Tabela: margens no FOPTD de projeto vs. na linearização exata da planta]
    # The sampled loop adds a half-sample ZOH delay to the delay-free Jacobian model.
    omegas_m = np.logspace(-3, 3, 20000)
    margin_rows = []
    for name, g in gains.items():
        if name.startswith("2-DOF"):
            continue  # same feedback loop as the 1-DOF controller
        l_foptd = loop_gain_foptd(foptd, g, omegas_m)
        l_lin = loop_gain_linearized(plant, ss, q_j_ss, g, omegas_m, theta=dt / 2.0)
        margin_rows.append({
            "Method": name,
            r"\(M_s\) (FOPTD)": f"{np.max(np.abs(1.0 / (1.0 + l_foptd))):.2f}",
            r"PM (FOPTD, \(^\circ\))": f"{phase_margin_deg(l_foptd, omegas_m):.1f}",
            r"\(M_s\) (lin.)": f"{np.max(np.abs(1.0 / (1.0 + l_lin))):.2f}",
            r"PM (lin., \(^\circ\))": f"{phase_margin_deg(l_lin, omegas_m):.1f}",
        })
    export_latex_table(
        data=margin_rows,
        output_path=tables_dir / "loop_margins_table.tex",
        caption=(
            "Sensitivity peak and phase margin of each PID loop on the identified FOPTD design "
            "model and on the exact Jacobian linearization of the CSTR at $\\mathbf{x}_{ss}$ "
            "with the half-sample zero-order-hold delay $\\Delta t/2 = 0.01$~min. Valve "
            "saturation and slew-rate limits are not part of either linear loop."
        ),
        label="tab:loop_margins",
    )
    logger.info("Benchmark nominal concluído.")


# %% [5. Ponto de Entrada Principal]
if __name__ == "__main__":
    run_benchmark()
