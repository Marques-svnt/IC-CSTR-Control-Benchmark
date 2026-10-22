# %% [Módulo e Importações]
"""Critérios matemáticos de desempenho quantitativo para análise de controle de processos.

Implementa a avaliação numérica de índices canônicos no domínio do tempo e de esforço
de controle para sistemas de controle clássico, neural e baseado em agentes:
    1. IAE (Integral do Erro Absoluto):
       IAE = integral |e(t)| dt
       Quantifica a área total de desvio do setpoint ao longo do horizonte temporal.
    2. ITAE (Integral do Erro Absoluto Ponderado no Tempo):
       ITAE = integral t * |e(t)| dt
       Penaliza com severidade oscilações tardias e acomodação lenta.
    3. ISE (Integral do Erro Quadrático):
       ISE = integral e(t)^2 dt
       Penaliza severamente grandes transientes e picos de erro iniciais.
    4. TV (Variação Total da Ação de Controle):
       TV = sum |u_k - u_{k-1}|
       Métrica fundamental que quantifica a suavidade e o desgaste físico da válvula.
    5. Sobressinal Percentual (Overshoot / Mp):
       Mp = max(0, (y_pico - SP) / Delta_SP) * 100%
    6. Tempo de Acomodação (Settling Time - ts):
       Tempo a partir do qual a variável de processo permanece dentro de +/- 2% do degrau.
    7. Tempo de Subida (Rise Time - tr):
       Tempo necessário para a resposta transitar de 10% a 90% do valor final.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# %% [Estrutura de Métricas de Desempenho de Controle]
@dataclass(frozen=True)
class ControlPerformanceMetrics:
    """Conjunto padronizado de métricas quantitativas de desempenho em malha fechada.

    Attributes:
        iae: Integral do Erro Absoluto [unidade_PV * min].
        itae: Integral do Erro Absoluto Ponderado no Tempo [unidade_PV * min^2].
        ise: Integral do Erro Quadrático [unidade_PV^2 * min].
        tv: Variação Total do sinal de controle manipulado [unidade_MV].
        overshoot_pct: Sobressinal percentual máximo de ultrapassagem [%].
        settling_time: Tempo de acomodação para a faixa de tolerância de +/- 2% [min].
        rise_time: Tempo de subida entre 10% e 90% da transição de referência [min].
    """

    iae: float
    itae: float
    ise: float
    tv: float
    overshoot_pct: float
    settling_time: Optional[float]
    rise_time: Optional[float]

    def to_validated_dataframe(self, method: str = "controller", ms: Optional[float] = None):
        """Converte as métricas em um DataFrame validado pelo contrato BenchmarkMetricsSchema."""
        import pandas as pd

        from src.sim_core.schemas import validate_benchmark_dataframe

        df = pd.DataFrame(
            [
                {
                    "method": method,
                    "iae": self.iae,
                    "itae": self.itae,
                    "ise": self.ise,
                    "tv": self.tv,
                    "overshoot_pct": self.overshoot_pct,
                    "ms": ms if ms is not None else 1.0,
                }
            ]
        )
        return validate_benchmark_dataframe(df)


# %% [Função de Cálculo Numérico das Métricas]
def evaluate_performance(
    t: np.ndarray,
    y: np.ndarray,
    setpoint: np.ndarray,
    u: np.ndarray,
    settling_band: float = 0.02,
    u_init: Optional[float] = None,
    t_step: float = 0.0,
) -> ControlPerformanceMetrics:
    """Calcula os índices quantitativos de rastreamento e esforço de controle.

    Utiliza a regra dos trapézios para integração numérica dos erros temporais
    e busca linear para determinação dos tempos característicos da resposta transitória.

    Args:
        t: Vetor 1D de tempo estritamente monótono crescente [min].
        y: Vetor 1D de valores da variável de processo controlada (PV).
        setpoint: Vetor 1D contendo os valores de referência desejados (SP).
        u: Vetor 1D da ação manipulada entregue pelo elemento final de controle (MV).
        settling_band: Fração de tolerância para o tempo de acomodação (padrão 2% ou 0.02).
        u_init: Actuator position before t[0] (e.g. q_j_ss). When given, the initial jump
            |u[0] - u_init| is included in TV.
        t_step: Instant of the setpoint step [min]. ITAE weights the error by
            max(0, t - t_step), so pre-step error does not inflate it.

    Returns:
        ControlPerformanceMetrics: Estrutura consolidada com todas as métricas calculadas.

    Raises:
        ValueError: Caso os vetores possuam dimensões incompatíveis ou menos de 2 pontos.
    """
    n = len(t)
    if not (len(y) == len(setpoint) == len(u) == n):
        raise ValueError(
            f"Array length mismatch: t={len(t)}, y={len(y)}, sp={len(setpoint)}, u={len(u)}"
        )
    if n < 2:
        raise ValueError("At least 2 points are required to calculate performance metrics")

    dt = np.diff(t)
    error = setpoint - y
    abs_error = np.abs(error)

    # 1. Integração Numérica Trapezoidal dos Índices Temporais de Erro
    iae = float(np.sum(0.5 * (abs_error[:-1] + abs_error[1:]) * dt))
    t_rel = np.maximum(0.0, t - t_step)
    itae = float(np.sum(0.5 * (t_rel[:-1] * abs_error[:-1] + t_rel[1:] * abs_error[1:]) * dt))
    ise = float(np.sum(0.5 * (error[:-1] ** 2 + error[1:] ** 2) * dt))

    # 2. Variação Total (TV) da Ação Manipulada: TV = sum |u_k - u_{k-1}|
    tv = float(np.sum(np.abs(np.diff(u))))
    if u_init is not None:
        tv += float(abs(u[0] - u_init))

    # 3. Cálculo de Sobressinal (Overshoot Percentual)
    sp_final = setpoint[-1]
    y_init = y[0]
    step_amplitude = abs(sp_final - y_init)

    if step_amplitude > 1e-6:
        if sp_final > y_init:
            peak = np.max(y)
            overshoot = max(0.0, (peak - sp_final) / step_amplitude * 100.0)
        else:
            trough = np.min(y)
            overshoot = max(0.0, (sp_final - trough) / step_amplitude * 100.0)
    else:
        overshoot = 0.0

    # 4. Tempo de Acomodação (Settling Time para faixa de +/- 2%)
    settling_threshold = max(settling_band * step_amplitude, 1e-4)
    outside_band_indices = np.where(np.abs(y - sp_final) > settling_threshold)[0]

    if len(outside_band_indices) == 0:
        settling_time = float(t[0])
    elif outside_band_indices[-1] == n - 1:
        # A resposta não permaneceu dentro da faixa até o término da janela temporal
        settling_time = None
    else:
        settling_time = float(t[outside_band_indices[-1] + 1])

    # 5. Tempo de Subida (Rise Time entre 10% e 90% da transição)
    rise_time: Optional[float] = None
    if step_amplitude > 1e-6:
        val_10 = y_init + 0.10 * (sp_final - y_init)
        val_90 = y_init + 0.90 * (sp_final - y_init)

        if sp_final > y_init:
            idx_10 = np.where(y >= val_10)[0]
            idx_90 = np.where(y >= val_90)[0]
        else:
            idx_10 = np.where(y <= val_10)[0]
            idx_90 = np.where(y <= val_90)[0]

        if len(idx_10) > 0 and len(idx_90) > 0 and idx_90[0] >= idx_10[0]:
            rise_time = float(t[idx_90[0]] - t[idx_10[0]])

    logger.debug(
        "Métricas calculadas: IAE=%.3f, ITAE=%.3f, TV=%.3f, Overshoot=%.1f%%",
        iae,
        itae,
        tv,
        overshoot,
    )

    return ControlPerformanceMetrics(
        iae=iae,
        itae=itae,
        ise=ise,
        tv=tv,
        overshoot_pct=float(overshoot),
        settling_time=settling_time,
        rise_time=rise_time,
    )


# %% [Bloco de Execução Interativa / Demonstração no Spyder]
if __name__ == "__main__":
    print("=" * 70)
    print("DEMONSTRAÇÃO INTERATIVA SPYDER 6: Métricas de Controle de Processos")
    print("=" * 70)

    # Criação de resposta sintética subamortecida (segunda ordem) ao degrau de setpoint
    t_demo = np.linspace(0.0, 10.0, 501)
    sp_demo = np.full_like(t_demo, 348.0)  # Degrau de 350 K para 348 K (amplitude = 2 K)
    y_init = 350.0

    # Resposta analítica: y(t) = 348 + 2 * exp(-0.8*t) * (cos(2*t) + 0.4*sin(2*t))
    y_demo = 348.0 + 2.0 * np.exp(-0.8 * t_demo) * (
        np.cos(2.0 * t_demo) + 0.4 * np.sin(2.0 * t_demo)
    )
    # Sinal de controle suave de atuação
    u_demo = 100.0 + 15.0 * (1.0 - np.exp(-t_demo / 1.5))

    metrics = evaluate_performance(
        t=t_demo,
        y=y_demo,
        setpoint=sp_demo,
        u=u_demo,
        settling_band=0.02,
    )

    print("\n[Métricas de Desempenho Calculadas]:")
    print(f"  IAE  (Integral do Erro Absoluto):           {metrics.iae:.4f} K·min")
    print(f"  ITAE (Erro Absoluto Ponderado no Tempo):    {metrics.itae:.4f} K·min²")
    print(f"  ISE  (Integral do Erro Quadrático):         {metrics.ise:.4f} K²·min")
    print(f"  TV   (Variação Total da Ação u):            {metrics.tv:.4f} L/min")
    print(f"  Mp   (Sobressinal Máximo):                  {metrics.overshoot_pct:.2f} %")
    ts_val = f"{metrics.settling_time:.2f} min" if metrics.settling_time else "N/A"
    print(f"  ts   (Tempo de Acomodação +/- 2%):          {ts_val}")
    tr_val = f"{metrics.rise_time:.2f} min" if metrics.rise_time else "N/A"
    print(f"  tr   (Tempo de Subida 10%-90%):             {tr_val}")

    print("\nDemonstração de métricas de controle concluída com sucesso no Spyder 6.")
    print("=" * 70)
