# %% [Módulo e Importações]
"""Regras de sintonia analítica para controladores PID baseadas em curvas de reação FOPTD.

Implementa os métodos clássicos e modernos da literatura de controle de processos:
    1. Ziegler-Nichols (Malha Aberta / Curva de Reação):
       - Kp = sinal(K) * (1.2 * tau) / (|K| * theta)
       - Ti = 2.0 * theta
       - Td = 0.5 * theta
       Visam resposta rápida e rejeição de distúrbios, porém com razão de declínio
       de 1/4 (overshoot elevado de ~25% a 40% e baixa margem de estabilidade).
    2. Cohen-Coon:
       - Incorpora a razão de atraso r = theta / tau para compensar processos
         com tempo morto significativo.
    3. Skogestad SIMC (Simple Internal Model Control):
       - Sintonia analítica moderna baseada em modelo interno com especificação
         direta do tempo de acomodação em malha fechada tau_c.
       - Garante excelente compromisso entre velocidade de rastreamento e robustez
         robusta em frequência (pico de sensibilidade típico Ms <= 1.6).

Suporta conscientização de sinal (sign-awareness) para processos de ação reversa
(onde ganho de processo K < 0 implica Kp < 0, como no controle de temperatura via resfriamento).
"""

import logging
from enum import Enum
from typing import Optional

import numpy as np
from scipy.optimize import brentq

from src.classical_control.foptd import FOPTDModel
from src.classical_control.pid_controller import PIDGains

logger = logging.getLogger(__name__)


# %% [Enumeração de Regras Clássicas de Sintonia]
class TuningRule(str, Enum):
    """Métodos analíticos clássicos e modernos suportados para sintonia de PID."""

    ZIEGLER_NICHOLS_PID = "ziegler_nichols_pid"
    COHEN_COON_PID = "cohen_coon_pid"
    SKOGESTAD_SIMC_PID = "skogestad_simc_pid"
    SKOGESTAD_SIMC_PI = "skogestad_simc_pi"
    TYREUS_LUYBEN = "Tyreus-Luyben"
    AMIGO = "AMIGO"


# %% [Regras Modernas: Tyreus-Luyben (1992) e AMIGO (Åström & Hägglund, 2004)]
def tune_tyreus_luyben(
    foptd: FOPTDModel, mode: str = "PID", n_filter: float = 10.0
) -> PIDGains:
    """Tyreus-Luyben tuning from the exact FOPTD ultimate point.

    Solves theta*w_u + arctan(tau*w_u) - pi = 0 on (pi/(2 theta), pi/theta) with brentq,
    then P_u = 2 pi / w_u and K_u = sign(K) * sqrt(1 + (tau w_u)^2) / |K|.

    Args:
        foptd: Identified FOPTD model (theta > 0).
        mode: "PID" (Kp = Ku/2.2, Ti = 2.2 Pu, Td = Pu/6.3) or "PI" (Kp = Ku/3.2, Ti = 2.2 Pu).
        n_filter: Derivative filter coefficient N.

    Returns:
        PIDGains: Tyreus-Luyben gains (sign follows the process gain).

    Raises:
        ValueError: If theta <= 0 (no finite ultimate frequency) or mode is unknown.
    """
    k, tau, theta = foptd.k_p, foptd.tau, foptd.theta
    if theta <= 0.0:
        raise ValueError("Tyreus-Luyben requires a positive dead time theta")
    w_u = brentq(
        lambda w: theta * w + np.arctan(tau * w) - np.pi,
        np.pi / (2.0 * theta) + 1e-9,
        np.pi / theta - 1e-9,
        xtol=1e-14,
    )
    p_u = 2.0 * np.pi / w_u
    k_u = np.sign(k) * np.sqrt(1.0 + (tau * w_u) ** 2) / abs(k)
    if mode == "PID":
        return PIDGains(kp=float(k_u / 2.2), ti=float(2.2 * p_u), td=float(p_u / 6.3),
                        n_filter=n_filter)
    if mode == "PI":
        return PIDGains(kp=float(k_u / 3.2), ti=float(2.2 * p_u), td=0.0, n_filter=n_filter)
    raise ValueError(f"Unknown mode {mode!r}; expected 'PID' or 'PI'")


