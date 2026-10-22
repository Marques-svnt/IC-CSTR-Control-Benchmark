# %% [Módulo e Importações]
"""Modelo fenomenológico de Reator Tanque Agitado Contínuo (CSTR) Não-Isotérmico.

Implementa as equações diferenciais ordinárias (ODEs) não-lineares com cinética
de Arrhenius exotérmica de primeira ordem e dinâmica térmica da camisa de
resfriamento (cooling jacket), em conformidade com Seborg et al. e Ogunnaike.

Equações Fundamentais de Balanço:
    1. Balanço Molar do Reagente A:
       dC_A/dt = (q / V) * (C_Af - C_A) - r_A
    2. Balanço de Energia no Reator:
       dT/dt = (q / V) * (T_f - T) + [(-delta_H) / (rho * cp)] * r_A
               - [UA / (V * rho * cp)] * (T - T_j)
    3. Balanço de Energia na Camisa de Resfriamento:
       dT_j/dt = (q_j / V_j) * (T_jf - T_j) + [UA / (V_j * rho_j * cp_j)] * (T - T_j)
    4. Taxa de Reação Cinética de Arrhenius:
       r_A = k_0 * exp(-E_over_R / T) * C_A
"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from scipy.optimize import root

logger = logging.getLogger(__name__)


# %% [Parâmetros Fenomenológicos do CSTR]
@dataclass(frozen=True)
class CSTRParameters:
    """Parâmetros físico-químicos e operacionais nominais do reator CSTR.

    Representa as propriedades térmicas, geométricas e cinéticas do reator
    e da camisa de resfriamento, baseadas no benchmark clássico da literatura.

    Attributes:
        q: Vazão volumétrica da corrente de processo [L/min].
        V: Volume reacional útil do reator [L].
        k_0: Fator pré-exponencial cinético de Arrhenius [1/min].
        E_over_R: Energia de ativação dividida pela constante universal dos gases [K].
        delta_H: Entalpia de reação [cal/mol] (negativa para reações exotérmicas).
        rho_cp: Capacidade calorífica volumétrica da mistura reacional [cal/(L*K)].
        UA: Coeficiente global de transferência térmica vezes área de troca [cal/(min*K)].
        V_j: Volume útil da camisa de resfriamento [L].
        rho_j_cp_j: Capacidade calorífica volumétrica do fluido refrigerante [cal/(L*K)].
        C_Af: Concentração de reagente na alimentação de entrada [mol/L].
        T_f: Temperatura de entrada da corrente de processo [K].
        T_jf: Temperatura de alimentação do refrigerante na camisa [K].
    """

    q: float = 100.0
    V: float = 100.0
    k_0: float = 7.2e10
    E_over_R: float = 8750.0
    delta_H: float = -5.0e4
    rho_cp: float = 500.0
    UA: float = 5.0e4
    V_j: float = 20.0
    rho_j_cp_j: float = 500.0
    C_Af: float = 1.0
    T_f: float = 350.0
    T_jf: float = 300.0

    def __post_init__(self) -> None:
        """Valida os parâmetros físicos em runtime via contrato Pydantic v2."""
        from src.sim_core.schemas import CstrParameterContract

        CstrParameterContract(
            q=self.q,
            V=self.V,
            k_0=self.k_0,
            E_over_R=self.E_over_R,
            delta_H=self.delta_H,
            rho_cp=self.rho_cp,
            UA=self.UA,
            V_j=self.V_j,
            rho_j_cp_j=self.rho_j_cp_j,
            C_Af=self.C_Af,
            T_f=self.T_f,
            T_jf=self.T_jf,
        )


# %% [Estrutura de Estado do Reator]
@dataclass
class CSTRState:
    """Vetor de estados do reator contínuo perfeitamente agitado.

    Representa o estado instantâneo do sistema em determinado instante temporal.

    Attributes:
        C_A: Concentração molar do reagente no meio reacional [mol/L].
        T: Temperatura do meio reacional no interior do reator [K].
        T_j: Temperatura do fluido refrigerante no interior da camisa [K].
    """

    C_A: float
    T: float
    T_j: float

    def to_array(self) -> np.ndarray:
        """Converte o vetor de estados em um array 1D NumPy [C_A, T, T_j].

        Returns:
            np.ndarray: Array de ponto flutuante com dimensões (3,).
        """
        return np.array([self.C_A, self.T, self.T_j], dtype=np.float64)

    @classmethod
    def from_array(cls, arr: np.ndarray) -> "CSTRState":
        """Reconstrói a instância de estado a partir de um array 1D [C_A, T, T_j].

        Args:
            arr: Array NumPy de dimensão mínima 3.

        Returns:
            CSTRState: Objeto de estado reconstruído com valores tipados em float.
        """
        return cls(C_A=float(arr[0]), T=float(arr[1]), T_j=float(arr[2]))


# %% [Classe Principal da Planta CSTR]
class CSTRPlant:
    """Planta CSTR não-linear com reação exotérmica de 1ª ordem e camisa térmica.

    Implementa a avaliação de derivadas das equações diferenciais ordinárias (ODEs),
    o cálculo numérico de estados estacionários e a linearização analítica em torno
    de um ponto de operação via cálculo das matrizes Jacobianas A e B.
    """

    def __init__(self, params: Optional[CSTRParameters] = None) -> None:
        """Inicializa a planta CSTR com os parâmetros fenomenológicos especificados.

        Args:
            params: Configuração de parâmetros da planta. Se None, adota
                os parâmetros clássicos de benchmark da literatura.
        """
        self.params = params or CSTRParameters()
        logger.info(
            "CSTRPlant inicializado: V=%.1f L, q=%.1f L/min, UA=%.1f cal/(min*K)",
            self.params.V,
            self.params.q,
            self.params.UA,
        )

    def reaction_rate(self, C_A: float, T: float) -> float:
        """Calcula a taxa volumétrica de consumo do reagente A: r_A = k(T) * C_A.

        A dependência da constante de velocidade k(T) com a temperatura segue
        a equação fenomenológica de Arrhenius: k(T) = k_0 * exp(-E / (R * T)).

        Args:
            C_A: Concentração molar do reagente no meio reacional [mol/L].
            T: Temperatura absoluta do meio reacional [K].

        Returns:
            float: Taxa instantânea de consumo de reagente [mol/(L*min)].
        """
        # Proteção numérica contra temperaturas negativas ou não-físicas na exponencial
        T_safe = max(100.0, float(T))
        k = self.params.k_0 * np.exp(-self.params.E_over_R / T_safe)
        # Concentração molar é não-negativa
        return float(k * max(0.0, float(C_A)))

    def derivatives(
        self,
        t: float,
        state: np.ndarray,
        q_j: float,
        disturbances: Optional[dict[str, float]] = None,
    ) -> np.ndarray:
        """Calcula as derivadas temporais dos estados da planta: dx/dt = f(x, u, d).

        Implementa os balanços acoplados de massa e energia para o CSTR:
            - Balanço Molar: dC_A/dt = (q/V)*(C_Af - C_A) - r_A
            - Balanço de Energia (Reator):
              dT/dt = (q/V)*(T_f - T) + [(-delta_H)/(rho*cp)]*r_A - [UA/(V*rho*cp)]*(T - T_j)
            - Balanço de Energia (Camisa):
              dT_j/dt = (q_j/V_j)*(T_jf - T_j) + [UA/(V_j*rho_j*cp_j)]*(T - T_j)

        Args:
            t: Instante de tempo contínuo [min] (exigido por integradores ODE).
            state: Array unidimensional com os estados atuais [C_A, T, T_j].
            q_j: Vazão volumétrica de fluido de resfriamento na camisa [L/min].
            disturbances: Dicionário opcional contendo distúrbios dinâmicos nos
                parâmetros nominais ('C_Af', 'T_f', 'T_jf', 'UA', 'q').

        Returns:
            np.ndarray: Vetor contendo as derivadas [dC_A/dt, dT/dt, dT_j/dt].
        """
        C_A, T, T_j = float(state[0]), float(state[1]), float(state[2])
        p = self.params

        # Injeção dinâmica de perturbações externas nos parâmetros de entrada
        C_Af = disturbances.get("C_Af", p.C_Af) if disturbances else p.C_Af
        T_f = disturbances.get("T_f", p.T_f) if disturbances else p.T_f
        T_jf = disturbances.get("T_jf", p.T_jf) if disturbances else p.T_jf
        UA = disturbances.get("UA", p.UA) if disturbances else p.UA
        q = disturbances.get("q", p.q) if disturbances else p.q

        # Cálculo da cinética de consumo químico
        r_A = self.reaction_rate(C_A, T)

        # 1. Balanço Molar do Reagente A no reator perfeitamente agitado
        dC_A_dt = (q / p.V) * (C_Af - C_A) - r_A

        # 2. Balanço de Energia Térmica no meio reacional (calor gerado vs calor trocado)
        heat_gen = (-p.delta_H / p.rho_cp) * r_A
        heat_removal = (UA / (p.V * p.rho_cp)) * (T - T_j)
        dT_dt = (q / p.V) * (T_f - T) + heat_gen - heat_removal

        # 3. Balanço de Energia Térmica na camisa de resfriamento (remoção de calor)
        jacket_exchange = (UA / (p.V_j * p.rho_j_cp_j)) * (T - T_j)
        dT_j_dt = (q_j / p.V_j) * (T_jf - T_j) + jacket_exchange

        return np.array([dC_A_dt, dT_dt, dT_j_dt], dtype=np.float64)

    def find_steady_state(
        self, q_j: float, initial_guess: Optional[CSTRState] = None
    ) -> CSTRState:
        """Determina o estado estacionário de equilíbrio x_ss onde f(x_ss, q_j) = 0.

        Utiliza o método Powell híbrido ('hybr') da biblioteca SciPy para resolver
        o sistema não-linear acoplado de 3 equações algébricas.

        Args:
            q_j: Vazão volumétrica constante de fluido refrigerante [L/min].
            initial_guess: Estimativa inicial para o resolvedor numérico.
                Se None, utiliza estimativa física razoável [0.1 mol/L, 350 K, 300 K].

        Returns:
            CSTRState: Estado de equilíbrio estacionário computado.

        Raises:
            RuntimeError: Caso o resolvedor numérico não convirja para o equilíbrio.
        """
        guess = (
            initial_guess.to_array()
            if initial_guess is not None
            else np.array([0.1, 350.0, 300.0], dtype=np.float64)
        )

        def residual(x: np.ndarray) -> np.ndarray:
            return self.derivatives(0.0, x, q_j)

        res = root(residual, guess, method="hybr")
        if not res.success:
            logger.error(
                "Falha ao encontrar estado estacionário para q_j=%.2f: %s", q_j, res.message
            )
            raise RuntimeError(f"Falha de convergência do estado estacionário: {res.message}")

        ss_state = CSTRState.from_array(res.x)
        logger.info(
            "Estado estacionário (q_j=%.2f): C_A=%.4f mol/L, T=%.2f K, T_j=%.2f K",
            q_j,
            ss_state.C_A,
            ss_state.T,
            ss_state.T_j,
        )
        return ss_state

    def linearize(
        self, state_ss: CSTRState, q_j_ss: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Calcula analiticamente as matrizes Jacobianas do espaço de estados (A e B).

        Realiza a expansão em série de Taylor de primeira ordem em torno do ponto
        de operação (x_ss, q_j_ss):
            dx/dt = A * delta_x + B * delta_u
        onde A = [df_i/dx_j] (3x3) e B = [df_i/du] (3x1).

        Args:
            state_ss: Ponto de operação em estado estacionário [C_A, T, T_j].
            q_j_ss: Vazão de refrigerante no ponto de operação nominal [L/min].

        Returns:
            Tuple[np.ndarray, np.ndarray]:
                - Matriz Jacobiana de dinâmica de estados A de dimensão (3, 3).
                - Matriz Jacobiana de entrada de controle B de dimensão (3, 1).
        """
        p = self.params
        C_A = state_ss.C_A
        T = state_ss.T
        T_j = state_ss.T_j

        # Avaliação da constante cinética e sua derivada analítica em relação a T
        k = p.k_0 * np.exp(-p.E_over_R / T)
        dk_dT = k * (p.E_over_R / (T**2))

        # Derivadas parciais para a Linha 1: d(dC_A/dt) / d[C_A, T, T_j]
        a11 = -(p.q / p.V) - k
        a12 = -dk_dT * C_A
        a13 = 0.0

        # Derivadas parciais para a Linha 2: d(dT/dt) / d[C_A, T, T_j]
        a21 = (-p.delta_H / p.rho_cp) * k
        a22 = (
            -(p.q / p.V)
            + (-p.delta_H / p.rho_cp) * (dk_dT * C_A)
            - (p.UA / (p.V * p.rho_cp))
        )
        a23 = p.UA / (p.V * p.rho_cp)

        # Derivadas parciais para a Linha 3: d(dT_j/dt) / d[C_A, T, T_j]
        a31 = 0.0
        a32 = p.UA / (p.V_j * p.rho_j_cp_j)
        a33 = -(q_j_ss / p.V_j) - (p.UA / (p.V_j * p.rho_j_cp_j))

        A = np.array(
            [
                [a11, a12, a13],
                [a21, a22, a23],
                [a31, a32, a33],
            ],
            dtype=np.float64,
        )

        # Derivadas parciais em relação ao controle de resfriamento q_j: d(dx/dt) / dq_j
        b1 = 0.0
        b2 = 0.0
        b3 = (p.T_jf - T_j) / p.V_j

        B = np.array([[b1], [b2], [b3]], dtype=np.float64)

        logger.debug("Autovalores da matriz linearizada A: %s", np.linalg.eigvals(A))
        return A, B


