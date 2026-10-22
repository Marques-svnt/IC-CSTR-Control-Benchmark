# -*- coding: utf-8 -*-
"""Campanha abrangente de robustez, incerteza paramétrica e rejeição de distúrbios no CSTR.

Avalia os controladores PID clássicos (Ziegler-Nichols, Cohen-Coon, Skogestad SIMC
e ITAE Ótimo com restrição de sensibilidade máxima) através de quatro ensaios:
1. Rejeição de perturbações de carga não-mensuradas (choques térmicos e de
   concentração na alimentação).
2. Incrustação térmica (fouling) na camisa de resfriamento (degradação de UA de 100% até 60%).
3. Varredura de ruído de medição nos sensores e fronteira de esforço do atuador (IAE vs TV).
4. Rastreamento não-linear de múltiplos pontos de operação em larga escala.

Gera todas as figuras com resolução de 300 DPI e tabelas no padrão booktabs para o Artigo 1.
"""

# %% [1. Importações e Configuração de Caminhos]
import logging
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

# Adiciona a raiz do projeto ao sys.path para garantir importações relativas e absolutas
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from src.classical_control.closed_loop import ClosedLoopSimulator
from src.classical_control.foptd import FOPTDModel, identify_foptd
from src.classical_control.pid_controller import AntiWindupMethod, PIDController, PIDGains
from src.classical_control.tuning_analytical import TuningRule, tune_analytical
from src.classical_control.tuning_optimization import (
    OptimizationCriterion,
    calculate_maximum_sensitivity_foptd,
    tune_by_optimization,
)
from src.controllers.optimal.nmpc_controller import CstrNmpcController
from src.evaluation.plot_styles import (
    IEEE_LINESTYLES,
    IEEE_MARKERS,
    IEEE_PALETTE,
    get_figure_dimensions,
    setup_ieee_style,
)
from src.evaluation.sobol_sensitivity import (
    CSTR_UNCERTAINTY_PROBLEM,
    closed_loop_sobol,
    pid_factory,
)
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRPlant, CSTRState
from src.sim_core.integrator import NumericalIntegrator

# Configuração de logging estruturado
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("exp_02_robustness")

CONTROLLER_COLORS = IEEE_PALETTE


# %% [2. Identificação FOPTD e Sintonia dos Controladores PID]
OVERLEAF_DIR = PROJECT_ROOT / "Artigos_Rascunhos" / "Artigo_01_Classic_Methods" / "overleaf"
RESULTS_DIR = PROJECT_ROOT / "results"
# Per-paper builds override these two globals (CSV mirror folder, LaTeX float of the target class)
TABLE_FLOAT_ENV = "tableorg"
NMPC_HORIZON = 50  # 1.0 min at dt = 0.02 min; N = 75 gives identical nominal IAE
OPT_ITAE = "Optimal ITAE ($M_s \\leq 1.6$)"
OPT_ITAE_2DOF = "2-DOF Optimal ITAE"
BENCHMARK_LIMITS = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)


def identify_nominal_foptd(plant: CSTRPlant, ss: CSTRState, q_j_ss: float) -> FOPTDModel:
    """Open-loop +10 L/min step test and FOPTD fit (Sundaresan-Krishnaswamy + LM)."""
    logger.info("Executando degrau de identificação em malha aberta (+10 L/min)...")
    delta_q = 10.0
    id_res = NumericalIntegrator(method="RK45").simulate_open_loop(
        plant=plant,
        initial_state=ss,
        t_span=(0.0, 6.0),
        dt=0.02,
        u_func=lambda t: q_j_ss + delta_q,
    )
    foptd, rmse = identify_foptd(t=id_res.t, y=id_res.states[:, 1], delta_u=delta_q, y0=ss.T)
    logger.info(
        "FOPTD: K=%.4f K/(L/min), tau=%.4f min, theta=%.4f min (RMSE=%.4f K)",
        foptd.k_p,
        foptd.tau,
        foptd.theta,
        rmse,
    )
    return foptd


