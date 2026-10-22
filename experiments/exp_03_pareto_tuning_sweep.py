# -*- coding: utf-8 -*-
"""Exploração contínua da fronteira de Pareto no CSTR não-linear via varredura paramétrica.

Gera o trade-off autêntico de Pareto entre acurácia de rastreamento de setpoint (IAE)
e esforço/desgaste físico do atuador (TV) através de:
1. Varredura contínua da constante de tempo em malha fechada tau_c do SIMC em [0.015, 2.5] min.
2. Otimização multi-objetivo escalarizada através do peso de ponderação lambda em [0.05, 0.95].
3. Avaliação da sensibilidade máxima de pico Ms para delinear fronteiras de robustez (Ms <= 1.6).
4. Mapeamento das sintonias clássicas discretas (ZN, CC, SIMC, ITAE-opt) no espaço de projeto.

Atende estritamente às diretrizes de publicação IEEE Transactions (300 DPI, fontes Type 42).
"""

# %% [1. Importações e Configuração de Caminhos]
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Adiciona a raiz do projeto ao sys.path para garantir importações relativas e absolutas
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

from experiments.exp_02_robustness_campaign import (
    OVERLEAF_DIR,
    export_latex_table,
    setup_controllers,
)
from src.classical_control.closed_loop import ClosedLoopSimulator
from src.classical_control.foptd import FOPTDModel, identify_foptd
from src.classical_control.pid_controller import AntiWindupMethod, PIDController, PIDGains
from src.classical_control.tuning_analytical import TuningRule, tune_analytical
from src.classical_control.tuning_optimization import (
    calculate_maximum_sensitivity,
)
from src.evaluation.plot_styles import (
    IEEE_MARKERS,
    IEEE_PALETTE,
    get_figure_dimensions,
    setup_ieee_style,
)
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRPlant, CSTRState
from src.sim_core.integrator import NumericalIntegrator

# Configuração de logging informativo
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("exp_03_pareto")


# %% [3. Varredura Paramétrica Contínua de tau_c no Skogestad SIMC]
def run_simc_sweep(
    plant: CSTRPlant,
    ss: CSTRState,
    q_j_ss: float,
    foptd: FOPTDModel,
    limits: ActuatorLimits,
    tau_c_values: np.ndarray,
) -> List[Dict[str, Any]]:
    """Varia continuamente a constante de tempo de malha fechada tau_c do método SIMC.

    Passo a passo didático:
    1. Para cada tau_c no intervalo [0.015, 2.5] min, calcula os ganhos analíticos do SIMC.
    2. Avalia a sensibilidade máxima de pico Ms no domínio da frequência.
    3. Simula a resposta ao degrau de setpoint no modelo não-linear do CSTR.
    4. Computa as métricas IAE (erro de rastreamento) e TV (variação total do atuador).

    Args:
        plant: Modelo físico do CSTR.
        ss: Estado estacionário nominal.
        q_j_ss: Vazão base de fluido refrigerante [L/min].
        foptd: Modelo FOPTD identificado.
        limits: Restrições físicas da válvula.
        tau_c_values: Vetor com os valores discretos de tau_c [min].

    Returns:
        Lista de dicionários com os resultados de sintonia e desempenho.
    """
    logger.info(
        "Executando varredura paramétrica do Skogestad SIMC com %d pontos...", len(tau_c_values)
    )
    sim = ClosedLoopSimulator()
    results = []

    for tc in tau_c_values:
        gains = tune_analytical(foptd, TuningRule.SKOGESTAD_SIMC_PID, tau_c=float(tc))
        ms = calculate_maximum_sensitivity(foptd=foptd, gains=gains)

        pid = PIDController(
            gains=gains,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        )

        try:
            res = sim.run(
                plant=plant,
                controller=pid,
                initial_state=ss,
                t_span=(0.0, 10.0),
                dt=0.02,
                setpoint_func=lambda t: ss.T - 2.0,
            )
            iae = res.metrics.iae
            itae = res.metrics.itae
            tv = res.metrics.tv
            overshoot = res.metrics.overshoot_pct
            ts = res.metrics.settling_time if res.metrics.settling_time is not None else 10.0
        except Exception as e:
            logger.warning("Falha na simulação para tau_c=%.3f: %s", tc, e)
            continue

        results.append({
            "tau_c": float(tc),
            "kp": gains.kp,
            "ti": gains.ti,
            "td": gains.td,
            "ms": ms,
            "iae": iae,
            "itae": itae,
            "tv": tv,
            "overshoot": overshoot,
            "settling_time": ts,
        })

    return results


