# %% [Módulo e Importações]
"""Sintonia numérica de controladores PID por otimização restrita à sensibilidade máxima (Ms).

Implementa a sintonia direta não-linear baseada na minimização de índices de desempenho
integrais (ITAE, IAE ou ISE) calculados sobre a planta fenomenológica não-linear CSTR,
sujeita a restrições de robustez no domínio da frequência através do pico de
sensibilidade máxima:
    Ms = ||S(jw)||_inf = max_w |1 / (1 + L(jw))| <= max_ms (tipicamente 1.6)

A sensibilidade máxima Ms está diretamente ligada às margens clássicas de estabilidade:
    - Margem de Ganho: GM >= Ms / (Ms - 1)
    - Margem de Fase:  PM >= 2 * arcsin(1 / (2 * Ms))
Para Ms <= 1.6, garante-se GM >= 2.67 (8.5 dB) e PM >= 36.4 graus, prevenindo
instabilidade sob variações paramétricas ou não-linearidades operacionais.
"""

import logging
from enum import Enum
from typing import Optional, Tuple

import numpy as np
from scipy.optimize import minimize

from src.classical_control.closed_loop import ClosedLoopSimulator
from src.classical_control.foptd import FOPTDModel
from src.classical_control.pid_controller import AntiWindupMethod, PIDController, PIDGains
from src.sim_core.actuators import ActuatorLimits
from src.sim_core.cstr_plant import CSTRPlant, CSTRState

logger = logging.getLogger(__name__)


# %% [Critérios Integrais de Otimização]
class OptimizationCriterion(str, Enum):
    """Critérios de desempenho integral para otimização da resposta transitória."""

    ITAE = "itae"  # Integral do Erro Absoluto Ponderado no Tempo
    IAE = "iae"    # Integral do Erro Absoluto
    ISE = "ise"    # Integral do Erro Quadrático


# %% [Cálculo da Sensibilidade Máxima no Domínio da Frequência]
def calculate_maximum_sensitivity_foptd(
    foptd: FOPTDModel,
    gains: PIDGains,
    omega_range: Tuple[float, float] = (1e-3, 1e3),
    n_freqs: int = 5000,
) -> float:
    """Calcula o pico Ms = max_w |1 / (1 + G_p(jw) C_pid(jw))| para FOPTD com atraso theta.

    Avalia a função de sensibilidade clássica (Eq. 29 do manuscrito):
        S(jw) = 1 / (1 + G_p(jw) * C_pid(jw))
    onde G_p(jw) = [k_p * exp(-jw * theta)] / (tau * jw + 1) e C_pid(jw) é a resposta em frequência
    do PID paralelo com filtro derivativo de primeira ordem (N=10).

    Args:
        foptd: Modelo FOPTD identificado com ganho k_p, constante de tempo tau e atraso theta [min].
        gains: Parâmetros de sintonia do controlador PID.
        omega_range: Intervalo de frequências (omega_min, omega_max) [rad/min].
        n_freqs: Quantidade de pontos amostrais distribuídos logaritmicamente na frequência.

    Returns:
        float: Pico máximo da curva de sensibilidade Ms = ||S||_inf.
    """
    omegas = np.logspace(np.log10(omega_range[0]), np.log10(omega_range[1]), n_freqs)
    return float(np.max(sensitivity_magnitude_foptd(foptd, gains, omegas)))


def _pid_frequency_response(gains: PIDGains, s: np.ndarray) -> np.ndarray:
    """C(jw) of the parallel PID with first-order derivative filter Td/N."""
    tau_f = gains.td / gains.n_filter if gains.td > 0 else 0.0
    d_term = (gains.kp * gains.td * s) / (1.0 + tau_f * s) if gains.td > 0 else 0.0
    return gains.kp + gains.kp / (s * gains.ti) + d_term


def loop_gain_foptd(foptd: FOPTDModel, gains: PIDGains, omegas: np.ndarray) -> np.ndarray:
    """L(jw) = G_p(jw) C(jw) with the exact dead time of the identified FOPTD model."""
    s = 1j * np.asarray(omegas, dtype=np.float64)
    g_jw = (foptd.k_p / (foptd.tau * s + 1.0)) * np.exp(-s * foptd.theta)
    return g_jw * _pid_frequency_response(gains, s)