def setup_controllers(
    plant: CSTRPlant, ss: CSTRState, q_j_ss: float
) -> tuple[dict[str, PIDGains], FOPTDModel]:
    """Identifies the FOPTD model and tunes the seven PID baselines of the benchmark.

    ZN, Cohen-Coon, Tyreus-Luyben, AMIGO and SIMC (tau_c = 0.4 min) are analytical;
    Optimal ITAE minimises ITAE on the non-linear plant with Ms <= 1.6 evaluated on the
    identified dead-time FOPTD loop; its 2-DOF variant reuses the same feedback gains with
    setpoint weights beta = 0.5, gamma = 0 (identical L(s), hence identical Ms); AMIGO gets the
    same 2-DOF variant, since Astrom-Hagglund design it for use with setpoint weighting.

    Returns:
        (name -> PIDGains, identified FOPTD model).
    """
    foptd = identify_nominal_foptd(plant, ss, q_j_ss)
    analytical = {
        "Ziegler-Nichols": tune_analytical(foptd, rule=TuningRule.ZIEGLER_NICHOLS_PID),
        "Cohen-Coon": tune_analytical(foptd, rule=TuningRule.COHEN_COON_PID),
        "Tyreus-Luyben": tune_analytical(foptd, rule=TuningRule.TYREUS_LUYBEN),
        "AMIGO": tune_analytical(foptd, rule=TuningRule.AMIGO),
        "Skogestad SIMC": tune_analytical(foptd, rule=TuningRule.SKOGESTAD_SIMC_PID, tau_c=0.4),
    }

    def itae(g: PIDGains) -> float:
        """Optimizer objective without penalties: ITAE of the -2 K step over 6 min."""
        res = ClosedLoopSimulator().run(
            plant=plant,
            controller=PIDController(g, BENCHMARK_LIMITS, AntiWindupMethod.CLAMPING, u_bias=q_j_ss),
            initial_state=ss,
            t_span=(0.0, 6.0),
            dt=0.02,
            setpoint_func=lambda t: ss.T - 2.0,
        )
        return res.metrics.itae

    # Nelder-Mead is local: start from the default guess and from every analytical tuning
    # inside the robust set, keep the best feasible optimum.
    starts = [None] + [
        g for g in analytical.values() if calculate_maximum_sensitivity_foptd(foptd, g) <= 1.6
    ]
    candidates = [
        tune_by_optimization(
            plant=plant,
            nominal_state=ss,
            q_j_ss=q_j_ss,
            target_dT=-2.0,
            initial_gains=g0,
            criterion=OptimizationCriterion.ITAE,
            max_ms=1.6,
            t_sim=6.0,
            dt=0.02,
            foptd=foptd,
            limits=BENCHMARK_LIMITS,
        )
        for g0 in starts
    ]
    feasible = [g for g in candidates if calculate_maximum_sensitivity_foptd(foptd, g) <= 1.6 + 1e-3]
    opt = min(feasible, key=itae)
    logger.info("Optimal ITAE multi-start: %d starts -> %s (ITAE=%.4f)", len(starts), opt, itae(opt))
    gains = {
        "Ziegler-Nichols": analytical["Ziegler-Nichols"],
        "Cohen-Coon": analytical["Cohen-Coon"],
        "Tyreus-Luyben": analytical["Tyreus-Luyben"],
        "AMIGO": analytical["AMIGO"],
        "2-DOF AMIGO": replace(analytical["AMIGO"], beta=0.5, gamma=0.0),
        "Skogestad SIMC": analytical["Skogestad SIMC"],
        OPT_ITAE: opt,
        OPT_ITAE_2DOF: replace(opt, beta=0.5, gamma=0.0),
    }
    return gains, foptd


def make_factories(
    gains: dict[str, PIDGains],
    q_j_ss: float,
    limits: ActuatorLimits,
    dt: float,
    y_ss: float,
    include_nmpc: bool = True,
) -> dict[str, Callable[..., Any]]:
    """Zero-state controller constructors: f(sensor_noise_std=0.0, seed=None) -> controller.

    The NMPC-MHE jacket thermocouple uses the same noise level as the reactor sensor.
    `y_ss` fixes the 2-DOF deviation origin so a noisy first sample cannot bias e_p.
    """
    factories: dict[str, Callable[..., Any]] = {}
    for name, g in gains.items():
        factories[name] = (
            lambda sensor_noise_std=0.0, seed=None, g=g: PIDController(
                gains=g,
                actuator_limits=limits,
                anti_windup=AntiWindupMethod.CLAMPING,
                u_bias=q_j_ss,
                y_ss=y_ss,
            )
        )
    if include_nmpc:
        for name, mode in (("NMPC-Oracle", "oracle"), ("NMPC-MHE", "mhe")):
            factories[name] = (
                lambda sensor_noise_std=0.0, seed=None, mode=mode: CstrNmpcController(
                    horizon_steps=NMPC_HORIZON,
                    t_step_min=dt,
                    u_bias=q_j_ss,
                    feedback_mode=mode,
                    max_slew_rate=limits.max_slew_rate,
                    u_min=limits.u_min,
                    u_max=limits.u_max,
                    tj_noise_std=sensor_noise_std,
                    seed=seed,
                )
            )
    return factories