# %% [4. Otimização Multi-Objetivo Escalarizada (Fronteira Teórica de Pareto)]
def run_scalarized_multiobjective_sweep(
    plant: CSTRPlant,
    ss: CSTRState,
    q_j_ss: float,
    foptd: FOPTDModel,
    limits: ActuatorLimits,
    lambdas: np.ndarray,
    ref_iae: float,
    ref_tv: float,
) -> List[Dict[str, Any]]:
    """Resolve o problema multi-objetivo: min lambda*(IAE/IAE0) + (1-lambda)*(TV/TV0).

    Passo a passo didático:
    1. Normaliza IAE e TV pelos valores de referência nominal do SIMC (IAE0, TV0).
    2. Varia o peso lambda entre 0.05 (prioriza desgaste do atuador) e 0.95 (prioriza erro nulo).
    3. Aplica penalidade quadrática se a sensibilidade máxima Ms ultrapassar o limite 2.0.
    4. Aplica algoritmo Nelder-Mead com partida a quente (warm-start) sequencial.

    Args:
        plant: Modelo físico do CSTR.
        ss: Estado estacionário nominal.
        q_j_ss: Vazão base de resfriamento.
        foptd: Modelo FOPTD identificado.
        limits: Restrições físicas da válvula.
        lambdas: Vetor de pesos de ponderação no intervalo (0, 1).
        ref_iae: Valor de normalização para IAE.
        ref_tv: Valor de normalização para TV.

    Returns:
        Lista de resultados sintonizados na fronteira ótima de Pareto.
    """
    logger.info(
        "Executando otimização multi-objetivo escalarizada com %d pesos lambda...",
        len(lambdas),
    )
    sim = ClosedLoopSimulator()
    results = []

    # Estimativa inicial moderada para o algoritmo simplex Nelder-Mead
    x0 = np.array([-4.5, 1.2, 0.15], dtype=np.float64)

    for lam in lambdas:
        def objective(params: np.ndarray) -> float:
            kp, ti, td = float(params[0]), float(params[1]), float(params[2])
            if kp >= 0.0 or ti <= 0.05 or td < 0.0:
                return 1e6

            candidate = PIDGains(kp=kp, ti=ti, td=td)
            ms = calculate_maximum_sensitivity(foptd=foptd, gains=candidate)
            # Penalidade estrita para violação do limite superior de robustez Ms <= 2.0
            ms_pen = 1e3 * (ms - 2.0) ** 2 if ms > 2.0 else 0.0

            pid = PIDController(
                gains=candidate,
                actuator_limits=limits,
                anti_windup=AntiWindupMethod.CLAMPING,
                u_bias=q_j_ss,
            )

            try:
                res = sim.run(
                    plant=plant,
                    controller=pid,
                    initial_state=ss,
                    t_span=(0.0, 8.0),
                    dt=0.02,
                    setpoint_func=lambda t: ss.T - 2.0,
                )
            except Exception:
                return 1e6

            norm_iae = res.metrics.iae / ref_iae
            norm_tv = res.metrics.tv / ref_tv
            final_err = abs(res.t_pv[-1] - (ss.T - 2.0))
            offset_pen = 1e3 * final_err if final_err > 0.3 else 0.0

            cost = float(lam * norm_iae + (1.0 - lam) * norm_tv + ms_pen + offset_pen)
            return cost

        opt = minimize(
            fun=objective,
            x0=x0,
            method="Nelder-Mead",
            options={"maxiter": 80, "xatol": 1e-2, "fatol": 1e-2, "disp": False},
        )

        opt_gains = PIDGains(kp=float(opt.x[0]), ti=float(opt.x[1]), td=float(opt.x[2]))
        ms_opt = calculate_maximum_sensitivity(foptd=foptd, gains=opt_gains)

        pid_opt = PIDController(
            gains=opt_gains,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        )
        res_opt = sim.run(
            plant=plant,
            controller=pid_opt,
            initial_state=ss,
            t_span=(0.0, 10.0),
            dt=0.02,
            setpoint_func=lambda t: ss.T - 2.0,
        )

        results.append({
            "lambda": float(lam),
            "kp": opt_gains.kp,
            "ti": opt_gains.ti,
            "td": opt_gains.td,
            "ms": ms_opt,
            "iae": res_opt.metrics.iae,
            "itae": res_opt.metrics.itae,
            "tv": res_opt.metrics.tv,
            "overshoot": res_opt.metrics.overshoot_pct,
            "settling_time": res_opt.metrics.settling_time or 10.0,
        })
        # Partida a quente para aceleração da convergência no próximo peso
        x0 = np.array([opt_gains.kp, opt_gains.ti, opt_gains.td], dtype=np.float64)

    return results