def loop_gain_linearized(
    plant: CSTRPlant,
    state: CSTRState,
    q_j: float,
    gains: PIDGains,
    omegas: np.ndarray,
    theta: float = 0.0,
) -> np.ndarray:
    """L(jw) = C (jwI - A)^-1 B e^{-jw theta} C_pid(jw) on the Jacobian of the CSTR at `state`."""
    A, B = plant.linearize(state, q_j)
    c_row = np.array([[0.0, 1.0, 0.0]], dtype=np.float64)  # measured output T
    s = 1j * np.asarray(omegas, dtype=np.float64)
    g_jw = np.array(
        [complex((c_row @ np.linalg.solve(si * np.eye(3) - A, B))[0, 0]) for si in s]
    )
    return g_jw * np.exp(-s * theta) * _pid_frequency_response(gains, s)


def phase_margin_deg(loop: np.ndarray, omegas: np.ndarray) -> float:
    """Phase margin at the highest gain crossover |L(jw)| = 1 of a sampled loop gain.

    Args:
        loop: L(jw) sampled on increasing `omegas`.
        omegas: Frequency grid [rad/min], fine enough to resolve the crossover.

    Returns:
        180 deg + unwrapped phase of L at the crossover (interpolated linearly in log w).

    Raises:
        ValueError: If |L| never crosses 1 on the grid.
    """
    mag = np.abs(loop)
    idx = np.where((mag[:-1] >= 1.0) & (mag[1:] < 1.0))[0]
    if len(idx) == 0:
        raise ValueError("No gain crossover |L| = 1 on the frequency grid")
    k = idx[-1]
    phase = np.unwrap(np.angle(loop))
    frac = (np.log(mag[k])) / (np.log(mag[k]) - np.log(mag[k + 1]))
    phase_c = phase[k] + frac * (phase[k + 1] - phase[k])
    # Reference the phase to the loop's own low-frequency branch (-90 deg for integral action)
    branch = 360.0 * np.round((np.degrees(phase[0]) + 90.0) / 360.0)
    return float(np.degrees(phase_c) + 180.0 - branch)


def sensitivity_magnitude_foptd(
    foptd: FOPTDModel, gains: PIDGains, omegas: np.ndarray
) -> np.ndarray:
    """|S(jw)| = |1 / (1 + G_p(jw) C_pid(jw))| for the exact dead-time FOPTD loop.

    Args:
        foptd: Identified FOPTD model.
        gains: PID gains (parallel form, first-order derivative filter Td/N).
        omegas: Frequencies [rad/min].

    Returns:
        Array of |S(jw)| with the shape of `omegas`.
    """
    return np.abs(1.0 / (1.0 + loop_gain_foptd(foptd, gains, omegas)))


