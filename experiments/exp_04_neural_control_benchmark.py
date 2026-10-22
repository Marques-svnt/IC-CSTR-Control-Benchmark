# -*- coding: utf-8 -*-
"""Benchmark de controle neural adaptativo e oráculo ótimo no reator CSTR.

Experimento preparatório para o Artigo 2 e Fase 4 do PROIC:
Avalia o comportamento de rastreamento sob condições não-lineares severas:
- Degrau de setpoint amplo: Delta T = -5.0 K (344.16 -> 339.16 K)
- Distúrbio exotérmico de carga: aumento de +20% em C_Af (1.0 -> 1.2 mol/L) em t = 4 min
- Distúrbio térmico de alimentação: aumento de +5 K em T_f (350 -> 355 K) em t = 7 min

Compara:
1. Skogestad SIMC (Linha de base industrial suave)
2. Nelder-Mead ITAE (Ms <= 1.6)
3. Neuro-PID Adaptativo (Rede neural PyTorch ajustando Kp, Ti, Td dinamicamente)
4. NMPC Oracle (Limite Teórico Ótimo em CasADi/do-mpc)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import pandas as pd

from src.classical_control.closed_loop import ClosedLoopSimulator
from src.classical_control.foptd import identify_foptd
from src.classical_control.pid_controller import AntiWindupMethod, PIDController
from src.classical_control.tuning_analytical import TuningRule, tune_analytical
from src.classical_control.tuning_optimization import (
    OptimizationCriterion,
    tune_by_optimization,
)
from src.controllers.neural.neuro_pid_controller import NeuroPidController
from src.controllers.optimal.nmpc_controller import CstrNmpcController
from src.evaluation.plot_styles import get_figure_dimensions, setup_ieee_style
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRPlant
from src.sim_core.integrator import NumericalIntegrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("exp_04_neural")


def run_neural_control_benchmark() -> pd.DataFrame:
    """Executa o benchmark comparativo multivariável e gera visualizações."""
    plant = CSTRPlant()
    integrator = NumericalIntegrator(method="RK45")
    q_j_ss = 100.0
    ss = plant.find_steady_state(q_j=q_j_ss)

    logger.info("Estado nominal: T=%.2f K, C_A=%.4f mol/L, T_j=%.2f K", ss.T, ss.C_A, ss.T_j)

    # Identificação FOPTD
    id_res = integrator.simulate_open_loop(
        plant=plant,
        initial_state=ss,
        t_span=(0.0, 6.0),
        dt=0.02,
        u_func=lambda t: q_j_ss + 10.0,
    )
    foptd, _ = identify_foptd(
        t=id_res.t,
        y=id_res.states[:, 1],
        delta_u=10.0,
        y0=ss.T,
    )

    gains_simc = tune_analytical(foptd, rule=TuningRule.SKOGESTAD_SIMC_PID, tau_c=0.4)
    gains_opt = tune_by_optimization(
        plant=plant,
        nominal_state=ss,
        q_j_ss=q_j_ss,
        criterion=OptimizationCriterion.ITAE,
        max_ms=1.6,
        foptd=foptd,
    )

    sim = ClosedLoopSimulator(integrator=integrator)
    t_sim_span = (0.0, 10.0)
    dt = 0.02
    target_T = ss.T - 5.0  # Degrau severo de -5.0 K
    limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)

    # Perfil de distúrbios compostos
    def disturbance_profile(t: float) -> dict[str, float]:
        dist: dict[str, float] = {}
        if t >= 4.0:
            dist["C_Af"] = 1.20  # +20% concentração reagente (gera mais calor)
        if t >= 7.0:
            dist["T_f"] = 355.0  # +5 K temperatura de alimentação
        return dist

    controllers = {
        "Skogestad SIMC": PIDController(
            gains=gains_simc,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        ),
        "Optimal ITAE ($M_s \\leq 1.6$)": PIDController(
            gains=gains_opt,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        ),
        "Adaptive Neuro-PID": NeuroPidController(
            base_gains=gains_opt,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
            adaptation_scale=0.30,
        ),
        "NMPC Oracle (Optimal Bound)": CstrNmpcController(
            horizon_steps=12,
            t_step_min=dt,
            setpoint_temperature_k=target_T,
            u_bias=q_j_ss,
        ),
    }

    sim_results = {}
    table_rows = []

    for name, ctrl in controllers.items():
        logger.info("Simulando: %s", name)
        res = sim.run(
            plant=plant,
            controller=ctrl,
            initial_state=ss,
            t_span=t_sim_span,
            dt=dt,
            setpoint_func=lambda t: target_T,
            disturbance_func=disturbance_profile,
            noise_std=0.0,
            seed=42,
        )
        sim_results[name] = res
        table_rows.append({
            "Controller": name,
            "IAE": f"{res.metrics.iae:.2f}",
            "ITAE": f"{res.metrics.itae:.2f}",
            "ISE": f"{res.metrics.ise:.2f}",
            "TV (L/min)": f"{res.metrics.tv:.1f}",
            "Overshoot (%)": f"{res.metrics.overshoot_pct:.1f}",
            "Settling (min)": (
                f"{res.metrics.settling_time:.2f}"
                if res.metrics.settling_time is not None
                else "N/A"
            ),
        })

    df = pd.DataFrame(table_rows)

    # Plotagem
    setup_ieee_style(single_column=True)
    fig_w, fig_h = get_figure_dimensions(columns=1, height_override=5.0)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(fig_w, fig_h), sharex=True, dpi=300)

    palette = {
        "Skogestad SIMC": ("#1f77b4", "--"),
        "Optimal ITAE ($M_s \\leq 1.6$)": ("#2ca02c", "-."),
        "Adaptive Neuro-PID": ("#ff7f0e", "-"),
        "NMPC Oracle (Optimal Bound)": ("#9467bd", "-"),
    }

    ax1.axhline(target_T, color="black", linestyle=":", linewidth=1.0, label="Setpoint (339.16 K)")
    ax1.axvline(4.0, color="gray", linestyle=":", alpha=0.7)
    ax1.axvline(7.0, color="gray", linestyle=":", alpha=0.7)
    ax1.text(4.1, 343.5, r"$\Delta C_{Af}=+20\%$", fontsize=7, color="gray")
    ax1.text(7.1, 343.5, r"$\Delta T_f=+5\text{K}$", fontsize=7, color="gray")

    for name, res in sim_results.items():
        color, ls = palette.get(name, ("#333333", "-"))
        lw = 1.6 if "Neuro" in name or "NMPC" in name else 1.1
        ax1.plot(res.t, res.t_pv, label=name, color=color, linestyle=ls, linewidth=lw)
        ax2.plot(res.t, res.u_applied, label=name, color=color, linestyle=ls, linewidth=lw)

    ax1.set_ylabel("Reactor Temp. $T$ (K)")
    ax1.set_xlim(0.0, 10.0)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", fontsize=6.5, framealpha=0.9)

    ax2.set_xlabel("Time $t$ (min)")
    ax2.set_ylabel("Cooling Flow $q_j$ (L/min)")
    ax2.set_xlim(0.0, 10.0)
    ax2.grid(True, linestyle=":", alpha=0.6)

    fig.tight_layout()
    plot_file = PROJECT_ROOT / "experiments" / "fig_exp_04_neural_benchmark.png"
    fig.savefig(plot_file, dpi=300)
    plt.close(fig)
    logger.info("Gráfico salvo em: %s", plot_file)

    csv_file = PROJECT_ROOT / "experiments" / "results_exp_04_neural_benchmark.csv"
    df.to_csv(csv_file, index=False)
    logger.info("Resultados CSV salvos em: %s", csv_file)

    return df


if __name__ == "__main__":
    results = run_neural_control_benchmark()
    print("\n--- RESULTADOS DO BENCHMARK NEURAL (ARTIGO 2 / FASE 4) ---")
    print(results.to_string(index=False))