# %% [5. Avaliação dos Pontos Discretos de Benchmark]
def run_benchmark_points(
    plant: CSTRPlant,
    ss: CSTRState,
    q_j_ss: float,
    foptd: FOPTDModel,
    limits: ActuatorLimits,
    gains_dict: Dict[str, PIDGains],
) -> Dict[str, Dict[str, Any]]:
    """Avalia os métodos clássicos discretos como pontos de ancoragem na fronteira."""
    sim = ClosedLoopSimulator()
    discrete_points = {}
    for name, gains in gains_dict.items():
        ms = calculate_maximum_sensitivity(foptd=foptd, gains=gains)
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
            dt=0.02,
            setpoint_func=lambda t: ss.T - 2.0,
        )
        discrete_points[name] = {
            "gains": gains,
            "ms": ms,
            "iae": res.metrics.iae,
            "itae": res.metrics.itae,
            "tv": res.metrics.tv,
            "overshoot": res.metrics.overshoot_pct,
        }
    return discrete_points


# %% [6. Geração da Figura de Publicação no Padrão IEEE (Coluna Dupla)]
def plot_true_pareto_frontier(
    simc_results: List[Dict[str, Any]],
    opt_results: List[Dict[str, Any]],
    discrete_points: Dict[str, Dict[str, Any]],
    figures_dir: Path,
) -> None:
    """Renderiza a figura de publicação da fronteira de Pareto com formatação editorial IEEE."""
    setup_ieee_style(single_column=False)
    fig_w, fig_h = get_figure_dimensions(columns=2, height_override=4.6)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fig_w, fig_h), dpi=300)

    # ----------------------------------------------------
    # Painel (a): Fronteira de Pareto no Plano (TV, IAE)
    # ----------------------------------------------------
    simc_tv = [r["tv"] for r in simc_results]
    simc_iae = [r["iae"] for r in simc_results]
    simc_ms = np.array([r["ms"] for r in simc_results])

    # Traçado contínuo do locus SIMC com mapa de cores codificado por Ms
    scatter = ax1.scatter(
        simc_tv,
        simc_iae,
        c=simc_ms,
        cmap="viridis_r",
        vmin=1.1,
        vmax=2.5,
        s=28,
        zorder=3,
        edgecolor="none",
        label=r"SIMC $\tau_c$-sweep locus",
    )
    ax1.plot(simc_tv, simc_iae, color="#555555", linestyle="-", linewidth=1.0, alpha=0.7)

    # Fronteira multi-objetivo escalarizada
    opt_tv = [r["tv"] for r in opt_results]
    opt_iae = [r["iae"] for r in opt_results]
    sorted_opt = sorted(zip(opt_tv, opt_iae), key=lambda x: x[0])
    ax1.plot(
        [x[0] for x in sorted_opt],
        [x[1] for x in sorted_opt],
        color="#1B7837",
        linestyle="--",
        linewidth=1.4,
        label=r"Pareto optimal front ($\lambda$-opt)",
    )

    # Discrete tuning rules are identified by marker in the legend; far-off points go to an inset
    front_tv = np.array(simc_tv + opt_tv)
    front_iae = np.array(simc_iae + opt_iae)
    # Zoom on the efficient region: points far outside it are listed in an inset instead
    y_max = 2.5 * float(np.min(front_iae))
    in_view = [pt["tv"] for pt in discrete_points.values() if pt["iae"] <= y_max]
    x_max = 1.3 * max(float(np.max(front_tv)), max(in_view, default=0.0))
    off_scale = []  # discrete points are identified by marker in the legend only
    for name, pt in discrete_points.items():
        if pt["tv"] <= x_max and pt["iae"] <= y_max:
            ax1.scatter([pt["tv"]], [pt["iae"]], color=IEEE_PALETTE[name], marker=IEEE_MARKERS[name],
                        s=48, edgecolors="black", linewidth=0.7, zorder=5,
                        label=f"{name.split(' (')[0]} ($M_s = {pt['ms']:.2f}$)")
        else:
            off_scale.append(
                f"{name}: TV$={pt['tv']:.0f}$, IAE$={pt['iae']:.1f}$ ($M_s={pt['ms']:.2f}$)"
            )
    if off_scale:
        ax1.text(0.98, 0.98, "Off-scale:\n" + "\n".join(off_scale), transform=ax1.transAxes,
                 ha="right", va="top", fontsize=5.8,
                 bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "#999999"})
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=6.0,
               framealpha=0.95, labelspacing=0.25)
    ax1.set_xscale("log")  # front lives at TV 10-45 L/min, high-gain tail reaches ~450
    ax1.set_xlim(0.8 * float(np.min(front_tv)), x_max)
    ax1.xaxis.set_major_formatter(plt.ScalarFormatter())
    ax1.xaxis.set_minor_formatter(plt.NullFormatter())
    ax1.set_ylim(0.5, y_max)
    ax1.set_xlabel(r"Actuator Total Variation $\mathrm{TV}$ (L/min) [Wear / Effort]", fontsize=8.8)
    ax1.set_ylabel(r"Tracking Error $\mathrm{IAE}$ (K$\cdot$min)", fontsize=8.8)
    ax1.set_title(r"(a) True Pareto Trade-off: $\mathrm{IAE}$ vs $\mathrm{TV}$", fontsize=9.3)
    ax1.grid(True, linestyle=":", alpha=0.6)

    # Barra de cores para sensibilidade máxima Ms
    cbar = plt.colorbar(scatter, ax=ax1, pad=0.02, aspect=20)
    cbar.set_label(r"Maximum Sensitivity $M_s = \|S\|_\infty$", fontsize=8.5)
    cbar.ax.tick_params(labelsize=7.5)

    # ----------------------------------------------------
    # Painel (b): Parâmetro tau_c vs Robustez (Ms) e IAE
    # ----------------------------------------------------
    tau_cs = [r["tau_c"] for r in simc_results]
    ms_vals = [r["ms"] for r in simc_results]
    iae_vals = [r["iae"] for r in simc_results]

    color_ms = "#1F78B4"
    color_iae = "#E31A1C"

    ax2.plot(
        tau_cs,
        ms_vals,
        color=color_ms,
        linestyle="-",
        linewidth=1.6,
        label=r"Sensitivity Peak $M_s$",
    )
    ax2.axhline(
        1.6, color="#33A02C", linestyle="--", linewidth=1.2, label=r"Robust Target ($M_s = 1.6$)"
    )
    ax2.axhline(
        2.0, color="#E31A1C", linestyle=":", linewidth=1.2, label=r"Marginal Limit ($M_s = 2.0$)"
    )

    ax2.set_xscale("log")
    ax2.set_xlabel(r"Closed-loop Tuning Parameter $\tau_c$ (min) [Log Scale]", fontsize=8.8)
    ax2.set_ylabel(r"Maximum Sensitivity Peak $M_s$", color=color_ms, fontsize=8.8)
    ax2.tick_params(axis="y", labelcolor=color_ms, labelsize=8.0)
    ax2.set_ylim(0.90, 3.8)
    ax2.grid(True, linestyle=":", alpha=0.6)

    # Eixo secundário (twinx) para erro de rastreamento IAE
    ax2_twin = ax2.twinx()
    ax2_twin.plot(
        tau_cs,
        iae_vals,
        color=color_iae,
        linestyle="-.",
        linewidth=1.6,
        label=r"Tracking Error $IAE$",
    )
    ax2_twin.set_ylabel(r"Tracking Error $IAE$ (K$\cdot$min)", color=color_iae, fontsize=8.8)
    ax2_twin.tick_params(axis="y", labelcolor=color_iae, labelsize=8.0)
    ax2_twin.set_ylim(0.8, 6.4)

    lines_1, labels_1 = ax2.get_legend_handles_labels()
    lines_2, labels_2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        loc="upper center",
        bbox_to_anchor=(0.50, 0.98),
        fontsize=6.5,
        framealpha=0.95,
        frameon=True,
        edgecolor="#CCCCCC",
        labelspacing=0.28,
    )
    ax2.set_title(r"(b) Robustness ($M_s$) and Performance ($IAE$) vs $\tau_c$", fontsize=9.3)

    plt.tight_layout()

    fig_png = figures_dir / "fig4_pareto_iae_tv.png"
    fig_pdf = figures_dir / "fig4_pareto_iae_tv.pdf"
    plt.savefig(fig_png, dpi=300)
    plt.savefig(fig_pdf)
    plt.close()
    logger.info("Figuras da fronteira de Pareto salvas com sucesso em: %s e %s", fig_png, fig_pdf)


