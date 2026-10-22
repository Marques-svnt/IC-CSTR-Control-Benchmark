# %% [Módulo e Importações]
"""Motor de simulação em malha fechada do CSTR com controle PID realimentado.

Coordena a interação híbrida entre o tempo contínuo (equações diferenciais fenomenológicas
da planta integradas numericamente via RK45) e o tempo discreto (amostragem digital do
controlador PID e dinâmicas não-lineares de saturação e taxa do atuador).

Permite avaliar a estabilidade, a rejeição a distúrbios de carga, a robustez a ruído
de medição e o rastreamento de trajetórias dinâmicas de setpoint, calculando automaticamente
todas as métricas acadêmicas e industriais de desempenho (IAE, ITAE, ISE, TV, Mp, ts).
"""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from src.classical_control.pid_controller import PIDController
from src.evaluation.metrics import ControlPerformanceMetrics, evaluate_performance
from src.sim_core.cstr_plant import CSTRPlant, CSTRState
from src.sim_core.integrator import NumericalIntegrator

logger = logging.getLogger(__name__)


# %% [Estrutura de Resultados da Simulação em Malha Fechada]
@dataclass
class ClosedLoopResult:
    """Trajetórias completas e métricas calculadas em uma simulação em malha fechada.

    Attributes:
        t: Vetor 1D de tempo discretizado [min].
        setpoint: Vetor 1D contendo a trajetória de referência desejada (SP) [K].
        t_pv: Vetor 1D contendo a variável de processo medida (PV) [K].
        states: Matriz bidimensional de estados verdadeiros (N, 3) contendo [C_A, T, T_j].
        u_applied: Vetor 1D contendo a ação de controle real entregue pelo atuador [L/min].
        u_unconstrained: Vetor 1D da ação ideal calculada pelo PID antes da saturação [L/min].
        metrics: Dataclass contendo as métricas quantitativas de desempenho calculadas.
    """

    t: np.ndarray
    setpoint: np.ndarray
    t_pv: np.ndarray
    states: np.ndarray
    u_applied: np.ndarray
    u_unconstrained: np.ndarray
    metrics: ControlPerformanceMetrics


# %% [Simulador em Malha Fechada do CSTR com PID]
class ClosedLoopSimulator:
    """Simulador de malha fechada acoplando controlador discreto e planta contínua."""

    def __init__(self, integrator: Optional[NumericalIntegrator] = None) -> None:
        """Inicializa o simulador em malha fechada com o integrador especificado.

        Args:
            integrator: Mecanismo de integração numérica contínua. Padrão: RK45.
        """
        self.integrator = integrator or NumericalIntegrator(method="RK45")

    def run(
        self,
        plant: CSTRPlant,
        controller: PIDController,
        initial_state: CSTRState,
        t_span: tuple[float, float],
        dt: float,
        setpoint_func: Callable[[float], float],
        disturbance_func: Optional[Callable[[float], dict[str, float]]] = None,
        noise_std: float = 0.0,
        seed: Optional[int] = None,
        t_step: float = 0.0,
    ) -> ClosedLoopResult:
        """Executa a simulação em malha fechada ao longo de um horizonte temporal.

        Ciclo de Execução a Cada Amostra t_k:
            1. Avaliação do setpoint SP(t_k) e medição do sensor com ruído: PV = T(t_k) + ruído.
            2. Cálculo da ação digital pelo controlador PID e atuação da válvula:
               (u_real, diag) = controller.compute(SP, PV, dt).
            3. Propagação contínua dos estados da planta ao longo de [t_k, t_k + dt]
               mantendo u_real constante (ZOH) e aplicando distúrbios exógenos.
            4. Registro das trajetórias e cálculo final consolidado das métricas de controle.

        Args:
            plant: Modelo da planta não-linear CSTR.
            controller: Instância configurada do controlador PID.
            initial_state: Vetor de estado físico inicial em t = t_span[0].
            t_span: Intervalo temporal de simulação (t_inicio, t_fim) [min].
            dt: Intervalo de amostragem e controle discreto [min].
            setpoint_func: Função que mapeia o tempo na referência de temperatura: t -> SP(t) [K].
            disturbance_func: Função opcional que injeta variações paramétricas: t -> dict.
            noise_std: Desvio padrão do ruído gaussiano adicionado ao sensor de temperatura [K].
            seed: Semente pseudoaleatória para reprodutibilidade.
            t_step: Instante do degrau de setpoint [min], usado no ITAE ponderado.

        Returns:
            ClosedLoopResult: Resultados completos das trajetórias temporais e métricas.
        """
        rng = np.random.default_rng(seed)
        t_points = np.arange(t_span[0], t_span[1] + 1e-9, dt)
        n_steps = len(t_points)

        states = np.zeros((n_steps, 3), dtype=np.float64)
        sp_arr = np.zeros(n_steps, dtype=np.float64)
        t_pv_arr = np.zeros(n_steps, dtype=np.float64)
        u_app_arr = np.zeros(n_steps, dtype=np.float64)
        u_uncon_arr = np.zeros(n_steps, dtype=np.float64)

        current_state = initial_state
        u_init = float(controller.u_bias)
        controller.reset(initial_measurement=current_state.T, initial_u=controller.u_bias)

        logger.info(
            "Iniciando simulação malha fechada: t_span=%s, dt=%.3f min, passos=%d",
            t_span,
            dt,
            n_steps,
        )

        for i in range(n_steps):
            t_now = t_points[i]
            sp = setpoint_func(t_now)
            sp_arr[i] = sp
            states[i] = current_state.to_array()

            noise = rng.normal(0.0, noise_std) if noise_std > 0.0 else 0.0
            pv_measured = current_state.T + noise
            t_pv_arr[i] = pv_measured

            # 1. Execução do algoritmo de controle (PID clássico ou multivariável/ótimo)
            if getattr(controller, "supports_full_state", False):
                u_act, diag = controller.compute(
                    setpoint=sp,
                    measurement=pv_measured,
                    dt=dt,
                    full_state=current_state.to_array(),
                )
            else:
                u_act, diag = controller.compute(setpoint=sp, measurement=pv_measured, dt=dt)
            u_app_arr[i] = u_act
            u_uncon_arr[i] = diag.get("u_unconstrained", u_act)

            # 2. Integração contínua da planta até a próxima amostra temporal
            if i < n_steps - 1:
                dist = disturbance_func(t_now) if disturbance_func else None
                current_state = self.integrator.step(
                    plant=plant,
                    current_state=current_state,
                    q_j=u_act,
                    t_current=t_now,
                    dt=dt,
                    disturbances=dist,
                )

        # 3. Métricas sobre a temperatura física verdadeira (sem ruído do sensor)
        metrics = evaluate_performance(
            t=t_points,
            y=states[:, 1],
            setpoint=sp_arr,
            u=u_app_arr,
            u_init=u_init,
            t_step=t_step,
        )

        logger.info(
            "Malha fechada finalizada: IAE=%.2f, ITAE=%.2f, TV=%.2f, Mp=%.1f%%",
            metrics.iae,
            metrics.itae,
            metrics.tv,
            metrics.overshoot_pct,
        )

        return ClosedLoopResult(
            t=t_points,
            setpoint=sp_arr,
            t_pv=t_pv_arr,
            states=states,
            u_applied=u_app_arr,
            u_unconstrained=u_uncon_arr,
            metrics=metrics,
        )