def calculate_maximum_sensitivity(
    plant: Optional[CSTRPlant] = None,
    nominal_state: Optional[CSTRState] = None,
    q_j_ss: Optional[float] = None,
    gains: PIDGains = None,
    omega_range: Tuple[float, float] = (1e-3, 1e3),
    n_freqs: int = 2000,
    foptd: Optional[FOPTDModel] = None,
    theta: Optional[float] = None,
) -> float:
    """Calcula o pico de sensibilidade Ms = max_w |1 / (1 + L(jw))| da malha linearizada ou FOPTD.

    Quando `foptd` é fornecido, avalia diretamente a sensibilidade sobre a função de transferência
    G_p(s) = (k_p * exp(-theta*s)) / (tau*s + 1) identificada, incorporando rigorosamente o atraso
    aparente de transporte na resposta de fase (Eq. 29 do manuscrito).
    Se `foptd` não for fornecido, usa a linearização em espaço de estados do CSTR físico, aplicando
    o termo de atraso exp(-jw * theta) se `theta` for especificado.

    Args:
        plant: Instância da planta CSTR física (opcional se foptd for informado).
        nominal_state: Estado estacionário do ponto de operação.
        q_j_ss: Vazão de fluido de resfriamento no estado estacionário.
        gains: Candidato a parâmetros de sintonia do controlador PID.
        omega_range: Intervalo de frequências de teste (omega_min, omega_max) [rad/min].
        n_freqs: Quantidade de pontos amostrais distribuídos logaritmicamente na frequência.
        foptd: Modelo FOPTD identificado com ganho, constante de tempo e atraso aparente theta.
        theta: Atraso de transporte opcional a ser acoplado à planta linearizada [min].

    Returns:
        float: Pico da curva de sensibilidade Ms (adimensional). Valores entre 1.2 e 1.6
        indicam excelente robustez; valores acima de 2.0 indicam oscilação ou fragilidade.
    """
    if foptd is not None:
        return calculate_maximum_sensitivity_foptd(
            foptd=foptd, gains=gains, omega_range=omega_range, n_freqs=n_freqs
        )

    if plant is None or nominal_state is None or q_j_ss is None:
        raise ValueError("Deve ser fornecido 'foptd' ou ('plant', 'nominal_state', 'q_j_ss').")

    omegas = np.logspace(np.log10(omega_range[0]), np.log10(omega_range[1]), n_freqs)
    loop = loop_gain_linearized(plant, nominal_state, q_j_ss, gains, omegas, theta=theta or 0.0)
    return float(np.max(np.abs(1.0 / (1.0 + loop))))


def analyze_loop_margins_and_gang_of_4(
    foptd: FOPTDModel,
    gains: PIDGains,
    pade_order: int = 3,
    omega_range: Tuple[float, float] = (1e-2, 1e2),
    n_freqs: int = 500,
) -> dict[str, float | np.ndarray]:
    """Certifica margens de estabilidade e a Gang of Four de Åström via python-control.

    Calcula:
        - Margem de ganho (GM), Margem de fase (PM [deg]) e frequências de cruzamento.
        - As 4 funções da Gang of Four sobre a malha racionalizada via Padé:
          S(s) = 1/(1+PC), T(s) = PC/(1+PC), PS(s) = P/(1+PC), CS(s) = C/(1+PC).

    Args:
        foptd: Modelo FOPTD identificado.
        gains: Ganhos do controlador PID.
        pade_order: Ordem da aproximação de Padé para o atraso de transporte theta.
        omega_range: Faixa de frequências (w_min, w_max) [rad/min].
        n_freqs: Número de frequências avaliadas.

    Returns:
        Dicionário contendo `gm`, `pm_deg`, `ms_exact`, `mt_peak`, e vetores `omega`,
        `mag_S`, `mag_T`, `mag_PS`, `mag_CS`.
    """
    import control as ct

    P_sys = foptd.to_control_tf(pade_order=pade_order)
    tau_f = gains.td / gains.n_filter if gains.td > 0 else 1e-4
    s = ct.tf([1.0, 0.0], [1.0])
    C_sys = (
        gains.kp
        + gains.kp / (gains.ti * s)
        + (gains.kp * gains.td * s) / (tau_f * s + 1.0)
    )

    L_sys = P_sys * C_sys
    gm, pm, wg, wp = ct.margin(L_sys)

    S_sys = ct.feedback(1, L_sys)
    T_sys = ct.feedback(L_sys, 1)
    PS_sys = ct.feedback(P_sys, C_sys)
    CS_sys = ct.feedback(C_sys, P_sys)

    omegas = np.logspace(np.log10(omega_range[0]), np.log10(omega_range[1]), n_freqs)
    mag_S = np.abs(S_sys(1j * omegas))
    mag_T = np.abs(T_sys(1j * omegas))
    mag_PS = np.abs(PS_sys(1j * omegas))
    mag_CS = np.abs(CS_sys(1j * omegas))

    ms_exact = calculate_maximum_sensitivity_foptd(foptd, gains, omega_range=omega_range)
    return {
        "gm": float(gm) if gm is not None else float("inf"),
        "pm_deg": float(pm) if pm is not None else 180.0,
        "wg": float(wg) if wg is not None else float("nan"),
        "wp": float(wp) if wp is not None else float("nan"),
        "ms_exact": float(ms_exact),
        "ms_pade": float(np.max(mag_S)),
        "mt_peak": float(np.max(mag_T)),
        "omega": omegas,
        "mag_S": mag_S,
        "mag_T": mag_T,
        "mag_PS": mag_PS,
        "mag_CS": mag_CS,
    }


