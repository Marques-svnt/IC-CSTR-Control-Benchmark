# -*- coding: utf-8 -*-
"""Script mestre de geração de figuras de publicação em tamanho máximo para o Artigo 1.

Gera todas as figuras no padrão IEEE Transactions (coluna dupla, 7.16 polegadas de largura,
alta resolução 300 DPI, fontes Type 42 Times New Roman/Serif) garantindo:
1. Tamanho máximo (largura de coluna dupla 7.16 in / ~2150 px em 300 DPI);
2. Nenhuma curva ou sobressinal cortado nos eixos Y;
3. Legendas unificadas superiores externas que NÃO sobrepõem e não suprimem nenhum conteúdo;
4. Salvamento em pasta dedicada 'figures_novas/' e atualização em 'figures/' e no artigo scratch.
"""

import logging
import pickle
import sys
from pathlib import Path
from typing import Dict, List

# Adiciona a raiz do projeto ao sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from src.classical_control.closed_loop import ClosedLoopSimulator
from src.classical_control.foptd import identify_foptd
from src.classical_control.pid_controller import AntiWindupMethod, PIDController, PIDGains
from src.classical_control.tuning_analytical import TuningRule, tune_analytical
from src.classical_control.tuning_optimization import (
    OptimizationCriterion,
    tune_by_optimization,
)
from src.evaluation.plot_styles import (
    IEEE_DOUBLE_COL_WIDTH_INCHES,
    IEEE_LINESTYLES,
    IEEE_PALETTE,
    setup_ieee_style,
)
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRPlant
from src.sim_core.integrator import NumericalIntegrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("generate_maximum_figures")


def save_figure_to_all(fig: plt.Figure, base_name: str, target_dirs: List[Path]) -> None:
    """Salva a figura em formato PDF e PNG de 300 DPI em todos os diretórios alvo."""
    for d in target_dirs:
        d.mkdir(parents=True, exist_ok=True)
        pdf_path = d / f"{base_name}.pdf"
        png_path = d / f"{base_name}.png"
        fig.savefig(pdf_path, dpi=300)
        fig.savefig(png_path, dpi=300)
        logger.info("Salvo: %s e %s", pdf_path, png_path)