# %% [7. Ensaio Principal e Geração de Artefatos]
def run_experiment() -> None:
    """Executa a campanha completa de exploração de Pareto e gera figuras e tabelas."""
    figures_dir = OVERLEAF_DIR / "figures"
    tables_dir = OVERLEAF_DIR / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    plant = CSTRPlant()
    integrator = NumericalIntegrator(method="RK45")
    q_j_ss = 100.0
    ss = plant.find_steady_state(q_j=q_j_ss)
    limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)

    # 1. Identificação do Modelo
    logger.info("Identificando função de transferência FOPTD nominal...")
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
    logger.info(
        "FOPTD: K=%.4f, tau=%.4f min, theta=%.4f min (RMSE=%.4f K)",
        foptd.k_p,
        foptd.tau,
        foptd.theta,
        rmse,
    )

    cache_file = PROJECT_ROOT / "experiments" / ".exp_03_cache.pkl"
    if cache_file.exists():
        logger.info("Carregando resultados da otimização de Pareto do cache local: %s", cache_file)
        import pickle
        with open(cache_file, "rb") as f:
            simc_results, opt_results, discrete_points = pickle.load(f)
    else:
        # 2. Varredura Paramétrica do Skogestad SIMC
        tau_c_vals = np.logspace(np.log10(0.015), np.log10(2.5), 45)
        simc_results = run_simc_sweep(plant, ss, q_j_ss, foptd, limits, tau_c_vals)

        # 3. Pontos de Referência dos Métodos Discretos
        gains_dict, _ = setup_controllers(plant, ss, q_j_ss)
        discrete_points = run_benchmark_points(plant, ss, q_j_ss, foptd, limits, gains_dict)

        # Valores de referência para normalização da otimização multi-objetivo
        ref_iae = discrete_points["Skogestad SIMC"]["iae"]
        ref_tv = discrete_points["Skogestad SIMC"]["tv"]

        # 4. Varredura de Otimização Multi-Objetivo Escalarizada
        lambdas = np.linspace(0.05, 0.95, 10)
        opt_results = run_scalarized_multiobjective_sweep(
            plant=plant,
            ss=ss,
            q_j_ss=q_j_ss,
            foptd=foptd,
            limits=limits,
            lambdas=lambdas,
            ref_iae=ref_iae,
            ref_tv=ref_tv,
        )
        import pickle
        with open(cache_file, "wb") as f:
            pickle.dump((simc_results, opt_results, discrete_points), f)
        logger.info("Resultados de Pareto salvos em cache: %s", cache_file)

    # 5. Geração da Figura de Publicação
    plot_true_pareto_frontier(simc_results, opt_results, discrete_points, figures_dir)

    # 6. Geração da Tabela Resumo em LaTeX
    table_rows = []
    target_tcs = [0.03, 0.10, 0.25, 0.40, 0.80, 1.50]
    for target in target_tcs:
        closest = min(simc_results, key=lambda r: abs(r["tau_c"] - target))
        table_rows.append({
            "Strategy": f"SIMC ($\\tau_c={closest['tau_c']:.2f}$)",
            "$K_{p}$": f"{closest['kp']:.2f}",
            "$T_{i}$ (min)": f"{closest['ti']:.2f}",
            "$T_{d}$ (min)": f"{closest['td']:.2f}",
            "$M_{s}$": f"{closest['ms']:.2f}",
            "IAE (K$\\cdot$min)": f"{closest['iae']:.2f}",
            "TV (L/min)": f"{closest['tv']:.1f}",
            "$M_{p}$ (\\%)": f"{closest['overshoot']:.1f}",
        })

    for name, pt in discrete_points.items():
        table_rows.append({
            "Strategy": name,
            "$K_{p}$": f"{pt['gains'].kp:.2f}",
            "$T_{i}$ (min)": f"{pt['gains'].ti:.2f}",
            "$T_{d}$ (min)": f"{pt['gains'].td:.2f}",
            "$M_{s}$": f"{pt['ms']:.2f}",
            "IAE (K$\\cdot$min)": f"{pt['iae']:.2f}",
            "TV (L/min)": f"{pt['tv']:.1f}",
            "$M_{p}$ (\\%)": f"{pt['overshoot']:.1f}",
        })

    export_latex_table(
        data=table_rows,
        output_path=tables_dir / "pareto_tradeoff_table.tex",
        caption=(
            "Quantitative trade-off along the continuous Pareto frontier: "
            "impact of closed-loop tuning parameter $\\tau_c$ and classical rules "
            "on robustness ($M_s$) and actuator effort ($TV$)."
        ),
        label="tab:pareto_tradeoff",
    )

    from src.evaluation.pareto import (
        ParetoPoint,
        compute_hypervolume_pymoo,
        optimize_pid_nsga3_pymoo,
    )

    nsga3_front = optimize_pid_nsga3_pymoo(foptd, n_generations=6, pop_size=12, ms_threshold=1.6)
    simc_pareto_pts = [
        ParetoPoint(iae=r["iae"], tv=r["tv"], ms=r["ms"], label=f"tau_c={r['tau_c']:.2f}")
        for r in simc_results
        if r["ms"] <= 1.6
    ]
    hv_simc = compute_hypervolume_pymoo(simc_pareto_pts)
    hv_nsga3 = compute_hypervolume_pymoo(nsga3_front)
    logger.info("Hipervolume 3D (pymoo): SIMC=%.2f | NSGA-III=%.2f", hv_simc, hv_nsga3)


# %% [8. Ponto de Entrada Principal]
if __name__ == "__main__":
    run_experiment()