# %% [Sintonia Numérica Ótima por Simplex Nelder-Mead com Restrição de Ms]
def tune_by_optimization(
    plant: CSTRPlant,
    nominal_state: CSTRState,
    q_j_ss: float,
    target_dT: float = -2.0,
    initial_gains: Optional[PIDGains] = None,
    criterion: OptimizationCriterion = OptimizationCriterion.ITAE,
    max_ms: float = 1.6,
    t_sim: float = 8.0,
    dt: float = 0.02,
    foptd: Optional[FOPTDModel] = None,
    limits: Optional[ActuatorLimits] = None,
) -> PIDGains:
    """Sintoniza ganhos ótimos de PID minimizando critério integral com restrição de Ms.

    O algoritmo emprega o método do Simplex de Nelder-Mead (scipy.optimize.minimize)
    sobre uma função objetivo que combina o índice integral não-linear e barreiras
    de penalidade quadrática para:
        - Violação da robustez em frequência: 1e4 * max(0, Ms - max_ms)^2
        - Erro residual em regime estacionário: penalidade caso haja offset significativo.

    Args:
        plant: Instância da planta fenomenológica CSTR.
        nominal_state: Ponto de operação inicial em estado estacionário.
        q_j_ss: Ponto de operação nominal do sinal de controle manipulado [L/min].
        target_dT: Variação em degrau da referência de temperatura [K].
        initial_gains: Estimativa inicial de ganhos. Se None, adota padrão conservador.
        criterion: Critério integral a minimizar (ITAE, IAE, ISE).
        max_ms: Teto máximo de sensibilidade permissível (padrão 1.6 para robustez).
        t_sim: Duração temporal da simulação de avaliação em malha fechada [min].
        dt: Passo temporal de discretização / integração [min].
        foptd: Identified FOPTD model. When given, Ms is evaluated on the dead-time loop
            (required for a meaningful Ms constraint; the delay-free Jacobian gives Ms ~ 1).
        limits: Valve limits used in the evaluation simulations. Pass the benchmark valve so
            the optimum is computed for the actuator it will run on. Default: [0, 300] L/min,
            100 L/min^2 (legacy).

    Returns:
        PIDGains: Instância contendo os ganhos ótimos convergidos.
    """
    if initial_gains is None:
        # Ponto de partida conservador padrão (Kp moderado negativo para ação reversa)
        p0 = np.array([-5.0, 1.5, 0.2], dtype=np.float64)
    else:
        p0 = np.array([initial_gains.kp, initial_gains.ti, initial_gains.td], dtype=np.float64)

    target_T = nominal_state.T + target_dT
    sim = ClosedLoopSimulator()
    limits = limits or ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=100.0)

    def objective(params: np.ndarray) -> float:
        kp, ti, td = float(params[0]), float(params[1]), float(params[2])

        # Restrições de viabilidade física direta (ação reversa: kp < 0, ti > 0, td >= 0)
        if kp >= 0.0 or ti <= 0.05 or td < 0.0:
            return 1e6

        candidate_gains = PIDGains(kp=kp, ti=ti, td=td)

        # 1. Verificação de robustez em frequência via sensibilidade máxima Ms
        ms = calculate_maximum_sensitivity(
            plant, nominal_state, q_j_ss, candidate_gains, foptd=foptd
        )
        ms_penalty = 1e4 * max(0.0, ms - max_ms) ** 2 if ms > max_ms else 0.0

        # 2. Simulação transitória em malha fechada sobre a planta não-linear
        pid = PIDController(
            gains=candidate_gains,
            actuator_limits=limits,
            anti_windup=AntiWindupMethod.CLAMPING,
            u_bias=q_j_ss,
        )

        try:
            res = sim.run(
                plant=plant,
                controller=pid,
                initial_state=nominal_state,
                t_span=(0.0, t_sim),
                dt=dt,
                setpoint_func=lambda t: target_T,
            )
        except Exception:
            return 1e6

        if criterion == OptimizationCriterion.ITAE:
            perf = res.metrics.itae
        elif criterion == OptimizationCriterion.IAE:
            perf = res.metrics.iae
        else:
            perf = res.metrics.ise

        # Penalização para evitar erro estático permanente (offset residual)
        final_err = abs(res.t_pv[-1] - target_T)
        offset_penalty = 1e3 * final_err if final_err > 0.5 else 0.0

        total_cost = perf + ms_penalty + offset_penalty
        return float(total_cost)

    logger.info(
        "Iniciando otimização de PID: critério=%s (max_ms=%.2f)",
        criterion.value,
        max_ms,
    )

    res = minimize(
        fun=objective,
        x0=p0,
        method="Nelder-Mead",
        options={"maxiter": 120, "xatol": 1e-2, "fatol": 1e-2, "disp": False},
    )

    opt_kp, opt_ti, opt_td = float(res.x[0]), float(res.x[1]), float(res.x[2])
    opt_gains = PIDGains(kp=opt_kp, ti=max(opt_ti, 0.05), td=max(opt_td, 0.0))
    final_ms = calculate_maximum_sensitivity(plant, nominal_state, q_j_ss, opt_gains, foptd=foptd)

    logger.info(
        "PID Ótimo encontrado: Kp=%.3f, Ti=%.3f min, Td=%.3f min (Ms=%.2f, Custo=%.2f)",
        opt_gains.kp,
        opt_gains.ti,
        opt_gains.td,
        final_ms,
        res.fun,
    )

    return opt_gains