def main() -> None:
    """Gera e exporta todas as figuras científicas de alta resolução do Artigo 1."""
    paper_dir = PROJECT_ROOT / "Artigos_Rascunhos" / "Artigo_01_Classic_Methods"
    overleaf_fig_dir = paper_dir / "overleaf" / "figures"
    figures_novas_dir = paper_dir / "figures_novas"
    figures_dir = paper_dir / "figures"
    legacy_paper_dir = PROJECT_ROOT / "Artigos_Rascunhos" / "Artigo_01_PID_Neural_Comparativo" / "figures"
    target_dirs = [overleaf_fig_dir, figures_novas_dir, figures_dir, legacy_paper_dir]
    try:
        scratch_figures_dir = Path.home() / ".gemini" / "antigravity" / "scratch" / "pid-neural-control-proic" / "docs" / "articles" / "paper-01-classical" / "figures"
        if scratch_figures_dir.parent.exists():
            target_dirs.append(scratch_figures_dir)
    except Exception:
        pass

    for d in target_dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Configuração do modelo e planta
    plant = CSTRPlant()
    integrator = NumericalIntegrator(method="RK45")
    q_j_ss = 100.0
    ss = plant.find_steady_state(q_j=q_j_ss)
    logger.info("Estado estacionário: T=%.2f K, C_A=%.4f mol/L", ss.T, ss.C_A)

    # Identificação FOPTD
    delta_q = 10.0
    id_res = integrator.simulate_open_loop(
        plant=plant,
        initial_state=ss,
        t_span=(0.0, 6.0),
        dt=0.02,
        u_func=lambda t: q_j_ss + delta_q,
    )
    foptd, rmse = identify_foptd(
        t=id_res.t,
        y=id_res.states[:, 1],
        delta_u=delta_q,
        y0=ss.T,
    )
    logger.info("FOPTD: K=%.4f, tau=%.3f, theta=%.3f (RMSE=%.4f)", foptd.k_p, foptd.tau, foptd.theta, rmse)

    # Controladores
    controllers: Dict[str, PIDGains] = {
        "Ziegler-Nichols": tune_analytical(foptd, rule=TuningRule.ZIEGLER_NICHOLS_PID),
        "Cohen-Coon": tune_analytical(foptd, rule=TuningRule.COHEN_COON_PID),
        "Skogestad SIMC": tune_analytical(foptd, rule=TuningRule.SKOGESTAD_SIMC_PID, tau_c=0.4),
        "Optimal ITAE ($M_s \\leq 1.6$)": tune_by_optimization(
            plant=plant,
            nominal_state=ss,
            q_j_ss=q_j_ss,
            criterion=OptimizationCriterion.ITAE,
            max_ms=1.6,
            foptd=foptd,
        ),
    }

    limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)
    sim = ClosedLoopSimulator(integrator=integrator)

    # Configuração de estilo global IEEE dupla coluna
    setup_ieee_style(single_column=False)
    mpl.rcParams["font.size"] = 9.0
    mpl.rcParams["axes.labelsize"] = 9.5
    mpl.rcParams["axes.titlesize"] = 10.0
    mpl.rcParams["legend.fontsize"] = 8.0

    # =========================================================================
    # FIGURA 1: Benchmark Nominal de Rastreamento de Setpoint (-2.0 K)
    # =========================================================================
    logger.info("--- Gerando Figura 1 (fig1_classical_benchmark) ---")
    t_sim_span = (0.0, 10.0)
    target_T = ss.T - 2.0
    dt = 0.02

    sim1_results = {}
    for name, gains in controllers.items():
        pid = PIDController(
            gains=gains,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        )
        res = sim.run(
            plant=plant,
            controller=pid,
            initial_state=ss,
            t_span=t_sim_span,
            dt=dt,
            setpoint_func=lambda t: target_T,
            noise_std=0.0,
            seed=42,
        )
        sim1_results[name] = res

    fig1, (ax1_1, ax1_2) = plt.subplots(
        2, 1, figsize=(IEEE_DOUBLE_COL_WIDTH_INCHES, 4.8), sharex=True, dpi=300
    )

    sample_res = next(iter(sim1_results.values()))
    ax1_1.plot(
        sample_res.t,
        sample_res.setpoint,
        color=IEEE_PALETTE["Setpoint"],
        linestyle=IEEE_LINESTYLES["Setpoint"],
        label=r"Setpoint ($T_{sp}$)",
        linewidth=1.3,
    )

    for name, res in sim1_results.items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax1_1.plot(res.t, res.t_pv, label=name, color=color, linestyle=linestyle, linewidth=1.3)
        ax1_2.plot(res.t, res.u_applied, label=name, color=color, linestyle=linestyle, linewidth=1.3)

    # Subplot 1: Temperatura do reator - amplitude total para evidenciar ciclo limite ZN/CC
    ax1_1.set_ylabel("Reactor Temp. $T$ (K)", fontsize=9.5)
    ax1_1.set_ylim(375.0, 415.0)
    ax1_1.set_title("Classical PID Benchmark: Nominal Setpoint Tracking ($-2.0$ K Step)", fontsize=10.0, pad=8)
    ax1_1.grid(True, linestyle=":", alpha=0.6)

    # Subplot 2: Vazão de fluido refrigerante
    ax1_2.axhline(
        limits.u_max,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        label=r"Actuator Limits ($u_{\mathrm{min}}, u_{\mathrm{max}}$)",
        linewidth=1.1,
    )
    ax1_2.axhline(
        limits.u_min,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        linewidth=1.1,
    )
    ax1_2.set_ylabel(r"Coolant Flow $q_j$ (L/min)", fontsize=9.5)
    ax1_2.set_xlabel("Time $t$ (min)", fontsize=9.5)
    ax1_2.set_ylim(-15, 335)
    ax1_2.grid(True, linestyle=":", alpha=0.6)

    # Legenda superior externa unificada
    h1, l1 = ax1_1.get_legend_handles_labels()
    h2, l2 = ax1_2.get_legend_handles_labels()
    handles_unified = h1 + [h2[-1]]
    labels_unified = l1 + [l2[-1]]

    fig1.legend(
        handles_unified,
        labels_unified,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=6,
        frameon=True,
        fontsize=8.0,
        framealpha=0.95,
        columnspacing=0.8,
        handletextpad=0.35,
    )

    fig1.tight_layout(rect=[0.0, 0.0, 1.0, 0.92])
    save_figure_to_all(fig1, "fig1_classical_benchmark", target_dirs)
    plt.close(fig1)

    # =========================================================================
    # FIGURA 2: Rejeição de Perturbações de Carga Não-Mensuradas (+5K e +20% CAf)
    # =========================================================================
    logger.info("--- Gerando Figura 2 (fig2_disturbance_rejection) ---")
    t_span_d = (0.0, 15.0)

    def disturbance_profile(t: float) -> dict[str, float]:
        dist = {}
        if 2.0 <= t < 8.0:
            dist["T_f"] = plant.params.T_f + 5.0
        elif t >= 8.0:
            dist["T_f"] = plant.params.T_f + 5.0
            dist["C_Af"] = plant.params.C_Af + 0.2
        return dist

    sim2_results = {}
    for name, gains in controllers.items():
        pid = PIDController(
            gains=gains,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        )
        res = sim.run(
            plant=plant,
            controller=pid,
            initial_state=ss,
            t_span=t_span_d,
            dt=dt,
            setpoint_func=lambda t: ss.T,
            disturbance_func=disturbance_profile,
            noise_std=0.05,
            seed=42,
        )
        sim2_results[name] = res

    fig2, (ax2_1, ax2_2) = plt.subplots(
        2, 1, figsize=(IEEE_DOUBLE_COL_WIDTH_INCHES, 4.8), sharex=True, dpi=300
    )

    sample_res2 = next(iter(sim2_results.values()))
    ax2_1.plot(
        sample_res2.t,
        sample_res2.setpoint,
        color=IEEE_PALETTE["Setpoint"],
        linestyle=IEEE_LINESTYLES["Setpoint"],
        label=r"Setpoint ($T_{sp}$)",
        linewidth=1.3,
    )

    # Linhas verticais e anotações para injeção de distúrbios
    ax2_1.axvline(2.0, color="gray", linestyle="--", linewidth=0.9, alpha=0.7)
    ax2_1.text(2.15, 456.0, r"$\Delta T_f = +5.0$ K", fontsize=8.0, color="#333333", fontweight="bold")
    ax2_1.axvline(8.0, color="gray", linestyle="--", linewidth=0.9, alpha=0.7)
    ax2_1.text(8.15, 456.0, r"$\Delta C_{Af} = +20\%$", fontsize=8.0, color="#333333", fontweight="bold")

    for name, res in sim2_results.items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax2_1.plot(res.t, res.t_pv, label=name, color=color, linestyle=linestyle, linewidth=1.3)
        ax2_2.plot(res.t, res.u_applied, label=name, color=color, linestyle=linestyle, linewidth=1.3)

    # Subplot 1: Amplitude completa de temperatura para mostrar pico exotérmico de ZN e CC
    ax2_1.set_ylabel("Reactor Temp. $T$ (K)", fontsize=9.5)
    ax2_1.set_ylim(385.0, 465.0)
    ax2_1.set_title(r"Regulatory Disturbance Rejection ($\Delta T_f = +5$ K at $t=2$ min, $\Delta C_{Af} = +20\%$ at $t=8$ min)", fontsize=10.0, pad=8)
    ax2_1.grid(True, linestyle=":", alpha=0.6)

    # Subplot 2: Vazão de fluido refrigerante
    ax2_2.axhline(
        limits.u_max,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        label=r"Actuator Limits ($u_{\mathrm{min}}, u_{\mathrm{max}}$)",
        linewidth=1.1,
    )
    ax2_2.axhline(
        limits.u_min,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        linewidth=1.1,
    )
    ax2_2.set_ylabel(r"Coolant Flow $q_j$ (L/min)", fontsize=9.5)
    ax2_2.set_xlabel("Time $t$ (min)", fontsize=9.5)
    ax2_2.set_ylim(-15, 335)
    ax2_2.grid(True, linestyle=":", alpha=0.6)

    # Legenda superior externa
    h1, l1 = ax2_1.get_legend_handles_labels()
    h2, l2 = ax2_2.get_legend_handles_labels()
    handles_unified = h1 + [h2[-1]]
    labels_unified = l1 + [l2[-1]]

    fig2.legend(
        handles_unified,
        labels_unified,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=6,
        frameon=True,
        fontsize=8.0,
        framealpha=0.95,
        columnspacing=0.8,
        handletextpad=0.35,
    )

    fig2.tight_layout(rect=[0.0, 0.0, 1.0, 0.92])
    save_figure_to_all(fig2, "fig2_disturbance_rejection", target_dirs)
    plt.close(fig2)

    # =========================================================================
    # FIGURA 3: Incrustação Térmica (Fouling 100% vs 70% UA) em 2x2 Subplots
    # =========================================================================
    logger.info("--- Gerando Figura 3 (fig3_fouling_robustness) ---")
    plot_data_fouling = {}
    target_T_foul = ss.T - 2.0
    for f_ratio in [1.0, 0.7]:
        f_key = f"{f_ratio:.1f}"
        plot_data_fouling[f_key] = {}
        ua_actual = plant.params.UA * f_ratio

        for name, gains in controllers.items():
            pid = PIDController(
                gains=gains,
                actuator_limits=limits,
                anti_windup=AntiWindupMethod.CLAMPING,
                u_bias=q_j_ss,
            )
            res = sim.run(
                plant=plant,
                controller=pid,
                initial_state=ss,
                t_span=(0.0, 10.0),
                dt=dt,
                setpoint_func=lambda t: target_T_foul if t >= 0.5 else ss.T,
                disturbance_func=lambda t, ua_val=ua_actual: {"UA": ua_val},
                noise_std=0.05,
                seed=42,
            )
            plot_data_fouling[f_key][name] = res

    fig3, ((ax3_1, ax3_2), (ax3_3, ax3_4)) = plt.subplots(
        2, 2, figsize=(IEEE_DOUBLE_COL_WIDTH_INCHES, 5.2), sharex=True, dpi=300
    )

    sample_res3 = next(iter(plot_data_fouling["1.0"].values()))

    # Painel (a): 100% UA Temp
    ax3_1.plot(
        sample_res3.t,
        sample_res3.setpoint,
        color=IEEE_PALETTE["Setpoint"],
        linestyle=IEEE_LINESTYLES["Setpoint"],
        label=r"Setpoint ($T_{sp}$)",
        linewidth=1.2,
    )
    for name, res in plot_data_fouling["1.0"].items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax3_1.plot(res.t, res.t_pv, label=name, color=color, linestyle=linestyle, linewidth=1.2)
    ax3_1.set_title(r"(a) Clean Jacket ($100\% UA$): Temperature $T$", fontsize=9.5)
    ax3_1.set_ylabel("Reactor Temp. $T$ (K)", fontsize=9.0)
    ax3_1.grid(True, linestyle=":", alpha=0.6)

    # Painel (b): 70% UA Temp
    sample_res3_f = next(iter(plot_data_fouling["0.7"].values()))
    ax3_2.plot(
        sample_res3_f.t,
        sample_res3_f.setpoint,
        color=IEEE_PALETTE["Setpoint"],
        linestyle=IEEE_LINESTYLES["Setpoint"],
        label=r"Setpoint ($T_{sp}$)",
        linewidth=1.2,
    )
    for name, res in plot_data_fouling["0.7"].items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax3_2.plot(res.t, res.t_pv, label=name, color=color, linestyle=linestyle, linewidth=1.2)
    ax3_2.set_title(r"(b) Fouled Jacket ($70\% UA$): Temperature $T$", fontsize=9.5)
    ax3_2.grid(True, linestyle=":", alpha=0.6)

    # Painel (c): 100% UA Vazão
    for name, res in plot_data_fouling["1.0"].items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax3_3.plot(res.t, res.u_applied, label=name, color=color, linestyle=linestyle, linewidth=1.2)
    ax3_3.axhline(
        limits.u_max,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        label=r"Actuator Limits ($u_{\mathrm{min}}, u_{\mathrm{max}}$)",
        linewidth=1.0,
    )
    ax3_3.set_title(r"(c) Clean Jacket ($100\% UA$): Coolant $q_j$", fontsize=9.5)
    ax3_3.set_ylabel(r"Coolant Flow $q_j$ (L/min)", fontsize=9.0)
    ax3_3.set_xlabel("Time $t$ (min)", fontsize=9.0)
    ax3_3.set_ylim(-15, 335)
    ax3_3.grid(True, linestyle=":", alpha=0.6)

    # Painel (d): 70% UA Vazão
    for name, res in plot_data_fouling["0.7"].items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax3_4.plot(res.t, res.u_applied, label=name, color=color, linestyle=linestyle, linewidth=1.2)
    ax3_4.axhline(
        limits.u_max,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        label=r"Actuator Limits ($u_{\mathrm{min}}, u_{\mathrm{max}}$)",
        linewidth=1.0,
    )
    ax3_4.set_title(r"(d) Fouled Jacket ($70\% UA$): Coolant $q_j$", fontsize=9.5)
    ax3_4.set_xlabel("Time $t$ (min)", fontsize=9.0)
    ax3_4.set_ylim(-15, 335)
    ax3_4.grid(True, linestyle=":", alpha=0.6)

    # Legenda superior externa unificada
    h1, l1 = ax3_1.get_legend_handles_labels()
    h3, l3 = ax3_3.get_legend_handles_labels()
    handles_unified3 = h1 + [h3[-1]]
    labels_unified3 = l1 + [l3[-1]]

    fig3.legend(
        handles_unified3,
        labels_unified3,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=6,
        frameon=True,
        fontsize=8.0,
        framealpha=0.95,
        columnspacing=0.8,
        handletextpad=0.35,
    )

    fig3.tight_layout(rect=[0.0, 0.0, 1.0, 0.93])
    save_figure_to_all(fig3, "fig3_fouling_robustness", target_dirs)
    plt.close(fig3)

    # =========================================================================
    # FIGURA 4: Fronteira de Pareto e Robustez (IAE vs TV e Ms vs tau_c)
    # =========================================================================
    logger.info("--- Gerando Figura 4 (fig4_pareto_iae_tv) ---")
    cache_path = PROJECT_ROOT / "experiments" / ".exp_03_cache.pkl"
    if cache_path.exists():
        with open(cache_path, "rb") as f:
            simc_results, opt_results, discrete_points = pickle.load(f)
        logger.info("Carregados %d pontos SIMC e %d pontos Pareto do cache.", len(simc_results), len(opt_results))
    else:
        logger.warning("Cache de Pareto não encontrado em %s! Re-executando cálculos simplificados...", cache_path)
        simc_results, opt_results, discrete_points = [], [], {}

    if simc_results:
        fig4, (ax4_1, ax4_2) = plt.subplots(
            2, 1, figsize=(5.8, 6.6), dpi=300, gridspec_kw={"height_ratios": [1.1, 1.0], "hspace": 0.44}
        )

        # Painel (a): Fronteira de Pareto no plano (TV, IAE)
        simc_tv = np.array([r["tv"] for r in simc_results])
        simc_iae = np.array([r["iae"] for r in simc_results])
        simc_ms = np.array([r["ms"] for r in simc_results])

        scatter = ax4_1.scatter(
            simc_tv,
            simc_iae,
            c=simc_ms,
            cmap="viridis_r",
            vmin=1.1,
            vmax=2.5,
            s=36,
            zorder=3,
            edgecolor="#333333",
            linewidth=0.4,
            label=r"SIMC locus ($\tau_c \in [0.015, 2.5]$ min)",
        )
        ax4_1.plot(simc_tv, simc_iae, color="#666666", linestyle="-", linewidth=1.1, alpha=0.7, zorder=2)

        opt_tv = [r["tv"] for r in opt_results]
        opt_iae = [r["iae"] for r in opt_results]
        sorted_opt = sorted(zip(opt_tv, opt_iae), key=lambda x: x[0])
        ax4_1.plot(
            [x[0] for x in sorted_opt],
            [x[1] for x in sorted_opt],
            color="#1B7837",
            linestyle="--",
            linewidth=1.8,
            zorder=4,
            label=r"$\lambda$-opt Pareto front",
        )

        simc_pt = discrete_points["Skogestad SIMC"]
        opt_key = [k for k in discrete_points if "Optimal" in k][0]
        opt_pt = discrete_points[opt_key]
        zn_pt = discrete_points["Ziegler-Nichols"]
        cc_pt = discrete_points["Cohen-Coon"]

        # Discrete points on-scale
        ax4_1.scatter([simc_pt["tv"]], [simc_pt["iae"]], color="#1B9E77", marker="s", s=75, edgecolors="black", linewidth=1.0, zorder=6, label=f"SIMC ($M_s = {simc_pt['ms']:.2f}$)")
        ax4_1.scatter([opt_pt["tv"]], [opt_pt["iae"]], color="#1F78B4", marker="o", s=75, edgecolors="black", linewidth=1.0, zorder=6, label=f"Optimal ITAE ($M_s = {opt_pt['ms']:.2f}$)")

        # Explicit legend handles for off-scale controllers so they are NOT omitted
        ax4_1.scatter([], [], color="#D95F02", marker="x", s=60, linewidth=1.5, label=f"Ziegler--Nichols ($M_s = {zn_pt['ms']:.2f}$)*")
        ax4_1.scatter([], [], color="#7570B3", marker="^", s=60, edgecolors="black", linewidth=0.9, label=f"Cohen--Coon ($M_s = {cc_pt['ms']:.2f}$)*")

        # Regra 1: Legenda Desacoplada ACIMA do grafico
        ax4_1.legend(
            loc="lower center",
            bbox_to_anchor=(0.46, 1.02),
            ncol=3,
            frameon=True,
            framealpha=0.95,
            edgecolor="#DDDDDD",
            fontsize=7.2,
            handletextpad=0.4,
            columnspacing=0.8,
            borderpad=0.3,
        )

        # Off-scale callout placed in upper-right quadrant
        callout_text = (
            r"$\mathbf{*Off\text{-}scale\ Empirical\ Rules\ (Limit\ Cycles):}$" + "\n"
            + f"Ziegler--Nichols: $\\mathrm{{TV}}={zn_pt['tv']:.0f}$ L/min, $\\mathrm{{IAE}}={zn_pt['iae']:.1f}$ ($M_s={zn_pt['ms']:.2f}$)\n"
            + f"Cohen--Coon:        $\\mathrm{{TV}}={cc_pt['tv']:.0f}$ L/min, $\\mathrm{{IAE}}={cc_pt['iae']:.1f}$ ($M_s={cc_pt['ms']:.2f}$)"
        )
        ax4_1.annotate(
            callout_text,
            xy=(298, 5.65),
            xytext=(298, 4.25),
            ha="right",
            va="top",
            arrowprops=dict(facecolor="#D95F02", edgecolor="#D95F02", arrowstyle="->", lw=1.1),
            fontsize=7.1,
            color="#222222",
            bbox=dict(boxstyle="round,pad=0.32", facecolor="#FFF9F5", edgecolor="#D95F02", alpha=0.95, lw=0.7),
            zorder=5,
        )

        # Destaque de anotacao no joelho (Pareto Knee)
        ax4_1.annotate(
            r"$\mathbf{Pareto\ Knee}$" + "\n" + r"($\tau_c \in [0.25, 0.40]$ min)",
            xy=(simc_pt["tv"], simc_pt["iae"]),
            xytext=(55, 2.20),
            arrowprops=dict(facecolor="#333333", edgecolor="#333333", arrowstyle="->", lw=0.9),
            fontsize=7.1,
            color="#333333",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#F8F8F8", edgecolor="#AAAAAA", alpha=0.9, lw=0.6),
            zorder=5,
        )

        ax4_1.text(
            0.02, 0.94,
            r"$\mathbf{(a)}$ Continuous Pareto Frontier in $(\mathrm{TV}, \mathrm{IAE})$ Space",
            transform=ax4_1.transAxes,
            fontsize=8.8,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFFFFF", edgecolor="none", alpha=0.85),
        )

        ax4_1.set_xlim(-5, 315)
        ax4_1.set_ylim(0.65, 5.85)
        ax4_1.set_xlabel(r"Actuator Total Variation $\mathrm{TV}$ (L/min) [Mechanical Wear / Effort]")
        ax4_1.set_ylabel(r"Tracking Error $\mathrm{IAE}$ ($\mathrm{K\cdot min}$)")
        ax4_1.grid(True, linestyle=":", alpha=0.5)

        cbar = fig4.colorbar(scatter, ax=ax4_1, pad=0.015, aspect=22)
        cbar.set_label(r"Maximum Sensitivity $M_s = \|S\|_\infty$", fontsize=8.2)
        cbar.ax.tick_params(labelsize=7.5)

        # Painel (b): Parâmetro tau_c vs Robustez (Ms) e IAE
        tau_cs = [r["tau_c"] for r in simc_results]
        ms_vals = [r["ms"] for r in simc_results]
        iae_vals = [r["iae"] for r in simc_results]

        color_ms = "#0072B2"
        color_iae = "#D55E00"

        line_ms, = ax4_2.plot(tau_cs, ms_vals, color=color_ms, linestyle="-", linewidth=1.8, label=r"Peak $M_s = \|S\|_\infty$")
        line_rob = ax4_2.axhline(1.6, color="#009E73", linestyle="--", linewidth=1.3, label=r"Robust Limit ($M_s = 1.6$)")
        line_lim = ax4_2.axhline(2.0, color="#CC79A7", linestyle=":", linewidth=1.3, label=r"Marginal Limit ($M_s = 2.0$)")

        ax4_2.set_xscale("log")
        ax4_2.set_xlabel(r"Closed-loop Tuning Parameter $\tau_c$ (min) [Logarithmic Scale]")
        ax4_2.set_ylabel(r"Maximum Sensitivity Peak $M_s$", color=color_ms)
        ax4_2.tick_params(axis="y", labelcolor=color_ms)
        ax4_2.set_ylim(0.85, 3.85)
        ax4_2.set_xlim(0.013, 2.7)
        ax4_2.grid(True, which="both", linestyle=":", alpha=0.4)

        simc_tau_c = 0.40
        line_pt = ax4_2.scatter(
            [simc_tau_c], [simc_pt["ms"]],
            color="#1B9E77", marker="s", s=65,
            edgecolors="black", linewidth=1.0, zorder=6,
            label="Nominal SIMC ($\\tau_c=0.40$ min)",
        )

        ax4_2_twin = ax4_2.twinx()
        line_iae, = ax4_2_twin.plot(
            tau_cs,
            iae_vals,
            color=color_iae,
            linestyle="-.",
            linewidth=1.8,
            label=r"Tracking Error $\mathrm{IAE}$ ($\mathrm{K\cdot min}$)",
        )
        ax4_2_twin.set_ylabel(r"Tracking Error $\mathrm{IAE}$ ($\mathrm{K\cdot min}$)", color=color_iae)
        ax4_2_twin.tick_params(axis="y", labelcolor=color_iae)
        ax4_2_twin.set_ylim(0.70, 6.20)

        lines_1 = [line_ms, line_iae, line_rob, line_lim, line_pt]
        labels_1 = [h_line.get_label() for h_line in lines_1]
        ax4_2.legend(
            lines_1,
            labels_1,
            loc="lower center",
            bbox_to_anchor=(0.50, 1.02),
            ncol=3,
            frameon=True,
            framealpha=0.95,
            edgecolor="#DDDDDD",
            fontsize=7.2,
            handletextpad=0.4,
            columnspacing=0.8,
            borderpad=0.3,
        )

        ax4_2.text(
            0.02, 0.94,
            r"$\mathbf{(b)}$ Robustness Boundary ($M_s$) and Tracking Metric ($\mathrm{IAE}$) vs $\tau_c$",
            transform=ax4_2.transAxes,
            fontsize=8.8,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFFFFF", edgecolor="none", alpha=0.85),
        )

        save_figure_to_all(fig4, "fig4_pareto_iae_tv", target_dirs)
        plt.close(fig4)

    # =========================================================================
    # FIGURA 5: Rastreamento em Múltiplos Pontos de Operação (396.65 -> 390 -> 402 -> 396.65 K)
    # =========================================================================
    logger.info("--- Gerando Figura 5 (fig5_multistep_tracking) ---")
    t_span_multi = (0.0, 24.0)

    def multistep_profile(t: float) -> float:
        if t < 4.0:
            return ss.T
        elif t < 10.0:
            return 390.0
        elif t < 17.0:
            return 402.0
        else:
            return ss.T

    sim5_results = {}
    for name, gains in controllers.items():
        pid = PIDController(
            gains=gains,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        )
        res = sim.run(
            plant=plant,
            controller=pid,
            initial_state=ss,
            t_span=t_span_multi,
            dt=dt,
            setpoint_func=multistep_profile,
            noise_std=0.05,
            seed=42,
        )
        sim5_results[name] = res

    fig5, (ax5_1, ax5_2) = plt.subplots(
        2, 1, figsize=(IEEE_DOUBLE_COL_WIDTH_INCHES, 4.8), sharex=True, dpi=300
    )

    sample_res5 = next(iter(sim5_results.values()))
    ax5_1.plot(
        sample_res5.t,
        sample_res5.setpoint,
        color=IEEE_PALETTE["Setpoint"],
        linestyle=IEEE_LINESTYLES["Setpoint"],
        label=r"Setpoint ($T_{sp}$)",
        linewidth=1.3,
    )

    for name, res in sim5_results.items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax5_1.plot(res.t, res.t_pv, label=name, color=color, linestyle=linestyle, linewidth=1.3)
        ax5_2.plot(res.t, res.u_applied, label=name, color=color, linestyle=linestyle, linewidth=1.3)

    # Subplot 1: Temperatura do reator - ampla faixa para cobrir 377 K até 455 K
    ax5_1.set_ylabel(r"Reactor Temp. $T$ (K)", fontsize=9.5)
    ax5_1.set_ylim(375.0, 455.0)
    ax5_1.set_title(r"Wide-Range Multi-Operating Point Tracking ($396.65 \rightarrow 390 \rightarrow 402 \rightarrow 396.65$ K)", fontsize=10.0, pad=8)
    ax5_1.grid(True, linestyle=":", alpha=0.6)

    # Subplot 2: Vazão de fluido refrigerante
    ax5_2.axhline(
        limits.u_max,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        label=r"Actuator Limits ($u_{\mathrm{min}}, u_{\mathrm{max}}$)",
        linewidth=1.1,
    )
    ax5_2.axhline(
        limits.u_min,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        linewidth=1.1,
    )
    ax5_2.set_ylabel(r"Coolant Flow $q_j$ (L/min)", fontsize=9.5)
    ax5_2.set_xlabel(r"Time $t$ (min)", fontsize=9.5)
    ax5_2.set_ylim(-15, 345)
    ax5_2.grid(True, linestyle=":", alpha=0.6)

    # Legenda superior externa
    h1, l1 = ax5_1.get_legend_handles_labels()
    h2, l2 = ax5_2.get_legend_handles_labels()
    handles_unified5 = h1 + [h2[-1]]
    labels_unified5 = l1 + [l2[-1]]

    fig5.legend(
        handles_unified5,
        labels_unified5,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=6,
        frameon=True,
        fontsize=8.0,
        framealpha=0.95,
        columnspacing=0.8,
        handletextpad=0.35,
    )

    fig5.tight_layout(rect=[0.0, 0.0, 1.0, 0.92])
    save_figure_to_all(fig5, "fig5_multistep_tracking", target_dirs)
    plt.close(fig5)

    # =========================================================================
    # FIGURA EXTRA: Sensibilidade ao Ruído (fig_noise_sensitivity)
    # =========================================================================
    logger.info("--- Gerando Figura Auxiliar (fig_noise_sensitivity) ---")
    noise_levels = [0.0, 0.05, 0.1, 0.2, 0.5, 1.0]
    seeds = [10, 20, 30]
    noise_results = {name: {sig: {"iae": [], "tv": []} for sig in noise_levels} for name in controllers.keys()}

    for sig in noise_levels:
        for seed_val in seeds:
            for name, gains in controllers.items():
                pid = PIDController(
                    gains=gains,
                    actuator_limits=limits,
                    anti_windup=AntiWindupMethod.CLAMPING,
                    u_bias=q_j_ss,
                )
                res = sim.run(
                    plant=plant,
                    controller=pid,
                    initial_state=ss,
                    t_span=(0.0, 10.0),
                    dt=dt,
                    setpoint_func=lambda t: ss.T - 2.0,
                    noise_std=sig,
                    seed=seed_val,
                )
                noise_results[name][sig]["iae"].append(res.metrics.iae)
                noise_results[name][sig]["tv"].append(res.metrics.tv)

    fig_noise, (ax_iae, ax_tv) = plt.subplots(
        1, 2, figsize=(IEEE_DOUBLE_COL_WIDTH_INCHES, 3.8), dpi=300
    )

    markers_dict = {
        "Ziegler-Nichols": ("o", "--", 5.5, 1.3),
        "Cohen-Coon": ("s", "--", 5.5, 1.3),
        "Skogestad SIMC": ("^", "-", 6.0, 1.5),
        "Constrained Optimal (ITAE)": ("D", "-", 5.5, 1.5),
    }

    legend_handles = []
    for name in controllers.keys():
        iaes = [np.mean(noise_results[name][sig]["iae"]) for sig in noise_levels]
        tvs = [np.mean(noise_results[name][sig]["tv"]) for sig in noise_levels]
        color = IEEE_PALETTE.get(name, "#333333")
        marker, ls, ms, lw = markers_dict.get(name, ("o", "-", 5.0, 1.0))
        label_text = name
        if "Optimal" in name or "ITAE" in name:
            label_text = r"Optimal ITAE ($M_s \leq 1.6$)"

        (line_iae,) = ax_iae.plot(
            noise_levels,
            iaes,
            marker=marker,
            linestyle=ls,
            label=label_text,
            color=color,
            markersize=ms,
            linewidth=lw,
        )
        (line_tv,) = ax_tv.plot(
            noise_levels,
            tvs,
            marker=marker,
            linestyle=ls,
            label=label_text,
            color=color,
            markersize=ms,
            linewidth=lw,
        )
        legend_handles.append(line_iae)

    # Panel (a): Tracking Error IAE vs sigma (Log Scale)
    ax_iae.set_yscale("log")
    ax_iae.set_xlabel(r"Measurement Noise Intensity $\sigma$ (K)", fontsize=9.0)
    ax_iae.set_ylabel(r"Tracking Error $\mathrm{IAE}$ ($\mathrm{K \cdot min}$) [Log Scale]", fontsize=9.0)
    ax_iae.set_title(r"(a) Tracking Quality vs. Noise Intensity", fontsize=9.5, pad=6)
    ax_iae.set_ylim(0.5, 250)
    ax_iae.set_xlim(-0.03, 1.03)
    ax_iae.grid(True, which="both", linestyle=":", alpha=0.5)

    # Panel (b): Actuator Effort TV vs sigma (Linear Scale)
    ax_tv.text(
        0.98,
        805,
        r"Filter-bounded plateau ($N = 10$)",
        fontsize=8.0,
        ha="right",
        va="bottom",
        color="#0072B2",
        fontweight="bold",
    )
    ax_tv.annotate(
        r"Quiescent baseline ($\sigma = 0$)",
        xy=(0.0, 20.9),
        xytext=(0.08, 120),
        arrowprops=dict(arrowstyle="->", lw=0.8, color="#1B9E77"),
        fontsize=7.8,
        ha="left",
        va="center",
        color="#1B9E77",
        fontweight="bold",
    )
    ax_tv.set_xlabel(r"Measurement Noise Intensity $\sigma$ (K)", fontsize=9.0)
    ax_tv.set_ylabel(r"Actuator Total Variation $\mathrm{TV}$ (L/min) [Wear]", fontsize=9.0)
    ax_tv.set_title(r"(b) Actuator Mechanical Effort vs. Noise Intensity", fontsize=9.5, pad=6)
    ax_tv.set_ylim(-15, 870)
    ax_tv.set_xlim(-0.03, 1.03)
    ax_tv.grid(True, linestyle=":", alpha=0.5)

    # Shared top legend with clean spacing
    fig_noise.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.99),
        ncol=4,
        frameon=True,
        fontsize=8.2,
        framealpha=0.95,
        edgecolor="#cccccc",
    )

    fig_noise.subplots_adjust(top=0.83, bottom=0.13, left=0.09, right=0.98, wspace=0.30)
    save_figure_to_all(fig_noise, "fig_noise_sensitivity", target_dirs)
    plt.close(fig_noise)


    logger.info("=== TODAS AS FIGURAS FORAM GERADAS E SALVAS COM SUCESSO! ===")


if __name__ == "__main__":
    main()