# %% [Bloco de Execução Interativa / Demonstração no Spyder]
if __name__ == "__main__":
    print("=" * 70)
    print("DEMONSTRAÇÃO INTERATIVA SPYDER 6: Planta CSTR Não-Isotérmica")
    print("=" * 70)

    # 1. Instanciação da planta fenomenológica
    plant = CSTRPlant()
    q_j_nominal = 100.0  # L/min

    # 2. Busca do estado estacionário
    ss = plant.find_steady_state(q_j=q_j_nominal)
    print(f"\n[Ponto de Operação Nominal (q_j = {q_j_nominal:.1f} L/min)]")
    print(f"  Concentração C_A: {ss.C_A:.4f} mol/L")
    print(f"  Temperatura T:    {ss.T:.2f} K ({ss.T - 273.15:.2f} °C)")
    print(f"  Temp. Camisa T_j: {ss.T_j:.2f} K ({ss.T_j - 273.15:.2f} °C)")

    # 3. Linearização analítica
    A, B = plant.linearize(ss, q_j_nominal)
    eigvals = np.linalg.eigvals(A)

    print("\n[Matriz Jacobiana do Sistema Linearizado A (3x3)]:")
    print(np.array2string(A, precision=4, suppress_small=True))
    print("\n[Vetor de Entrada B (3x1)]:")
    print(np.array2string(B, precision=4, suppress_small=True))

    print("\n[Autovalores do Sistema Aberto (Estabilidade Local)]:")
    for idx, ev in enumerate(eigvals, start=1):
        estabilidade = "Estável" if ev.real < 0 else "Instável"
        print(f"  lambda_{idx}: {ev.real:+.4f} + {ev.imag:+.4f}j ({estabilidade})")

    print("\nDemonstração concluída com sucesso no Spyder 6.")
    print("=" * 70)
