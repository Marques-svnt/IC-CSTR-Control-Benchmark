# -*- coding: utf-8 -*-
"""Script de benchmark comparativo entre controle SISO direto e controle em Cascata.

Compara o desempenho do controle clássico SISO (Skogestad SIMC e ITAE Ótimo)
frente à arquitetura em cascata industrial (T -> T_j -> q_j) sob três cenários:
1. Rastreamento nominal de setpoint (-2.0 K);
2. Rejeição de perturbação térmica na utilidade de resfriamento (+10.0 K em T_jf);
3. Limite de controlabilidade termodinâmica sob incrustação (fouling) da jaqueta.

Gera:
- Tabela LaTeX formatada com booktabs: tables/cascade_comparison_table.tex
- Figura de publicação vetorial (PDF) e bitmap 300 DPI: figures/fig6_cascade_comparison.pdf
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict

# Adiciona a raiz do projeto ao sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import numpy as np

from src.classical_control.cascade_controller import CascadePIDController, CascadePIDGains
from src.classical_control.foptd import FOPTDModel
from src.classical_control.pid_controller import PIDController
from src.classical_control.tuning_analytical import TuningRule, tune_analytical
from src.evaluation.plot_styles import (
    IEEE_DOUBLE_COL_WIDTH_INCHES,
    setup_ieee_style,
)
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRParameters, CSTRPlant

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("exp_05_cascade")


def run_cascade_benchmark() -> None:
    """Executa os ensaios comparativos de cascata vs malha simples e exporta resultados."""
    paper_dir = PROJECT_ROOT / "Artigos_Rascunhos" / "Artigo_01_Classic_Methods" / "overleaf"
    figures_dir = paper_dir / "figures"
    tables_dir = paper_dir / "tables"
    figures_novas_dir = figures_dir
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_novas_dir.mkdir(parents=True, exist_ok=True)

    plant = CSTRPlant()
    q_j_ss = 100.0
    ss = plant.find_steady_state(q_j=q_j_ss)

    # Limites físicos da válvula de controle
    limits = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=80.0)

    # Sintonias
    from experiments.exp_02_robustness_campaign import export_latex_table, identify_nominal_foptd

    foptd = identify_nominal_foptd(plant, ss, q_j_ss)
    simc_gains = tune_analytical(foptd, TuningRule.SKOGESTAD_SIMC_PID, tau_c=0.40)

    # Sequential SIMC. Inner loop q_j -> T_j from the linearized jacket balance:
    # dT_j/dt = A[2,2] T_j + B[2] q_j + ...  ->  tau_2 = -1/A[2,2], K_2 = -B[2]/A[2,2],
    # with one sampling interval as effective delay.
    A, B = plant.linearize(ss, q_j_ss)
    dt_ctrl = 0.02
    slave_model = FOPTDModel(
        k_p=float(-B[2, 0] / A[2, 2]), tau=float(-1.0 / A[2, 2]), theta=dt_ctrl
    )
    tau_c2 = slave_model.tau  # inner closed loop as fast as the open-loop jacket
    slave_gains = tune_analytical(slave_model, TuningRule.SKOGESTAD_SIMC_PI, tau_c=tau_c2)
    # Outer loop T_j,sp -> T sees the closed inner loop as an extra delay tau_c2 + theta_2
    master_model = FOPTDModel(
        k_p=foptd.k_p / slave_model.k_p, tau=foptd.tau, theta=tau_c2 + slave_model.theta
    )
    master_gains = tune_analytical(master_model, TuningRule.SKOGESTAD_SIMC_PID, tau_c=0.40)
    logger.info("Cascade SIMC: slave %s | master %s", slave_gains, master_gains)
    cascade_gains = CascadePIDGains(
        master_gains=master_gains,
        slave_gains=slave_gains,
        t_j_min=300.0,
        t_j_max=380.0,
    )

    dt = 0.02
    t_span = np.arange(0.0, 10.0 + 1e-6, dt)

    # =========================================================================
    # CENÁRIO 1: Distúrbio na Utilidade de Resfriamento (T_jf: 300 -> 310 K em t = 2.0 min)
    # =========================================================================
    logger.info("Executando Cenário 1: Perturbação na utilidade de resfriamento (+10 K)...")
    res_dist: Dict[str, Dict[str, Any]] = {}

    for ctrl_name in ["SIMC (SISO)", "Cascade (Master-Slave)"]:
        state = ss
        if ctrl_name == "SIMC (SISO)":
            ctrl = PIDController(gains=simc_gains, actuator_limits=limits, u_bias=q_j_ss)
            ctrl.reset(initial_measurement=ss.T, initial_u=q_j_ss)
        else:
            ctrl = CascadePIDController(
                gains=cascade_gains, actuator_limits=limits, u_bias=q_j_ss, t_j_bias=ss.T_j
            )
            ctrl.reset(initial_t=ss.T, initial_tj=ss.T_j, initial_u=q_j_ss)

        t_hist, tj_hist, qj_hist, tj_sp_hist = [], [], [], []

        for t in t_span:
            # Distúrbio na temperatura da água de resfriamento em t >= 2.0 min
            tjf_curr = 310.0 if t >= 2.0 else 300.0
            p_inst = CSTRPlant(params=CSTRParameters(T_jf=tjf_curr))

            t_sp = ss.T  # Regulação em setpoint constante
            if ctrl_name == "SIMC (SISO)":
                q_j, diag = ctrl.compute(setpoint=t_sp, measurement=state.T, dt=dt)
                tj_sp_hist.append(ss.T_j)
            else:
                q_j, diag = ctrl.compute(t_sp=t_sp, t_pv=state.T, tj_pv=state.T_j, dt=dt)
                tj_sp_hist.append(diag["tj_sp"])

            # Integração numérica RK4
            x = state.to_array()
            def derivs(t_curr, x_arr):
                return p_inst.derivatives(t_curr, x_arr, q_j)
            k1 = np.array(derivs(t, x))
            k2 = np.array(derivs(t + 0.5*dt, x + 0.5*dt*k1))
            k3 = np.array(derivs(t + 0.5*dt, x + 0.5*dt*k2))
            k4 = np.array(derivs(t + dt, x + dt*k3))
            state = state.from_array(x + (dt/6.0)*(k1 + 2*k2 + 2*k3 + k4))

            t_hist.append(state.T)
            tj_hist.append(state.T_j)
            qj_hist.append(q_j)

        err = np.abs(np.array(t_hist) - ss.T)
        idx_post = int(2.0 / dt)
        iae = float(np.sum(err[idx_post:]) * dt)
        itae = float(np.sum((t_span[idx_post:] - 2.0) * err[idx_post:]) * dt)
        tv = float(np.sum(np.abs(np.diff(qj_hist[idx_post:]))))
        peak_dev = float(np.max(err[idx_post:]))

        res_dist[ctrl_name] = {
            "t": t_span,
            "T": np.array(t_hist),
            "T_j": np.array(tj_hist),
            "q_j": np.array(qj_hist),
            "T_j_sp": np.array(tj_sp_hist),
            "IAE": iae,
            "ITAE": itae,
            "TV": tv,
            "peak_dev": peak_dev,
        }
        logger.info(
            "%s -> IAE: %.3f K*min, Peak Dev: %.3f K, TV: %.1f L/min",
            ctrl_name, iae, peak_dev, tv
        )

    # =========================================================================
    # CENÁRIO 2: Incrustação Térmica (Fouling UA: 100% -> 70% e 60%)
    # =========================================================================
    logger.info("Executando Cenário 2: Incrustação térmica na jaqueta (Fouling)...")
    res_foul: Dict[str, Dict[str, Any]] = {}
    for ua_factor in [0.70, 0.60, 0.55]:
        for ctrl_name in ["SIMC (SISO)", "Cascade (Master-Slave)"]:
            p_fouled = CSTRPlant(params=CSTRParameters(UA=5.0e4 * ua_factor))
            state = ss
            if ctrl_name == "SIMC (SISO)":
                ctrl = PIDController(gains=simc_gains, actuator_limits=limits, u_bias=q_j_ss)
                ctrl.reset(initial_measurement=ss.T, initial_u=q_j_ss)
            else:
                ctrl = CascadePIDController(
                    gains=cascade_gains, actuator_limits=limits, u_bias=q_j_ss, t_j_bias=ss.T_j
                )
                ctrl.reset(initial_t=ss.T, initial_tj=ss.T_j, initial_u=q_j_ss)

            t_hist, qj_hist = [], []
            for t in t_span:
                t_sp = ss.T
                if ctrl_name == "SIMC (SISO)":
                    q_j, _ = ctrl.compute(setpoint=t_sp, measurement=state.T, dt=dt)
                else:
                    q_j, _ = ctrl.compute(t_sp=t_sp, t_pv=state.T, tj_pv=state.T_j, dt=dt)

                x = state.to_array()
                def derivs(t_curr, x_arr):
                    return p_fouled.derivatives(t_curr, x_arr, q_j)
                k1 = np.array(derivs(t, x))
                k2 = np.array(derivs(t + 0.5*dt, x + 0.5*dt*k1))
                k3 = np.array(derivs(t + 0.5*dt, x + 0.5*dt*k2))
                k4 = np.array(derivs(t + dt, x + dt*k3))
                state = state.from_array(x + (dt/6.0)*(k1 + 2*k2 + 2*k3 + k4))

                t_hist.append(state.T)
                qj_hist.append(q_j)

            key = f"{ctrl_name} (UA={int(ua_factor*100)}%)"
            final_T = t_hist[-1]
            final_q = qj_hist[-1]
            stable = abs(final_T - ss.T) < 1.0 and final_T < 405.0
            res_foul[key] = {
                "final_T": final_T,
                "final_qj": final_q,
                "stable": "Stable" if stable else "Thermal Runaway",
                "IAE": float(np.sum(np.abs(np.array(t_hist) - ss.T)) * dt),
            }

    # =========================================================================
    # GERAÇÃO DA TABELA LATEX: cascade_comparison_table.tex
    # =========================================================================
    def controllability(name: str) -> str:
        """Lowest tested UA that still regulates, and highest one that runs away."""
        ok = [f for f in (0.70, 0.60, 0.55) if res_foul[f"{name} (UA={int(f * 100)}%)"]["stable"] == "Stable"]
        lost = [f for f in (0.70, 0.60, 0.55) if f not in ok]
        held = f"held at {int(min(ok) * 100)}\\%" if ok else "none held"
        return held + (f", lost at {int(max(lost) * 100)}\\%" if lost else "")

    rows = []
    for label, name in (
        ("SIMC (SISO Direct)", "SIMC (SISO)"),
        ("Cascade ($T \\rightarrow T_j \\rightarrow q_j$)", "Cascade (Master-Slave)"),
    ):
        r = res_dist[name]
        rows.append({
            "Architecture": label,
            "Coolant Shock IAE": f"{r['IAE']:.2f}",
            "Peak Dev. (K)": f"{r['peak_dev']:.2f}",
            "TV (L/min)": f"{r['TV']:.1f}",
            "Fouling ($UA/UA_{\\mathrm{nom}}$)": controllability(name),
        })
    table_path = tables_dir / "cascade_comparison_table.tex"
    export_latex_table(
        data=rows,
        output_path=table_path,
        caption=(
            "SISO direct feedback vs industrial cascade ($T \\rightarrow T_j \\rightarrow q_j$): "
            "$+10$~K coolant supply shock at $t=2$~min (IAE, peak deviation and TV over "
            "$t \\ge 2$~min) and regulation under jacket fouling ($UA \\in \\{70, 60, 55\\}\\%$)."
        ),
        label="tab:cascade_comparison",
    )
    logger.info("Tabela salva em: %s", table_path)

    # =========================================================================
    # GERAÇÃO DA FIGURA: fig6_cascade_comparison.pdf
    # =========================================================================
    setup_ieee_style()
    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(IEEE_DOUBLE_COL_WIDTH_INCHES, 5.8), sharex=True, dpi=300
    )

    t = res_dist["SIMC (SISO)"]["t"]

    # Painel 1: Temperatura do Reator T
    ax1.plot(t, [ss.T] * len(t), "k--", lw=1.0, label="Reactor Setpoint $T_{sp}$ (396.65 K)")
    ax1.plot(t, res_dist["SIMC (SISO)"]["T"], color="#D95F02", lw=1.6, label="SIMC (SISO Direct)")
    ax1.plot(t, res_dist["Cascade (Master-Slave)"]["T"], color="#1B9E77", lw=1.6, label="Cascade ($T \\rightarrow T_j \\rightarrow q_j$)")
    ax1.axvline(2.0, color="gray", linestyle=":", lw=1.2)
    ax1.annotate(
        "Coolant Disturbance\n" + r"($\Delta T_{jf} = +10.0$ K)",
        xy=(2.0, 397.2),
        xytext=(0.20, 397.7),
        fontsize=8.5,
        color="#222222",
        ha="left",
        va="bottom",
        arrowprops=dict(arrowstyle="->", lw=0.9, color="#555555"),
    )
    ax1.set_ylabel(r"$T$ (K)", fontsize=9.0)
    ax1.set_ylim(396.0, 398.5)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", frameon=True, fontsize=8.0, framealpha=0.92)

    # Painel 2: Temperatura da Jaqueta T_j e Setpoint da Jaqueta T_j,sp
    ax2.plot(t, res_dist["SIMC (SISO)"]["T_j"], color="#D95F02", lw=1.4, linestyle="--", label="Jacket $T_j$ (SISO)")
    ax2.plot(t, res_dist["Cascade (Master-Slave)"]["T_j"], color="#1B9E77", lw=1.6, label="Jacket $T_j$ (Cascade)")
    ax2.plot(t, res_dist["Cascade (Master-Slave)"]["T_j_sp"], color="#7570B3", lw=1.2, linestyle=":", label="Jacket Setpoint $T_{j,sp}$ (Master)")
    ax2.axvline(2.0, color="gray", linestyle=":", lw=1.2)
    ax2.set_ylabel(r"$T_j$ (K)", fontsize=9.0)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right", frameon=True, fontsize=8.0, framealpha=0.92)

    # Painel 3: Vazão de Resfriamento q_j (Atuador)
    ax3.plot(t, res_dist["SIMC (SISO)"]["q_j"], color="#D95F02", lw=1.5, label="Coolant Flow $q_j$ (SISO)")
    ax3.plot(t, res_dist["Cascade (Master-Slave)"]["q_j"], color="#1B9E77", lw=1.6, label="Coolant Flow $q_j$ (Cascade)")
    ax3.axhline(300.0, color="red", linestyle="--", lw=1.0, label="Valve Saturation $u_{\\max} = 300$ L/min")
    ax3.axvline(2.0, color="gray", linestyle=":", lw=1.2)
    ax3.set_xlabel(r"Time $t$ (min)", fontsize=9.0)
    ax3.set_ylabel(r"$q_j$ (L/min)", fontsize=9.0)
    ax3.set_ylim(80.0, 260.0)
    ax3.grid(True, linestyle=":", alpha=0.6)
    ax3.legend(loc="upper right", frameon=True, fontsize=8.0, framealpha=0.92)

    fig.tight_layout()

    for d in [figures_dir, figures_novas_dir]:
        fig.savefig(d / "fig6_cascade_comparison.pdf", dpi=300)
        fig.savefig(d / "fig6_cascade_comparison.png", dpi=300)
        logger.info("Figura salva em: %s", d / "fig6_cascade_comparison.pdf")

    plt.close(fig)
    logger.info("Benchmark de controle em cascata concluído com sucesso!")


if __name__ == "__main__":
    run_cascade_benchmark()