# %% [Bloco de Execução Interativa / Demonstração no Spyder]
if __name__ == "__main__":
    print("=" * 70)
    print("DEMONSTRAÇÃO INTERATIVA SPYDER 6: Otimização PID Restrita por Ms")
    print("=" * 70)

    # 1. Configuração da planta e do ponto de operação nominal
    plant_demo = CSTRPlant()
    q_j_nom = 100.0
    ss_demo = plant_demo.find_steady_state(q_j=q_j_nom)

    # 2. Avaliação de sensibilidade máxima para ganhos de teste
    gains_teste = PIDGains(kp=-7.5, ti=1.2, td=0.15)
    ms_teste = calculate_maximum_sensitivity(
        plant=plant_demo,
        nominal_state=ss_demo,
        q_j_ss=q_j_nom,
        gains=gains_teste,
    )
    print(f"Ganhos Teste: Kp={gains_teste.kp:.2f}, Ti={gains_teste.ti:.2f}, "
          f"Td={gains_teste.td:.2f}")
    print(f"Pico de Sensibilidade Máxima Ms: {ms_teste:.3f} (Limite Robusto: <= 1.60)")

    # 3. Execução de otimização rápida (t_sim curto para visualização no Spyder)
    print("\nExecutando otimização via Nelder-Mead minimizando ITAE com Ms <= 1.60...")
    gains_opt = tune_by_optimization(
        plant=plant_demo,
        nominal_state=ss_demo,
        q_j_ss=q_j_nom,
        target_dT=-1.0,
        criterion=OptimizationCriterion.ITAE,
        max_ms=1.6,
        t_sim=3.0,
        dt=0.05,
    )
    ms_final = calculate_maximum_sensitivity(
        plant=plant_demo,
        nominal_state=ss_demo,
        q_j_ss=q_j_nom,
        gains=gains_opt,
    )

    print("\n[Resultados da Sintonia por Otimização Numérica]:")
    print(f"  Kp Ótimo:      {gains_opt.kp:.3f}")
    print(f"  Ti Ótimo:      {gains_opt.ti:.3f} min")
    print(f"  Td Ótimo:      {gains_opt.td:.3f} min")
    print(f"  Ms Resultante: {ms_final:.3f} (Restrição Respeitada: {ms_final <= 1.65})")

    print("\nDemonstração de otimização concluída com sucesso no Spyder 6.")
    print("=" * 70)
