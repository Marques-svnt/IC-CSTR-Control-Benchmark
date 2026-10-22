# %% [Módulo e Importações]
"""Identificação de modelos de Primeira Ordem com Tempo Morto (FOPTD).

Fornece a representação analítica de modelos FOPTD (First-Order Plus Time Delay)
e algoritmos de identificação paramétrica a partir de dados experimentais ou
simulados de ensaios de resposta ao degrau em malha aberta.

A função de transferência clássica de processo é definida no domínio de Laplace por:
    G(s) = [K_p * exp(-theta * s)] / (tau * s + 1)

Onde:
    - K_p: Ganho estático do processo (delta_y / delta_u) [unidades de PV / unidades de MV].
    - tau: Constante de tempo dominante do processo [min].
    - theta: Tempo morto aparente / atraso de transporte puro [min].

O algoritmo de identificação utiliza uma estimativa heurística robusta baseada
no método dos dois pontos (Sundaresan-Krishnaswamy a 28.3% e 63.2% da transição)
seguida de refinamento ótimo não-linear por mínimos quadrados via Levenberg-Marquardt
ou Trust Region Reflective (scipy.optimize.curve_fit).
"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from scipy.optimize import curve_fit

logger = logging.getLogger(__name__)


# %% [Modelo Analítico FOPTD]
@dataclass(frozen=True)
class FOPTDModel:
    """Parâmetros e cálculo da resposta no tempo de uma função de transferência FOPTD.

    Modelo Matemático no Domínio de Laplace:
        G(s) = (K_p * e^(-theta * s)) / (tau * s + 1)

    Equação Diferencial no Domínio do Tempo:
        tau * (dy(t)/dt) + y(t) = K_p * u(t - theta)

    Attributes:
        k_p: Ganho estático do processo [unidades_PV / unidades_MV].
        tau: Constante de tempo dominante [min]. Deve ser estritamente positiva.
        theta: Tempo morto / atraso de transporte aparente [min]. Não-negativo.
    """

    k_p: float
    tau: float
    theta: float

    def __post_init__(self) -> None:
        """Validação física dos parâmetros do modelo."""
        if self.tau <= 0.0:
            raise ValueError(f"A constante de tempo tau deve ser positiva, obtido {self.tau}")
        if self.theta < 0.0:
            raise ValueError(f"O tempo morto theta deve ser não-negativo, obtido {self.theta}")

    def step_response(self, t: np.ndarray, delta_u: float, y0: float = 0.0) -> np.ndarray:
        """Calcula a trajetória analítica temporal exata da resposta ao degrau y(t).

        Expressão Analítica:
            - Para t < theta:         y(t) = y_0
            - Para t >= theta:        y(t) = y_0 + K_p * delta_u * [1 - exp(-(t - theta) / tau)]

        Args:
            t: Vetor 1D de instantes de tempo [min].
            delta_u: Amplitude do degrau de entrada aplicado em t = 0.
            y0: Nível de base inicial da variável de processo antes do degrau.

        Returns:
            np.ndarray: Série temporal da resposta analítica calculada y(t).
        """
        y = np.full_like(t, y0, dtype=np.float64)
        active_mask = t >= self.theta
        t_active = t[active_mask] - self.theta
        y[active_mask] = y0 + self.k_p * delta_u * (1.0 - np.exp(-t_active / self.tau))
        return y

    def to_control_tf(self, pade_order: int = 3):
        """Converte o modelo FOPTD para `control.TransferFunction` com aproximação de Padé.

        Args:
            pade_order: Ordem da aproximação racional de Padé para exp(-theta * s).

        Returns:
            control.TransferFunction: Função de transferência racional racionalizada G(s).
        """
        import control as ct

        g_lag = ct.tf([self.k_p], [self.tau, 1.0])
        if self.theta > 1e-6 and pade_order > 0:
            num_d, den_d = ct.pade(self.theta, pade_order)
            g_delay = ct.tf(num_d, den_d)
            return g_lag * g_delay
        return g_lag


# %% [Algoritmo de Identificação Numérica FOPTD]
def identify_foptd(
    t: np.ndarray,
    y: np.ndarray,
    delta_u: float,
    y0: Optional[float] = None,
) -> Tuple[FOPTDModel, float]:
    """Ajusta um modelo FOPTD ótimo a curvas de resposta ao degrau empíricas ou simuladas.

    O processo de identificação é dividido em duas etapas fundamentais:
        1. Estimativa Heurística Inicial (Método de Sundaresan-Krishnaswamy / Smith):
           Localiza os tempos onde a resposta atinge 28.3% e 63.2% da variação total:
               tau_init = 1.5 * (t_63.2% - t_28.3%)
               theta_init = max(t_63.2% - tau_init, 0.0)
               k_init = delta_y / delta_u
        2. Otimização Não-Linear por Mínimos Quadrados:
           Refina [K_p, tau, theta] via curve_fit sujeitos a limites físicos estritos
           (tau > 0, theta >= 0 e sinal do ganho consistente com o processo).

    Args:
        t: Vetor de tempo [min] iniciando em 0.
        y: Curva da variável controlada medida ao longo do ensaio degrau.
        delta_u: Magnitude não-nula do degrau aplicado no sinal de controle.
        y0: Valor de linha de base inicial. Se None, adota y[0].

    Returns:
        Tuple[FOPTDModel, float]:
            - Instância com os parâmetros identificados (k_p, tau, theta).
            - Raiz do Erro Quadrático Médio (RMSE) entre a curva medida e a ajustada.

    Raises:
        ValueError: Caso delta_u seja nulo ou as dimensões dos vetores sejam incompatíveis.
    """
    if abs(delta_u) < 1e-9:
        raise ValueError("A magnitude do degrau delta_u não pode ser nula para identificação")
    if len(t) != len(y) or len(t) < 5:
        raise ValueError(
            "Os vetores de tempo e saída devem ter dimensões iguais com pelo menos 5 pontos"
        )

    baseline = y[0] if y0 is None else y0
    total_delta_y = y[-1] - baseline
    k_init = total_delta_y / delta_u

    # 1. Estimativa Heurística dos Pontos Críticos (28.3% e 63.2%)
    y_28 = baseline + 0.283 * total_delta_y
    y_63 = baseline + 0.632 * total_delta_y

    sign = 1.0 if total_delta_y >= 0 else -1.0
    idx_28 = np.where(sign * y >= sign * y_28)[0]
    idx_63 = np.where(sign * y >= sign * y_63)[0]

    t_28 = float(t[idx_28[0]]) if len(idx_28) > 0 else float(t[-1] * 0.3)
    t_63 = float(t[idx_63[0]]) if len(idx_63) > 0 else float(t[-1] * 0.6)

    tau_init = max(1.5 * (t_63 - t_28), 0.05)
    theta_init = max(t_63 - tau_init, 0.0)

    # 2. Função Paramétrica para Regressão Não-Linear
    def foptd_fit(
        time_pts: np.ndarray, k_val: float, tau_val: float, theta_val: float
    ) -> np.ndarray:
        m = FOPTDModel(k_p=k_val, tau=tau_val, theta=theta_val)
        return m.step_response(time_pts, delta_u, y0=baseline)

    # Limites físicos de busca paramétrica
    lower_bounds = [-np.inf if k_init < 0 else 0.0, 0.01, 0.0]
    upper_bounds = [0.0 if k_init < 0 else np.inf, t[-1] * 2.0, t[-1] * 0.8]

    p0 = [k_init, tau_init, theta_init]

    try:
        popt, _ = curve_fit(
            f=foptd_fit,
            xdata=t,
            ydata=y,
            p0=p0,
            bounds=(lower_bounds, upper_bounds),
            maxfev=2000,
        )
    except Exception as exc:
        logger.warning(
            "curve_fit FOPTD falhou (%s), utilizando parâmetros da estimativa heurística", exc
        )
        popt = p0

    model = FOPTDModel(k_p=float(popt[0]), tau=float(popt[1]), theta=float(popt[2]))
    y_pred = model.step_response(t, delta_u, y0=baseline)
    rmse = float(np.sqrt(np.mean((y - y_pred) ** 2)))

    logger.info(
        "FOPTD Identificado: Kp=%.4f, tau=%.3f min, theta=%.3f min (RMSE=%.4e)",
        model.k_p,
        model.tau,
        model.theta,
        rmse,
    )

    return model, rmse


# %% [Bloco de Execução Interativa / Demonstração no Spyder]
if __name__ == "__main__":
    print("=" * 70)
    print("DEMONSTRAÇÃO INTERATIVA SPYDER 6: Identificação de Modelo FOPTD")
    print("=" * 70)

    # 1. Criação de modelo sintético de referência para validação
    true_kp = -0.185     # K / (L/min)
    true_tau = 1.45      # min
    true_theta = 0.32    # min
    model_real = FOPTDModel(k_p=true_kp, tau=true_tau, theta=true_theta)

    t_vec = np.linspace(0.0, 10.0, 300)
    delta_u_test = 10.0  # +10 L/min degrau
    y_base = 350.0       # K

    # 2. Resposta teórica com adição de ruído de processo
    y_synthetic = model_real.step_response(t_vec, delta_u=delta_u_test, y0=y_base)
    rng = np.random.default_rng(123)
    y_noisy = y_synthetic + rng.normal(0.0, 0.02, size=len(t_vec))

    # 3. Execução da identificação não-linear
    model_est, fit_rmse = identify_foptd(
        t=t_vec, y=y_noisy, delta_u=delta_u_test, y0=y_base
    )

    print("\n[Comparativo: Parâmetros Reais vs Identificados]:")
    print(f"  Ganho Kp:     Real = {true_kp:+.4f} | Identificado = {model_est.k_p:+.4f}")
    print(f"  Tau [min]:    Real = {true_tau:.4f}  | Identificado = {model_est.tau:.4f}")
    print(f"  Theta [min]:  Real = {true_theta:.4f}  | Identificado = {model_est.theta:.4f}")
    print(f"  Qualidade do Ajuste (RMSE): {fit_rmse:.4e} K")

    print("\nDemonstração de identificação FOPTD concluída com sucesso no Spyder 6.")
    print("=" * 70)