def tune_amigo(foptd: FOPTDModel, mode: str = "PID", n_filter: float = 10.0) -> PIDGains:
    """AMIGO PID tuning (Åström & Hägglund, 2004), designed for Ms ~ 1.4.

    Kp = (0.2 + 0.45 tau/theta)/K, Ti = (0.4 theta + 0.8 tau)/(theta + 0.1 tau) * theta,
    Td = 0.5 theta tau / (0.3 theta + tau). PI mode uses the AMIGO-PI rule:
    Kp = 0.15/K + (0.35 - theta tau/(theta+tau)^2) tau/(K theta),
    Ti = 0.35 theta + 13 theta tau^2 / (tau^2 + 12 theta tau + 7 theta^2).

    Args:
        foptd: Identified FOPTD model (theta > 0).
        mode: "PID" or "PI".
        n_filter: Derivative filter coefficient N.

    Returns:
        PIDGains: AMIGO gains (sign follows the process gain).

    Raises:
        ValueError: If theta <= 0 or mode is unknown.
    """
    k, tau, theta = foptd.k_p, foptd.tau, foptd.theta
    if theta <= 0.0:
        raise ValueError("AMIGO requires a positive dead time theta")
    if mode == "PID":
        kp = (0.2 + 0.45 * tau / theta) / k
        ti = (0.4 * theta + 0.8 * tau) / (theta + 0.1 * tau) * theta
        td = 0.5 * theta * tau / (0.3 * theta + tau)
    elif mode == "PI":
        kp = 0.15 / k + (0.35 - theta * tau / (theta + tau) ** 2) * tau / (k * theta)
        ti = 0.35 * theta + 13.0 * theta * tau**2 / (tau**2 + 12.0 * theta * tau + 7.0 * theta**2)
        td = 0.0
    else:
        raise ValueError(f"Unknown mode {mode!r}; expected 'PID' or 'PI'")
    return PIDGains(kp=float(kp), ti=float(ti), td=float(td), n_filter=n_filter)