# %% [3. Utilitário de Exportação de Tabelas em LaTeX]
def export_latex_table(
    data: list[dict[str, Any]],
    output_path: Path,
    caption: str,
    label: str,
) -> None:
    """Exporta registros tabulares para código LaTeX no padrão editorial booktabs.

    Args:
        data: Lista de dicionários representando as linhas da tabela.
        output_path: Caminho de destino para salvar o arquivo .tex.
        caption: Legenda descritiva da tabela.
        label: Rótulo de referência cruzada no LaTeX.
    """
    df = pd.DataFrame(data)
    cols = " & ".join(df.columns)
    rows_list = []
    for _, row in df.iterrows():
        rows_list.append(" & ".join(str(val) for val in row.values) + r" \\")
    rows_str = "\n".join(rows_list)
    col_align = "l" + "c" * (len(df.columns) - 1)

    # sn-jnl wraps `table` in threeparttable, which breaks \\resizebox; `tableorg` is the
    # class's saved plain float. Tables wider than the text block are scaled down only.
    placement = "t" if TABLE_FLOAT_ENV.endswith("*") else "htbp"  # starred floats: top only
    latex_table = f"""\\begin{{{TABLE_FLOAT_ENV}}}[{placement}]
\\centering
\\footnotesize
\\caption{{{caption}}}
\\label{{{label}}}
\\resizebox{{\\ifdim\\width>\\textwidth\\textwidth\\else\\width\\fi}}{{!}}{{%
\\begin{{tabular}}{{{col_align}}}
\\toprule
{cols} \\\\
\\midrule
{rows_str}
\\bottomrule
\\end{{tabular}}%
}}
\\end{{{TABLE_FLOAT_ENV}}}
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex_table, encoding="utf-8")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RESULTS_DIR / f"{output_path.stem}.csv", index=False)  # same strings as the .tex
    logger.info("Tabela LaTeX salva com sucesso em: %s", output_path)


# %% [4. Ensaio 1: Rejeição de Perturbações de Carga Não-Mensuradas]
def run_load_disturbance_campaign(
    plant: CSTRPlant,
    ss: CSTRState,
    q_j_ss: float,
    controllers: dict[str, Callable[..., Any]],
    limits: ActuatorLimits,
    figures_dir: Path,
    tables_dir: Path,
) -> None:
    """Avalia o controle regulatório contra perturbações não-mensuradas na alimentação.

    Cronograma didático de perturbações:
    - t em [0, 2) min: Regime permanente nominal.
    - t em [2, 8) min: Choque térmico de alimentação Delta T_f = +5.0 K.
    - t em [8, 15] min: Choque cumulativo de concentração Delta C_Af = +0.2 mol/L (+20%).

    Args:
        plant: Modelo físico do reator CSTR.
        ss: Estado estacionário nominal.
        q_j_ss: Vazão base de resfriamento [L/min].
        controllers: Dicionário de controladores PID sintonizados.
        limits: Restrições físicas de saturação e taxa da válvula.
        figures_dir: Diretório de destino para figuras.
        tables_dir: Diretório de destino para tabelas.
    """
    logger.info("=== Executando Campanha de Rejeição de Perturbações de Carga ===")
    sim = ClosedLoopSimulator()
    t_span = (0.0, 15.0)
    dt = 0.02

    def disturbance_profile(t: float) -> dict[str, float]:
        dist = {}
        if 2.0 <= t < 8.0:
            dist["T_f"] = plant.params.T_f + 5.0
        elif t >= 8.0:
            dist["T_f"] = plant.params.T_f + 5.0
            dist["C_Af"] = plant.params.C_Af + 0.2
        return dist

    has_nmpc = any(name.startswith("NMPC") for name in controllers)
    sim_results = {}
    table_rows = []

    for name, make in controllers.items():
        pid = make(sensor_noise_std=0.05, seed=42)
        res = sim.run(
            plant=plant,
            controller=pid,
            initial_state=ss,
            t_span=t_span,
            dt=dt,
            setpoint_func=lambda t: ss.T,  # Controle puramente regulatório em T nominal
            disturbance_func=disturbance_profile,
            noise_std=0.05,
            seed=42,
        )
        sim_results[name] = res

        dev = np.abs(res.t_pv - ss.T)
        peak_dev = np.max(dev[res.t >= 2.0])

        table_rows.append({
            "Method": name,
            "IAE": f"{res.metrics.iae:.2f}",
            "ITAE": f"{res.metrics.itae:.2f}",
            "TV (L/min)": f"{res.metrics.tv:.1f}",
            "Peak Dev (K)": f"{peak_dev:.2f}",
            "Max Valve (L/min)": f"{np.max(res.u_applied):.1f}",
            r"\(T(t_f) - T_{sp}\) (K)": f"{res.states[-1, 1] - ss.T:+.2f}",
        })
        if has_nmpc:
            a_hat = getattr(pid, "_estimated_alpha_ua", None)
            table_rows[-1][r"\(\hat\alpha_{UA}(t_f)\)"] = "--" if a_hat is None else f"{a_hat:.3f}"

    export_latex_table(
        data=table_rows,
        output_path=tables_dir / "disturbance_rejection_table.tex",
        caption="Regulatory performance under combined feed temperature ($+5$~K) "
        "and concentration ($+20\\%$) load disturbances. $T(t_f) - T_{sp}$ is the true "
        "temperature error at $t_f = 15$~min"
        + (
            "; $\\hat\\alpha_{UA}(t_f)$ is the NMPC fouling estimate (true value $1.0$, "
            "no fouling in this test)."
            if has_nmpc
            else "."
        ),
        label="tab:load_disturbance",
    )

    # Geração dos gráficos IEEE em coluna única (3.5 in) com Legenda Unificada Superior
    setup_ieee_style(single_column=True)
    fig_w, fig_h = get_figure_dimensions(columns=1, height_override=4.2)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(fig_w, fig_h), sharex=True, dpi=300)

    # Sinal de referência nominal
    sample_res = next(iter(sim_results.values()))
    ax1.plot(
        sample_res.t,
        sample_res.setpoint,
        color=IEEE_PALETTE["Setpoint"],
        linestyle=IEEE_LINESTYLES["Setpoint"],
        label="Target $T_{sp}$",
        linewidth=1.2,
    )

    # Linhas verticais indicando a injeção dos distúrbios com anotações em posições desobstruídas
    ax1.axvline(2.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)
    ax1.text(2.1, 395.6, r"$\Delta T_f = +5$ K", fontsize=7.2, color="#444444")
    ax1.axvline(8.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)
    ax1.text(8.1, 395.6, r"$\Delta C_{Af} = +20\%$", fontsize=7.2, color="#444444")

    for name, res in sim_results.items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax1.plot(res.t, res.t_pv, label=name, color=color, linestyle=linestyle, linewidth=1.2)
        ax2.plot(res.t, res.u_applied, label=name, color=color, linestyle=linestyle, linewidth=1.2)

    # Subplot 1: Temperatura do reator com faixa [395.0, 404.0] K
    # Sem legenda interna: desobstrução completa dos transientes e picos de distúrbio
    ax1.set_ylabel("Reactor Temp. $T$ (K)", fontsize=8.5)
    ax1.set_title(r"Load Disturbance Rejection ($+5$ K & $+20\% C_{Af}$)", fontsize=9.0)
    ax1.set_ylim(394.0, 406.0)
    ax1.grid(True, linestyle=":", alpha=0.6)

    # Subplot 2: Vazão de fluido refrigerante com limites físicos
    ax2.axhline(
        limits.u_max,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        label=r"Limits ($u_{\mathrm{min}}, u_{\mathrm{max}}$)",
        linewidth=1.0,
    )
    ax2.axhline(
        limits.u_min,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        linewidth=1.0,
    )
    ax2.set_ylabel(r"Coolant Flow $q_j$ (L/min)", fontsize=8.5)
    ax2.set_xlabel("Time $t$ (min)", fontsize=8.5)
    ax2.set_ylim(-15, 335)
    ax2.grid(True, linestyle=":", alpha=0.6)

    # Construção da Legenda Unificada Superior (fig.legend) estilo Figura 3
    # Extrai manipuladores de ax1 (referência + 4 PIDs) e ax2 (limites de saturação)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    handles_unified = h1 + [h2[-1]]
    labels_unified = l1 + [l2[-1]]

    fig.legend(
        handles_unified,
        labels_unified,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=4,
        frameon=True,
        fontsize=5.6,
        framealpha=0.92,
        columnspacing=0.4,
        handletextpad=0.25,
    )

    plt.tight_layout(rect=[0.0, 0.0, 1.0, 0.885])
    fig_png = figures_dir / "fig2_disturbance_rejection.png"
    fig_pdf = figures_dir / "fig2_disturbance_rejection.pdf"
    plt.savefig(fig_png, dpi=300)
    plt.savefig(fig_pdf)
    plt.close()
    logger.info("Figuras salvas com sucesso em: %s e %s", fig_png, fig_pdf)


# %% [5. Ensaio 2: Incrustação Térmica na Camisa (Degradação de UA)]
def run_fouling_campaign(
    plant: CSTRPlant,
    ss: CSTRState,
    q_j_ss: float,
    controllers: dict[str, Callable[..., Any]],
    limits: ActuatorLimits,
    figures_dir: Path,
    tables_dir: Path,
) -> None:
    """Avalia a estabilidade e a perda de desempenho com a degradação térmica de UA (incrustação).

    Passo a passo didático:
    1. Varia o coeficiente global de transferência térmica UA de 100% até 60% do valor de projeto.
    2. Aplica degrau de setpoint (-2 K) e analisa a lentidão e saturação da válvula.
    3. Constrói um painel 2x2 com LEGENDA COMPARTILHADA ÚNICA no topo da figura (fig.legend),
       eliminando 4 caixas repetitivas e desobstruindo integralmente todos os subplots.

    Args:
        plant: Modelo físico do CSTR.
        ss: Estado estacionário nominal.
        q_j_ss: Vazão base de resfriamento.
        controllers: Controladores PID avaliados.
        limits: Restrições físicas da válvula.
        figures_dir: Diretório de destino para figuras.
        tables_dir: Diretório de destino para tabelas.
    """
    logger.info("=== Executando Campanha de Incrustação Térmica (Degradação de UA) ===")
    sim = ClosedLoopSimulator()
    t_span = (0.0, 10.0)
    dt = 0.02
    target_T = ss.T - 2.0

    fouling_levels = [1.0, 0.9, 0.8, 0.7, 0.6]  # UA / UA_nominal
    table_rows = []

    # Armazena trajetórias de 100% UA (limpo) e 70% UA (incrustação severa) para o gráfico 2x2
    plot_data: dict[str, dict[str, Any]] = {"1.0": {}, "0.7": {}}

    for name, make in controllers.items():
        for f_ratio in fouling_levels:
            ua_actual = plant.params.UA * f_ratio
            pid = make()

            res = sim.run(
                plant=plant,
                controller=pid,
                initial_state=ss,
                t_span=t_span,
                dt=dt,
                setpoint_func=lambda t: target_T,  # same servo protocol as exp_01 (step at t = 0)
                disturbance_func=lambda t: {"UA": ua_actual},
                noise_std=0.0,  # deterministic sweep; noise is studied in the Monte Carlo campaign
            )

            if f_ratio in [1.0, 0.7]:
                plot_data[str(f_ratio)][name] = res

            table_rows.append({
                "Method": name,
                "$UA / UA_{\\text{nom}}$": f"{int(f_ratio * 100)}\\%",
                "IAE": f"{res.metrics.iae:.2f}",
                "ITAE": f"{res.metrics.itae:.2f}",
                "TV (L/min)": f"{res.metrics.tv:.1f}",
                "$M_p$ (\\%)": f"{res.metrics.overshoot_pct:.1f}",
            })

    export_latex_table(
        data=table_rows,
        output_path=tables_dir / "fouling_sensitivity_table.tex",
        caption="Impact of heat exchanger fouling ($UA$ reduction from $100\\%$ to $60\\%$) "
        "on closed-loop tracking metrics.",
        label="tab:fouling_sensitivity",
    )

    # Figura em Coluna Dupla (7.16 in) no formato 2x2 com Legenda Compartilhada Superior
    setup_ieee_style(single_column=False)
    fig_w, fig_h = get_figure_dimensions(columns=2, height_override=4.2)
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(fig_w, fig_h), sharex=True, dpi=300)

    sample_res = next(iter(plot_data["1.0"].values()))

    # Painel (a): Temperatura T com Camisa Limpa (100% UA)
    ax1.plot(
        sample_res.t,
        sample_res.setpoint,
        color=IEEE_PALETTE["Setpoint"],
        linestyle=IEEE_LINESTYLES["Setpoint"],
        label="Target $T_{sp}$",
        linewidth=1.2,
    )
    for name, res in plot_data["1.0"].items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax1.plot(res.t, res.t_pv, label=name, color=color, linestyle=linestyle, linewidth=1.2)
    ax1.set_title(r"(a) Clean Jacket ($100\% UA$): Temperature $T$", fontsize=9.0)
    ax1.set_ylabel("Reactor Temp. $T$ (K)", fontsize=8.5)
    ax1.grid(True, linestyle=":", alpha=0.6)

    # Painel (b): Temperatura T com Camisa Incrustada (70% UA)
    ax2.plot(
        sample_res.t,
        sample_res.setpoint,
        color=IEEE_PALETTE["Setpoint"],
        linestyle=IEEE_LINESTYLES["Setpoint"],
        label="Target $T_{sp}$",
        linewidth=1.2,
    )
    for name, res in plot_data["0.7"].items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax2.plot(res.t, res.t_pv, label=name, color=color, linestyle=linestyle, linewidth=1.2)
    ax2.set_title(r"(b) Fouled Jacket ($70\% UA$): Temperature $T$", fontsize=9.0)
    ax2.grid(True, linestyle=":", alpha=0.6)

    # Painel (c): Vazão de Fluido q_j com Camisa Limpa (100% UA)
    for name, res in plot_data["1.0"].items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax3.plot(res.t, res.u_applied, label=name, color=color, linestyle=linestyle, linewidth=1.2)
    ax3.axhline(
        limits.u_max,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        label=r"Limits ($u_{\mathrm{min}}, u_{\mathrm{max}}$)",
        linewidth=1.0,
    )
    ax3.set_title(r"(c) Clean Jacket ($100\% UA$): Coolant $q_j$", fontsize=9.0)
    ax3.set_ylabel(r"Coolant Flow $q_j$ (L/min)", fontsize=8.5)
    ax3.set_xlabel("Time $t$ (min)", fontsize=8.5)
    ax3.set_ylim(-15, 335)
    ax3.grid(True, linestyle=":", alpha=0.6)

    # Painel (d): Vazão de Fluido q_j com Camisa Incrustada (70% UA)
    for name, res in plot_data["0.7"].items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax4.plot(res.t, res.u_applied, label=name, color=color, linestyle=linestyle, linewidth=1.2)
    ax4.axhline(
        limits.u_max,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        label=r"Limits ($u_{\mathrm{min}}, u_{\mathrm{max}}$)",
        linewidth=1.0,
    )
    ax4.set_title(r"(d) Fouled Jacket ($70\% UA$): Coolant $q_j$", fontsize=9.0)
    ax4.set_xlabel("Time $t$ (min)", fontsize=8.5)
    ax4.set_ylim(-15, 335)
    ax4.grid(True, linestyle=":", alpha=0.6)

    # Construção da Legenda Unificada Superior (fig.legend)
    # Extrai os manipuladores de ax1 (referência + 4 PIDs) e ax3 (limites físicos)
    h1, l1 = ax1.get_legend_handles_labels()
    h3, l3 = ax3.get_legend_handles_labels()
    handles_unified = h1 + [h3[-1]]
    labels_unified = l1 + [l3[-1]]

    fig.legend(
        handles_unified,
        labels_unified,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=6,
        frameon=True,
        fontsize=7.2,
        framealpha=0.92,
        columnspacing=0.8,
        handletextpad=0.4,
    )

    # Ajusta a margem superior para acomodar perfeitamente a legenda sem sobrepor os títulos
    plt.tight_layout(rect=[0.0, 0.0, 1.0, 0.90])
    fig_png = figures_dir / "fig3_fouling_robustness.png"
    fig_pdf = figures_dir / "fig3_fouling_robustness.pdf"
    plt.savefig(fig_png, dpi=300)
    plt.savefig(fig_pdf)
    plt.close()
    logger.info("Figuras salvas com sucesso em: %s e %s", fig_png, fig_pdf)


# %% [6. Ensaio 3: Sensibilidade a Ruído de Medição e Desgaste do Atuador (IAE vs TV)]
def run_noise_and_pareto_campaign(
    plant: CSTRPlant,
    ss: CSTRState,
    q_j_ss: float,
    controllers: dict[str, Callable[..., Any]],
    limits: ActuatorLimits,
    figures_dir: Path,
    tables_dir: Path,
) -> None:
    """Quantifica a sensibilidade ao ruído estocástico de medição via Monte Carlo.

    Passo a passo didático:
    1. Varia o desvio padrão do ruído gaussiano sigma em [0.0, 0.1, 0.2, 0.5, 1.0] K.
    2. Executa simulações Monte Carlo com 5 sementes pseudo-aleatórias para cada nível de ruído.
    3. Calcula média e desvio padrão para IAE (erro de rastreamento) e TV (desgaste da válvula).
    4. Plota o diagrama de dispersão IAE vs TV com anotações claras e legenda desobstruída.

    Args:
        plant: Modelo físico do CSTR.
        ss: Estado estacionário nominal.
        q_j_ss: Vazão base de resfriamento.
        controllers: Controladores PID avaliados.
        limits: Restrições físicas da válvula.
        figures_dir: Diretório de destino para figuras.
        tables_dir: Diretório de destino para tabelas.
    """
    logger.info("=== Executando Campanha de Ruído nos Sensores e Chattering da Válvula ===")
    sim = ClosedLoopSimulator()
    t_span = (0.0, 10.0)
    dt = 0.02
    target_T = ss.T - 2.0

    noise_levels = [0.0, 0.1, 0.2, 0.5, 1.0]  # Desvio padrão do ruído gaussiano [K]
    n_monte_carlo = 30

    results: dict[str, dict[float, dict[str, list[float]]]] = {
        name: {sigma: {"iae": [], "tv": []} for sigma in noise_levels}
        for name in controllers
    }

    def one_run(name: str, sigma: float, seed: int) -> tuple[str, float, float, float]:
        ctrl = controllers[name](sensor_noise_std=sigma, seed=10_000 + seed)
        res = sim.run(
            plant=plant,
            controller=ctrl,
            initial_state=ss,
            t_span=t_span,
            dt=dt,
            setpoint_func=lambda t: target_T,  # same servo protocol as exp_01 (step at t = 0)
            noise_std=sigma,
            seed=100 + seed,
        )
        return name, sigma, res.metrics.iae, res.metrics.tv

    tasks = [
        (name, sigma, seed)
        for name in controllers
        for sigma in noise_levels
        for seed in range(n_monte_carlo)
    ]
    for name, sigma, iae, tv in Parallel(n_jobs=-1)(delayed(one_run)(*t) for t in tasks):
        results[name][sigma]["iae"].append(iae)
        results[name][sigma]["tv"].append(tv)

    table_rows = []
    for name in controllers:
        for sigma in noise_levels:
            mean_iae = float(np.mean(results[name][sigma]["iae"]))
            std_iae = float(np.std(results[name][sigma]["iae"]))
            mean_tv = float(np.mean(results[name][sigma]["tv"]))
            std_tv = float(np.std(results[name][sigma]["tv"]))

            table_rows.append({
                "Method": name,
                "Noise $\\sigma$ (K)": f"{sigma:.1f}",
                "IAE (mean $\\pm$ std)": f"{mean_iae:.2f} $\\pm$ {std_iae:.2f}",
                "TV (L/min)": f"{mean_tv:.1f} $\\pm$ {std_tv:.1f}",
            })

    export_latex_table(
        data=table_rows,
        output_path=tables_dir / "noise_chattering_table.tex",
        caption="Sensitivity of tracking error (IAE) and actuator effort (TV) "
        "to measurement noise levels across $30$ Monte Carlo runs.",
        label="tab:noise_sensitivity",
    )

    # Configuração gráfica no padrão IEEE de coluna única
    setup_ieee_style(single_column=True)
    fig_w, fig_h = get_figure_dimensions(columns=1, height_override=3.9)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=300)

    for name in controllers:
        marker = IEEE_MARKERS[name]
        iaes = [np.mean(results[name][sig]["iae"]) for sig in noise_levels]
        tvs = [np.mean(results[name][sig]["tv"]) for sig in noise_levels]
        color = CONTROLLER_COLORS[name]
        ax.plot(
            tvs,
            iaes,
            marker=marker,
            linestyle=IEEE_LINESTYLES[name],
            label=name,
            color=color,
            markersize=5.0,
            linewidth=1.2,
        )

    # Anotações limpas com setas indicando os extremos de ruído sem sobreposição de texto
    ref = "Skogestad SIMC" if "Skogestad SIMC" in controllers else next(iter(controllers))
    sample_iaes = [np.mean(results[ref][sig]["iae"]) for sig in noise_levels]
    sample_tvs = [np.mean(results[ref][sig]["tv"]) for sig in noise_levels]
    ax.annotate(
        r"$\sigma = 0.0$ K",
        xy=(sample_tvs[0], sample_iaes[0]),
        xytext=(35, 12),
        textcoords="offset points",
        fontsize=7.2,
        color="#333333",
        arrowprops=dict(arrowstyle="->", lw=0.7, color="#555555"),
    )
    ax.annotate(
        r"$\sigma = 1.0$ K (high noise)",
        xy=(sample_tvs[-1], sample_iaes[-1]),
        xytext=(-85, 20),
        textcoords="offset points",
        fontsize=7.2,
        color="#333333",
        arrowprops=dict(arrowstyle="->", lw=0.7, color="#555555"),
    )

    ax.set_xlabel(r"Actuator Total Variation $\mathrm{TV}$ (L/min) [Wear / Effort]", fontsize=8.5)
    ax.set_ylabel(r"Tracking Error $\mathrm{IAE}$ (K$\cdot$min)", fontsize=8.5)
    # Legend above the axes so no curve is covered
    h, lab = ax.get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=5.6,
               columnspacing=0.6, handlelength=2.2, markerscale=0.8)
    ax.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout(rect=[0.0, 0.0, 1.0, 0.855])
    fig_png = figures_dir / "fig_noise_sensitivity.png"
    fig_pdf = figures_dir / "fig_noise_sensitivity.pdf"
    plt.savefig(fig_png, dpi=300)
    plt.savefig(fig_pdf)
    plt.close()
    logger.info("Figuras salvas com sucesso em: %s e %s", fig_png, fig_pdf)


# %% [7. Ensaio 4: Rastreamento Não-Linear em Múltiplos Pontos de Operação]
def run_multistep_campaign(
    plant: CSTRPlant,
    ss: CSTRState,
    q_j_ss: float,
    controllers: dict[str, Callable[..., Any]],
    limits: ActuatorLimits,
    figures_dir: Path,
    tables_dir: Path,
) -> None:
    """Avalia o rastreamento em ampla faixa cobrindo regimes exotérmicos distintos.

    Cronograma didático de transição operacional:
    - 0 a 4 min: Ponto nominal estável (396.65 K).
    - 4 a 10 min: Degrau para 390.0 K (regime de menor taxa reacional).
    - 10 a 17 min: Degrau para 402.0 K (regime fortemente exotérmico, sensível a runaway térmico).
    - 17 a 24 min: Retorno ao ponto nominal estável (396.65 K).

    Args:
        plant: Modelo físico do CSTR.
        ss: Estado estacionário nominal.
        q_j_ss: Vazão base de resfriamento.
        controllers: Controladores PID avaliados.
        limits: Restrições físicas da válvula.
        figures_dir: Diretório de destino para figuras.
        tables_dir: Diretório de destino para tabelas.
    """
    logger.info("=== Executando Campanha de Rastreamento em Múltiplos Pontos de Operação ===")
    sim = ClosedLoopSimulator()
    t_span = (0.0, 24.0)
    dt = 0.02

    def multistep_profile(t: float) -> float:
        if t < 4.0:
            return ss.T
        elif t < 10.0:
            return 390.0
        elif t < 17.0:
            return 402.0
        else:
            return ss.T

    sim_results = {}
    table_rows = []

    for name, make in controllers.items():
        pid = make(sensor_noise_std=0.05, seed=42)
        res = sim.run(
            plant=plant,
            controller=pid,
            initial_state=ss,
            t_span=t_span,
            dt=dt,
            setpoint_func=multistep_profile,
            noise_std=0.05,
            seed=42,
        )
        sim_results[name] = res

        table_rows.append({
            "Method": name,
            "Total IAE": f"{res.metrics.iae:.2f}",
            "Total ITAE": f"{res.metrics.itae:.2f}",
            "Total TV (L/min)": f"{res.metrics.tv:.1f}",
            "Max Valve (L/min)": f"{np.max(res.u_applied):.1f}",
            "Min Valve (L/min)": f"{np.min(res.u_applied):.1f}",
        })

    export_latex_table(
        data=table_rows,
        output_path=tables_dir / "multistep_tracking_table.tex",
        caption="Multi-operating point tracking across moderate (390~K), nominal (396.65~K), "
        "and highly exothermic (402~K) reaction regimes.",
        label="tab:multistep_tracking",
    )

    # Geração dos gráficos IEEE em coluna única (3.5 in)
    setup_ieee_style(single_column=True)
    fig_w, fig_h = get_figure_dimensions(columns=1, height_override=4.2)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(fig_w, fig_h), sharex=True, dpi=300)

    sample_res = next(iter(sim_results.values()))
    ax1.plot(
        sample_res.t,
        sample_res.setpoint,
        color=IEEE_PALETTE["Setpoint"],
        linestyle=IEEE_LINESTYLES["Setpoint"],
        label=r"Target $T_{sp}$",
        linewidth=1.2,
    )

    for name, res in sim_results.items():
        color = IEEE_PALETTE.get(name, "#333333")
        linestyle = IEEE_LINESTYLES.get(name, "-")
        ax1.plot(res.t, res.t_pv, label=name, color=color, linestyle=linestyle, linewidth=1.2)
        ax2.plot(res.t, res.u_applied, label=name, color=color, linestyle=linestyle, linewidth=1.2)

    # Subplot 1: Temperatura do reator
    # Sem legenda interna: desobstrução completa de todos os patamares operacionais
    ax1.set_ylabel(r"Reactor Temp. $T$ (K)", fontsize=8.5)
    ax1.set_title("Wide-Range Multi-Operating Point Tracking", fontsize=9.0)
    ax1.grid(True, linestyle=":", alpha=0.6)

    # Subplot 2: Vazão de fluido refrigerante com limites físicos
    ax2.axhline(
        limits.u_max,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        label=r"Limits ($u_{\mathrm{min}}, u_{\mathrm{max}}$)",
        linewidth=1.0,
    )
    ax2.axhline(
        limits.u_min,
        color=IEEE_PALETTE["Constraint"],
        linestyle=IEEE_LINESTYLES["Constraint"],
        linewidth=1.0,
    )
    ax2.set_ylabel(r"Coolant Flow $q_j$ (L/min)", fontsize=8.5)
    ax2.set_xlabel(r"Time $t$ (min)", fontsize=8.5)
    ax2.set_ylim(-15, 345)
    ax2.grid(True, linestyle=":", alpha=0.6)

    # Construção da Legenda Unificada Superior (fig.legend) estilo Figura 3
    # Extrai manipuladores de ax1 (referência + 4 PIDs) e ax2 (limites de saturação)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    handles_unified = h1 + [h2[-1]]
    labels_unified = l1 + [l2[-1]]

    fig.legend(
        handles_unified,
        labels_unified,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=4,
        frameon=True,
        fontsize=5.6,
        framealpha=0.92,
        columnspacing=0.4,
        handletextpad=0.25,
    )

    plt.tight_layout(rect=[0.0, 0.0, 1.0, 0.885])
    fig_png = figures_dir / "fig5_multistep_tracking.png"
    fig_pdf = figures_dir / "fig5_multistep_tracking.pdf"
    plt.savefig(fig_png, dpi=300)
    plt.savefig(fig_pdf)
    plt.close()
    logger.info("Figuras salvas com sucesso em: %s e %s", fig_png, fig_pdf)


# %% [8. Ensaio 5: Sensibilidade Global de Sobol (SALib) sob Incerteza Conjunta]
SOBOL_CONTROLLERS = ("Ziegler-Nichols", "Tyreus-Luyben", "AMIGO", "Skogestad SIMC", OPT_ITAE_2DOF)
SOBOL_LABELS = {
    "E_over_R_scale": r"$E_a/R$",
    "UA_scale": r"$UA$",
    "C_Af": r"$C_{Af}$",
    "theta_sensor": r"$\theta_{\mathrm{sensor}}$",
}


def run_sobol_uncertainty_campaign(
    gains: dict[str, PIDGains],
    q_j_ss: float,
    limits: ActuatorLimits,
    figures_dir: Path,
    tables_dir: Path,
    n_base: int = 512,
) -> pd.DataFrame:
    """First/total-order Sobol indices of IAE and TV under (E_a/R, UA, C_Af, theta_sensor).

    Exports results/sobol_sensitivity_summary.csv (full precision), tables/sobol_sensitivity.tex
    and figures/fig_sobol_indices.pdf.
    """
    logger.info("=== Executando Análise de Sensibilidade Global de Sobol (SALib, N=%d) ===", n_base)
    factories = {name: pid_factory(gains[name], limits, q_j_ss) for name in SOBOL_CONTROLLERS}
    df = closed_loop_sobol(factories, n_base=n_base, seed=2026, q_j_ss=q_j_ss)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RESULTS_DIR / "sobol_sensitivity_summary.csv", index=False)

    wide = df.pivot_table(index=["controller", "parameter"], columns="metric", values=["S1", "ST"])
    rows = []
    for name in SOBOL_CONTROLLERS:
        for param in CSTR_UNCERTAINTY_PROBLEM["names"]:
            r = wide.loc[(name, param)]
            rows.append(
                {
                    "Controller": name,
                    "Parameter": SOBOL_LABELS[param],
                    "$S_1$ (IAE)": f"{r[('S1', 'IAE')]:.3f}",
                    "$S_T$ (IAE)": f"{r[('ST', 'IAE')]:.3f}",
                    "$S_1$ (TV)": f"{r[('S1', 'TV')]:.3f}",
                    "$S_T$ (TV)": f"{r[('ST', 'TV')]:.3f}",
                }
            )
    export_latex_table(
        data=rows,
        output_path=tables_dir / "sobol_sensitivity.tex",
        caption=(
            f"Global Sobol indices (Saltelli sampling, $N={n_base}$, "
            f"${n_base * 6}$ closed-loop runs per controller) of IAE and TV for a $-2$~K "
            "setpoint step under simultaneous uncertainty $E_a/R \\in [0.97, 1.03]$, "
            "$UA \\in [0.65, 1.05]\\,UA_{\\mathrm{nom}}$, $C_{Af} \\in [0.85, 1.15]$~mol/L "
            "and sensor dead time $\\theta_{\\mathrm{sensor}} \\in [0, 0.1]$~min."
        ),
        label="tab:sobol_sensitivity",
    )

    setup_ieee_style(single_column=False)
    fig_w, _ = get_figure_dimensions(columns=2)
    fig, axes = plt.subplots(1, 2, figsize=(fig_w, 2.6), sharey=True, dpi=300)
    params = CSTR_UNCERTAINTY_PROBLEM["names"]
    width = 0.8 / len(SOBOL_CONTROLLERS)
    x = np.arange(len(params))
    for ax, metric in zip(axes, ("IAE", "TV")):
        for k, name in enumerate(SOBOL_CONTROLLERS):
            st = [wide.loc[(name, prm)][("ST", metric)] for prm in params]
            s1 = [wide.loc[(name, prm)][("S1", metric)] for prm in params]
            pos = x - 0.4 + width * (k + 0.5)
            ax.bar(pos, st, width, color=IEEE_PALETTE[name], alpha=0.35, edgecolor=IEEE_PALETTE[name])
            ax.bar(pos, s1, width * 0.5, color=IEEE_PALETTE[name], label=name)
        ax.set_xticks(x, [SOBOL_LABELS[prm] for prm in params])
        ax.set_title(f"{metric}: $S_1$ (solid) and $S_T$ (shaded)")
        ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    axes[0].set_ylabel("Sobol index")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=len(SOBOL_CONTROLLERS), fontsize=7.0,
               bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.88])
    fig.savefig(figures_dir / "fig_sobol_indices.pdf")
    fig.savefig(figures_dir / "fig_sobol_indices.png", dpi=300)
    plt.close(fig)
    return df


# %% [9. Orquestrador Geral da Campanha]
def run_campaign() -> None:
    """Orquestra a execução sequencial de todas as campanhas de robustez do Artigo 1."""
    figures_dir = OVERLEAF_DIR / "figures"
    tables_dir = OVERLEAF_DIR / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    plant = CSTRPlant()
    q_j_ss = 100.0
    ss = plant.find_steady_state(q_j=q_j_ss)
    limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)

    gains, _ = setup_controllers(plant, ss, q_j_ss)
    controllers = make_factories(gains, q_j_ss, limits, dt=0.02, y_ss=ss.T)

    logger.info("Iniciando campanha experimental abrangente de robustez...")
    run_load_disturbance_campaign(plant, ss, q_j_ss, controllers, limits, figures_dir, tables_dir)
    run_fouling_campaign(plant, ss, q_j_ss, controllers, limits, figures_dir, tables_dir)
    run_noise_and_pareto_campaign(plant, ss, q_j_ss, controllers, limits, figures_dir, tables_dir)
    run_multistep_campaign(plant, ss, q_j_ss, controllers, limits, figures_dir, tables_dir)
    run_sobol_uncertainty_campaign(gains, q_j_ss, limits, figures_dir, tables_dir)
    logger.info("Campanha de robustez concluída com êxito!")


# %% [10. Ponto de Entrada Principal]
if __name__ == "__main__":
    run_campaign()