# %% [Bloco de Execução Interativa / Demonstração no Spyder]
if __name__ == "__main__":
    from src.classical_control.pid_controller import AntiWindupMethod, PIDGains
    from src.sim_core.actuators import ActuatorLimits

    print("=" * 70)
    print("DEMONSTRAÇÃO INTERATIVA SPYDER 6: Simulação em Malha Fechada (CSTR)")
    print("=" * 70)

    # 1. Planta fenomenológica e ponto nominal
    plant_demo = CSTRPlant()
    q_j_ss = 100.0  # L/min
    ss_nominal = plant_demo.find_steady_state(q_j=q_j_ss)

    # 2. Sintonia de PID clássico
    gains_demo = PIDGains(kp=-8.5, ti=1.1, td=0.18, n_filter=10.0)
    limits_demo = ActuatorLimits(u_min=0.0, u_max=300.0, max_slew_rate=120.0)
    pid_ctrl = PIDController(
        gains=gains_demo,
        actuator_limits=limits_demo,
        anti_windup=AntiWindupMethod.CLAMPING,
        derivative_on_measurement=True,
        u_bias=q_j_ss,
    )

    # 3. Execução da simulação com degrau de setpoint de -2 K em t = 0 min
    target_temp = ss_nominal.T - 2.0
    sim_engine = ClosedLoopSimulator()

    print(f"Temperatura Nominal: {ss_nominal.T:.2f} K -> Alvo: {target_temp:.2f} K")
    print("Executando simulação de 5 minutos...")

    sim_res = sim_engine.run(
        plant=plant_demo,
        controller=pid_ctrl,
        initial_state=ss_nominal,
        t_span=(0.0, 5.0),
        dt=0.02,
        setpoint_func=lambda t: target_temp,
        noise_std=0.01,
        seed=123,
    )

    m = sim_res.metrics
    print("\n[Métricas de Desempenho em Malha Fechada]:")
    print(f"  IAE (Área do Erro):        {m.iae:.3f} K·min")
    print(f"  ITAE (Ponderado no Tempo): {m.itae:.3f} K·min²")
    print(f"  TV (Esforço do Atuador):   {m.tv:.2f} L/min")
    print(f"  Sobressinal (Mp):          {m.overshoot_pct:.2f} %")
    ts_str = f"{m.settling_time:.2f} min" if m.settling_time is not None else "Não acomodou"
    print(f"  Tempo de Acomodação (2%):  {ts_str}")
    tr_str = f"{m.rise_time:.2f} min" if m.rise_time is not None else "N/A"
    print(f"  Tempo de Subida (10-90%):  {tr_str}")

    print("\nDemonstração de simulação malha fechada concluída com sucesso no Spyder 6.")
    print("=" * 70)