# %% [Função de Sintonia Analítica]
def tune_analytical(
    model: FOPTDModel,
    rule: TuningRule,
    tau_c: Optional[float] = None,
    n_filter: float = 10.0,
) -> PIDGains:
    """Calcula analiticamente os ganhos do PID a partir dos parâmetros FOPTD.

    Formulação Matemática das Regras:
        - Ziegler-Nichols:
          Kp = sinal(K) * (1.2 * tau) / (|K| * theta)
          Ti = 2.0 * theta
          Td = 0.5 * theta
        - Cohen-Coon:
          r = theta / tau
          Kp = sinal(K) * (tau / (|K| * theta)) * (4/3 + r/4)
          Ti = theta * (32 + 6*r) / (13 + 8*r)
          Td = theta * 4 / (11 + 2*r)
        - Skogestad SIMC:
          tau_c = tau_c se especificado, senão max(theta, 0.1 * tau)
          Kp = sinal(K) * (1 / |K|) * (tau / (tau_c + theta))
          Ti = min(tau, 4 * (tau_c + theta))
          Td = 0.33 * theta (para PID) ou 0.0 (para PI)

    Args:
        model: Modelo FOPTD identificado contendo ganho k_p, constante tau e atraso theta.
        rule: Regra de sintonia analítica selecionada (Enum TuningRule).
        tau_c: Constante de tempo desejada em malha fechada para regra SIMC [min].
            Se None, adota a recomendação padrão de Skogestad: max(theta, 0.1 * tau).
        n_filter: Coeficiente de filtragem da ação derivativa N (tau_f = Td / N).

    Returns:
        PIDGains: Instância configurada com os ganhos calculados (kp, ti, td, n_filter).

    Raises:
        ValueError: Caso a regra especificada seja desconhecida.
    """
    if rule == TuningRule.TYREUS_LUYBEN:
        return tune_tyreus_luyben(model, n_filter=n_filter)
    if rule == TuningRule.AMIGO:
        return tune_amigo(model, n_filter=n_filter)

    k = model.k_p
    tau = model.tau
    # Proteção contra tempo morto nulo para evitar divisão por zero
    theta = max(model.theta, 0.02 * tau)
    sign_k = 1.0 if k >= 0 else -1.0
    abs_k = abs(k)

    r_ratio = theta / tau

    if rule == TuningRule.ZIEGLER_NICHOLS_PID:
        # Ziegler-Nichols por Curva de Reação (Malha Aberta)
        kp = sign_k * (1.2 * tau) / (abs_k * theta)
        ti = 2.0 * theta
        td = 0.5 * theta

    elif rule == TuningRule.COHEN_COON_PID:
        # Cohen-Coon: compensação aprimorada para razões theta/tau elevadas
        kp = sign_k * (tau / (abs_k * theta)) * ((4.0 / 3.0) + (r_ratio / 4.0))
        ti = theta * (32.0 + 6.0 * r_ratio) / (13.0 + 8.0 * r_ratio)
        td = theta * 4.0 / (11.0 + 2.0 * r_ratio)

    elif rule == TuningRule.SKOGESTAD_SIMC_PID:
        # Skogestad SIMC para PID (robusto com Ms moderado)
        tc = tau_c if tau_c is not None else max(theta, 0.1 * tau)
        kp = sign_k * (1.0 / abs_k) * (tau / (tc + theta))
        ti = min(tau, 4.0 * (tc + theta))
        td = 0.33 * theta

    elif rule == TuningRule.SKOGESTAD_SIMC_PI:
        # Skogestad SIMC para PI (elimina ação derivativa)
        tc = tau_c if tau_c is not None else max(theta, 0.1 * tau)
        kp = sign_k * (1.0 / abs_k) * (tau / (tc + theta))
        ti = min(tau, 4.0 * (tc + theta))
        td = 0.0

    else:
        raise ValueError(f"Regra de sintonia analítica não reconhecida: {rule}")

    gains = PIDGains(
        kp=float(kp),
        ti=float(ti),
        td=float(td),
        n_filter=float(n_filter),
    )

    logger.info(
        "Sintonia Analítica [%s]: Kp=%.3f, Ti=%.3f min, Td=%.3f min",
        rule.value,
        gains.kp,
        gains.ti,
        gains.td,
    )

    return gains


# %% [Bloco de Execução Interativa / Demonstração no Spyder]
if __name__ == "__main__":
    print("=" * 70)
    print("DEMONSTRAÇÃO INTERATIVA SPYDER 6: Sintonia Analítica Clássica (FOPTD)")
    print("=" * 70)

    # Modelo representativo da malha de temperatura do CSTR
    cstr_model = FOPTDModel(k_p=-0.15, tau=1.20, theta=0.25)
    print(f"Modelo FOPTD da Planta: Kp = {cstr_model.k_p:.3f} K/(L/min), "
          f"tau = {cstr_model.tau:.2f} min, theta = {cstr_model.theta:.2f} min\n")

    regras = [
        ("Ziegler-Nichols PID", TuningRule.ZIEGLER_NICHOLS_PID, None),
        ("Cohen-Coon PID", TuningRule.COHEN_COON_PID, None),
        ("Skogestad SIMC PID (tau_c = theta)", TuningRule.SKOGESTAD_SIMC_PID, 0.25),
        ("Skogestad SIMC PI  (tau_c = theta)", TuningRule.SKOGESTAD_SIMC_PI, 0.25),
    ]

    print(f"{'Método de Sintonia':<36} | {'Kp':>8} | {'Ti (min)':>8} | {'Td (min)':>8}")
    print("-" * 70)

    for nome, reg, tc_val in regras:
        g = tune_analytical(cstr_model, rule=reg, tau_c=tc_val)
        print(f"{nome:<36} | {g.kp:>8.3f} | {g.ti:>8.3f} | {g.td:>8.3f}")

    print("\nDemonstração de sintonia analítica concluída com sucesso no Spyder 6.")
    print("=" * 70)
