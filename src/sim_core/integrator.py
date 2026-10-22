# %% [Módulo e Importações]
"""Integrador numérico para simulação de processos químicos contínuos não-lineares.

Fornece integração temporal robusta das equações diferenciais ordinárias (ODEs)
da planta CSTR através da biblioteca SciPy (solve_ivp). Suporta esquemas
explícitos e implícitos adequados para sistemas rígidos (stiff):
    - RK45 (Dormand-Prince ordem 4/5 com passo adaptativo, padrão).
    - Radau (Método implícito de Radau IIA de 5ª ordem para alta rigidez térmica).
    - BDF (Fórmulas de Diferenciação Regressiva para sistemas químicos stiff).

Gerencia a evolução temporal contínua da planta sob controle digital discreto com
intervalos de amostragem dt constantes, além de simulação em malha aberta com
admissão de ruído de medição gaussiano e perturbações exógenas de carga.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from scipy.integrate import solve_ivp

from src.sim_core.cstr_plant import CSTRPlant, CSTRState

logger = logging.getLogger(__name__)


# %% [Contêiner de Resultados de Simulação]
@dataclass
class SimulationResult:
    """Contêiner de séries temporais resultantes de uma simulação da planta.

    Attributes:
        t: Vetor 1D de instantes de tempo discretizados [min].
        states: Matriz bidimensional de estados de dimensão (N, 3) contendo [C_A, T, T_j].
        u: Vetor 1D contendo a trajetória do sinal de controle aplicado [L/min].
        T_measured: Vetor 1D contendo as medições ruidosas da temperatura do reator [K].
    """

    t: np.ndarray
    states: np.ndarray
    u: np.ndarray
    T_measured: np.ndarray


# %% [Motor de Integração Numérica para ODEs]
class NumericalIntegrator:
    """Gerencia a integração contínua das ODEs do CSTR entre intervalos discretos."""

    def __init__(self, method: str = "RK45", rtol: float = 1e-6, atol: float = 1e-8) -> None:
        """Inicializa o motor de integração numérica com parâmetros de tolerância.

        Args:
            method: Algoritmo de integração do SciPy ('RK45', 'Radau', 'BDF', 'LSODA').
            rtol: Tolerância relativa do erro local de truncamento.
            atol: Tolerância absoluta do erro local de truncamento.
        """
        self.method = method
        self.rtol = rtol
        self.atol = atol
        logger.debug(
            "NumericalIntegrator inicializado com método=%s, rtol=%.1e, atol=%.1e",
            method,
            rtol,
            atol,
        )

    def step(
        self,
        plant: CSTRPlant,
        current_state: CSTRState,
        q_j: float,
        t_current: float,
        dt: float,
        disturbances: Optional[dict[str, float]] = None,
    ) -> CSTRState:
        """Avança os estados da planta ao longo de um único intervalo de amostragem dt.

        A ação de controle manipulada q_j é mantida rigorosamente constante durante
        o intervalo [t_current, t_current + dt] (emulação de Segurador de Ordem Zero - ZOH).

        Args:
            plant: Instância da planta fenomenológica do CSTR.
            current_state: Estado da planta no instante inicial do passo t_current.
            q_j: Vazão volumétrica de refrigerante constante no intervalo [L/min].
            t_current: Instante temporal de início da integração [min].
            dt: Período de amostragem / passo de controle [min].
            disturbances: Dicionário opcional com perturbações dinâmicas de parâmetros.

        Returns:
            CSTRState: Estado predito da planta no instante futuro t_current + dt.

        Raises:
            RuntimeError: Caso o integrador falhe ou resulte em estados não-físicos/NaNs.
        """
        y0 = current_state.to_array()
        t_span = (t_current, t_current + dt)

        # Integração numérica de alta precisão via scipy.integrate.solve_ivp
        sol = solve_ivp(
            fun=lambda t, y: plant.derivatives(t, y, q_j, disturbances=disturbances),
            t_span=t_span,
            y0=y0,
            method=self.method,
            rtol=self.rtol,
            atol=self.atol,
        )

        if not sol.success:
            logger.error(
                "Falha na integração no instante t=%.2f: %s", t_current, sol.message
            )
            raise RuntimeError(f"Falha de integração numérica ODE: {sol.message}")

        y_next = sol.y[:, -1]
        # Validação de integridade numérica contra explosão numérica ou singularidades
        if np.any(np.isnan(y_next)) or np.any(np.isinf(y_next)):
            raise RuntimeError(
                f"Estado numérico inválido (NaN/Inf) em t={t_current + dt}: {y_next}"
            )

        return CSTRState.from_array(y_next)

    def simulate_open_loop(
        self,
        plant: CSTRPlant,
        initial_state: CSTRState,
        t_span: tuple[float, float],
        dt: float,
        u_func: Callable[[float], float],
        disturbance_func: Optional[Callable[[float], dict[str, float]]] = None,
        noise_std: float = 0.0,
        seed: Optional[int] = None,
    ) -> SimulationResult:
        """Simula a trajetória da planta em malha aberta sob perfil arbitrário de controle.

        Permite a geração de dados empíricos de resposta ao degrau para
        identificação de modelos FOPTD e ensaios de dinâmica de processo.

        Args:
            plant: Instância da planta não-linear CSTR.
            initial_state: Vetor de estado no instante t = t_span[0].
            t_span: Intervalo temporal total (t_inicio, t_fim) em minutos.
            dt: Passo de discretização / período de amostragem [min].
            u_func: Função que mapeia o tempo contínuo na ação u: t -> q_j(t).
            disturbance_func: Função opcional que injeta distúrbios: t -> dict.
            noise_std: Desvio padrão do ruído gaussiano adicionado à medição de T [K].
            seed: Semente pseudoaleatória para reprodutibilidade estocástica.

        Returns:
            SimulationResult: Estrutura contendo todas as séries temporais simuladas.
        """
        rng = np.random.default_rng(seed)
        t_points = np.arange(t_span[0], t_span[1] + 1e-9, dt)
        n_steps = len(t_points)

        states = np.zeros((n_steps, 3), dtype=np.float64)
        u_vals = np.zeros(n_steps, dtype=np.float64)
        T_meas = np.zeros(n_steps, dtype=np.float64)

        current_state = initial_state
        states[0] = current_state.to_array()
        u_vals[0] = u_func(t_points[0])
        noise_0 = rng.normal(0.0, noise_std) if noise_std > 0 else 0.0
        T_meas[0] = current_state.T + noise_0

        for i in range(n_steps - 1):
            t_now = t_points[i]
            q_j = u_func(t_now)
            u_vals[i] = q_j

            dist = disturbance_func(t_now) if disturbance_func else None
            current_state = self.step(
                plant, current_state, q_j, t_now, dt, disturbances=dist
            )
            states[i + 1] = current_state.to_array()

            noise_i = rng.normal(0.0, noise_std) if noise_std > 0 else 0.0
            T_meas[i + 1] = current_state.T + noise_i

        u_vals[-1] = u_func(t_points[-1])

        return SimulationResult(
            t=t_points,
            states=states,
            u=u_vals,
            T_measured=T_meas,
        )


# %% [Bloco de Execução Interativa / Demonstração no Spyder]
if __name__ == "__main__":
    print("=" * 70)
    print("DEMONSTRAÇÃO INTERATIVA SPYDER 6: Integrador Numérico RK45")
    print("=" * 70)

    # 1. Configuração da planta e estado estacionário nominal
    plant_demo = CSTRPlant()
    q_j_ss = 100.0  # L/min
    ss_state = plant_demo.find_steady_state(q_j=q_j_ss)

    # 2. Configuração do integrador com RK45
    integrator = NumericalIntegrator(method="RK45", rtol=1e-6, atol=1e-8)

    # 3. Simulação de ensaio degrau em malha aberta: +15 L/min na vazão da camisa
    delta_q = 15.0  # L/min
    t_end = 6.0     # minutos
    dt_sim = 0.05   # minutos

    print(f"Executando simulação malha aberta por {t_end:.1f} min (dt = {dt_sim} min)...")
    res = integrator.simulate_open_loop(
        plant=plant_demo,
        initial_state=ss_state,
        t_span=(0.0, t_end),
        dt=dt_sim,
        u_func=lambda t: q_j_ss + (delta_q if t >= 1.0 else 0.0),
        noise_std=0.05,
        seed=42,
    )

    T_init = res.states[0, 1]
    T_final = res.states[-1, 1]
    delta_temp = T_final - T_init

    print("\n[Resultados do Ensaio ao Degrau de Refrigeração]:")
    print(f"  Instantes simulados: {len(res.t)} passos")
    print(f"  Temperatura Inicial T(0): {T_init:.2f} K")
    print(f"  Temperatura Final T(end): {T_final:.2f} K")
    print(f"  Variação delta_T:         {delta_temp:.2f} K (Processo com Ganho Inverso)")
    print(f"  C_A Final:                {res.states[-1, 0]:.4f} mol/L")

    print("\nDemonstração do integrador numérico concluída com sucesso no Spyder 6.")
    print("=" * 70)
