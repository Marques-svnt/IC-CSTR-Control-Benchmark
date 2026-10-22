# %% [Módulo e Importações]
"""Controlador PID discreto de padrão industrial com estratégias avançadas de anti-windup.

Implementa a formulação paralela do algoritmo PID com recursos realistas indispensáveis
em plantas químicas de processo:
    1. Ação Proporcional:
       P_k = K_p * e_k
    2. Ação Derivativa com Filtro de Primeira Ordem (N-filter):
       tau_f = T_d / N, com discretização passa-baixas:
       D_f[k] = (1 - alpha) * D_f[k-1] + alpha * d(in)/dt
       Suporta Derivada sobre a Medição (-d(PV)/dt) para eliminar o indesejado
       efeito de "derivative kick" (picos na haste da válvula) durante mudanças de setpoint.
    3. Ação Integral com Integração Trapezoidal Discreta:
       Delta_I = (K_p / T_i) * 0.5 * (e_k + e_{k-1}) * dt
    4. Esquemas Comparativos de Anti-Windup:
       - Condicional (Clamping): Congela a integração caso a saída esteja saturada
         e o erro atue na mesma direção da saturação.
       - Recálculo (Back-Calculation): Realimenta a diferença entre o comando
         restringido do atuador e o comando ideal não-restringido:
         Delta_I += [(u_real - u_uncon) / T_t] * dt, com T_t = sqrt(T_i * T_d).
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

import numpy as np

from src.sim_core.actuators import ActuatorLimits, ValveActuator

logger = logging.getLogger(__name__)


# %% [Enumerações e Estrutura de Ganhos PID]
class AntiWindupMethod(str, Enum):
    """Mecanismos suportados para mitigação e prevenção de saturação integral (windup)."""

    NONE = "none"
    CLAMPING = "clamping"
    BACK_CALCULATION = "back_calculation"
    # Ablation only: amplitude-only, sign-blind textbook rule (ignores slew-rate cuts and Kp < 0)
    CLAMPING_NAIVE = "clamping_naive"


@dataclass
class PIDGains:
    """Parâmetros e constantes de sintonia do controlador PID.

    Attributes:
        kp: Ganho proporcional (adimensional ou [L/(min*K)]).
        ti: Constante de tempo integral [min]. Deve ser estritamente positiva.
        td: Constante de tempo derivativa [min]. Não-negativa.
        n_filter: Coeficiente de filtragem derivativa (tau_f = td / n_filter). Tipicamente 5 a 20.
        tt: Constante de tempo de rastreamento para back-calculation [min].
            Caso seja None, adota automaticamente sqrt(ti * td) se td > 0, ou ti caso contrário.
        beta: Setpoint weight on the proportional path, in [0, 1] (1.0 = 1-DOF).
        gamma: Setpoint weight on the derivative path, in [0, 1] (0.0 = derivative on PV).
    """

    kp: float
    ti: float
    td: float = 0.0
    n_filter: float = 10.0
    tt: Optional[float] = None
    beta: float = 1.0
    gamma: float = 0.0

    def __post_init__(self) -> None:
        """Validação física de consistência dos parâmetros de sintonia."""
        if self.ti <= 0.0:
            raise ValueError(f"A constante integral ti deve ser positiva, obtido {self.ti}")
        if self.td < 0.0:
            raise ValueError(f"A constante derivativa td não pode ser negativa, obtido {self.td}")
        if self.n_filter <= 0.0:
            raise ValueError(
                f"O coeficiente de filtro n_filter deve ser positivo, obtido {self.n_filter}"
            )
        for name in ("beta", "gamma"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must lie in [0, 1], got {getattr(self, name)}")
        if self.tt is None:
            self.tt = np.sqrt(self.ti * self.td) if self.td > 0.0 else self.ti


# %% [Controlador PID Paralelo Industrial com Anti-Windup]
class PIDController:
    """Controlador PID Paralelo Discreto com anti-windup e filtragem derivativa."""

    def __init__(
        self,
        gains: PIDGains,
        actuator_limits: Optional[ActuatorLimits] = None,
        anti_windup: AntiWindupMethod = AntiWindupMethod.CLAMPING,
        derivative_on_measurement: bool = True,
        u_bias: float = 100.0,
        y_ss: Optional[float] = None,
    ) -> None:
        """Inicializa o controlador PID e instancia o atuador de válvula integrado.

        Args:
            gains: Especificação completa de ganhos e filtros (kp, ti, td, n_filter, tt).
            actuator_limits: Limites físicos de saturação e velocidade (slew rate).
            anti_windup: Algoritmo de anti-windup ('none', 'clamping', 'back_calculation').
            derivative_on_measurement: Se True, avalia a derivada sobre a medição (-dPV/dt)
                prevenindo o derivative kick. Se False, avalia sobre o sinal de erro (de/dt).
            u_bias: Valor nominal do sinal de controle em regime permanente (feedforward bias).
            y_ss: Nominal steady-state output used as the origin of the 2-DOF deviation
                variables. If None, the first measurement seen by `compute` is captured.
        """
        self.gains = gains
        self.limits = actuator_limits or ActuatorLimits()
        self.valve = ValveActuator(limits=self.limits, initial_position=u_bias)
        self.anti_windup = anti_windup
        self.derivative_on_measurement = derivative_on_measurement
        self.u_bias = float(u_bias)
        self._y_ss_fixed = y_ss
        self._y_ss: Optional[float] = y_ss

        # Memória de estados internos para execução recursiva discreta
        self._integral_state: float = 0.0
        self._prev_error: float = 0.0
        self._prev_error_d: Optional[float] = None
        self._prev_measurement: Optional[float] = None
        self._filtered_deriv_state: float = 0.0
        self._last_u_unconstrained: float = self.u_bias
        self._last_u_applied: float = self.u_bias
        self._is_saturated: bool = False

        logger.info(
            "PIDController inicializado: Kp=%.3f, Ti=%.3f, Td=%.3f, AntiWindup=%s",
            self.gains.kp,
            self.gains.ti,
            self.gains.td,
            self.anti_windup.value,
        )

    def reset(self, initial_measurement: float, initial_u: Optional[float] = None) -> None:
        """Reinicia os estados internos do controlador garantindo inicialização suave (bumpless).

        Args:
            initial_measurement: Valor medido inicial da variável de processo (PV).
            initial_u: Saída de controle inicial desejada. Se None, adota u_bias.
        """
        u_init = initial_u if initial_u is not None else self.u_bias
        self.valve.reset(u_init)
        self._integral_state = 0.0
        self._prev_error = 0.0
        self._prev_error_d = None
        self._prev_measurement = float(initial_measurement)
        self._filtered_deriv_state = 0.0
        self._last_u_unconstrained = u_init
        self._last_u_applied = u_init
        self._is_saturated = False
        self._y_ss = self._y_ss_fixed
        logger.debug("PIDController reiniciado com PV inicial = %.2f", initial_measurement)

    def compute(
        self,
        setpoint: float,
        measurement: float,
        dt: float,
    ) -> Tuple[float, dict[str, float]]:
        """Calcula a ação de controle discreta u_k para o período de amostragem atual.

        Sequência de Execução Algorítmica:
            1. Erro de Controle:
               e_k = SP - PV
            2. Termo Proporcional:
               P = K_p * e_k
            3. Termo Derivativo com Filtro Passa-Baixas (N-filter):
               alpha = dt / (tau_f + dt), tau_f = T_d / N
               D = K_p * T_d * D_filtrado
            4. Termo Integral com Estratégia de Anti-Windup:
               - Se Clamping: interrompe integração se a saída estiver saturada e
                 o erro mantiver a tendência de saturação.
               - Se Back-Calculation: injeta termo corretivo proporcional a (u_real - u_uncon).
            5. Cálculo da Saída Não-Restringida e Restringimento pelo Atuador:
               u_uncon = u_bias + P + I + D
               (u_real, is_sat) = valve.apply(u_uncon, dt)

        Args:
            setpoint: Valor de referência desejado (SP).
            measurement: Valor medido instantâneo da variável controlada (PV).
            dt: Período de amostragem discreto [min].

        Returns:
            Tuple[float, dict[str, float]]:
                - u_actual: Ação de controle física efetivamente aplicada [L/min].
                - diag: Dicionário diagnóstico contendo as parcelas ('p', 'i', 'd',
                        'u_unconstrained', 'is_saturated').

        Raises:
            ValueError: Se o passo dt for menor ou igual a zero.
        """
        if dt <= 0.0:
            raise ValueError(f"O período de amostragem dt deve ser positivo, obtido {dt}")

        error = setpoint - measurement  # integral error e_i (always 1-DOF)

        if self._prev_measurement is None:
            self._prev_measurement = measurement
        if self._y_ss is None:
            self._y_ss = measurement

        # 1. Parcela Proporcional 2-DOF: e_p = beta*(SP - y_ss) - (PV - y_ss)
        dy_sp = setpoint - self._y_ss
        dy = measurement - self._y_ss
        p_term = self.gains.kp * (self.gains.beta * dy_sp - dy)
        # Derivative path e_d = gamma*dSP - dPV (gamma=1 when differentiating the error)
        gamma = self.gains.gamma if self.derivative_on_measurement else 1.0
        error_d = gamma * dy_sp - dy
        if self._prev_error_d is None:
            # Bumpless start: assume the previous setpoint equalled the previous PV
            self._prev_error_d = (gamma - 1.0) * (self._prev_measurement - self._y_ss)

        # 2. Parcela Derivativa com Filtro de Primeira Ordem (N-filter)
        if self.gains.td > 0.0:
            tau_f = self.gains.td / self.gains.n_filter
            alpha = dt / (tau_f + dt)

            # gamma=0 -> derivative on measurement (no kick); gamma=1 -> de/dt
            d_input = (error_d - self._prev_error_d) / dt

            # Atualização do estado do filtro passa-baixas recursivo
            self._filtered_deriv_state = (
                (1.0 - alpha) * self._filtered_deriv_state + alpha * d_input
            )
            d_term = self.gains.kp * self.gains.td * self._filtered_deriv_state
        else:
            d_term = 0.0

        # 3. Atualização da Parcela Integral com Condições de Anti-Windup
        i_gain = self.gains.kp / self.gains.ti
        e_trap = 0.5 * (error + self._prev_error)
        should_integrate = True

        if self.anti_windup == AntiWindupMethod.CLAMPING and self._is_saturated:
            # Clamping direcional: congela se o incremento integral trapezoidal empurra na direção
            # da saturação (amplitude ou slew rate); K_p < 0 inverte o sinal de i_gain * e_trap
            sat_excess = self._last_u_unconstrained - self._last_u_applied
            if sat_excess * (i_gain * e_trap) > 0.0:
                should_integrate = False

        if self.anti_windup == AntiWindupMethod.CLAMPING_NAIVE and self._is_saturated:
            if (self._last_u_unconstrained >= self.limits.u_max and error > 0.0) or (
                self._last_u_unconstrained <= self.limits.u_min and error < 0.0
            ):
                should_integrate = False

        if should_integrate:
            # Integração trapezoidal discreta de maior precisão
            delta_i = i_gain * e_trap * dt
            if self.anti_windup == AntiWindupMethod.BACK_CALCULATION:
                # Correção por recálculo: rastreia a discrepância entre saída real e calculada
                tracking_error = self._last_u_applied - self._last_u_unconstrained
                tt = self.gains.tt or self.gains.ti
                delta_i += (tracking_error / tt) * dt

            self._integral_state += delta_i

        i_term = self._integral_state

        # 4. Cálculo da Ação Não-Restringida (u_unconstrained)
        u_unconstrained = self.u_bias + p_term + i_term + d_term

        # 5. Restringimento Dinâmico pelo Atuador Físico (saturação e slew rate)
        u_actual, is_saturated = self.valve.apply(u_unconstrained, dt=dt)

        # Atualização da memória histórica para a próxima iteração
        self._last_u_unconstrained = u_unconstrained
        self._last_u_applied = u_actual
        self._is_saturated = is_saturated
        self._prev_error = error
        self._prev_error_d = error_d
        self._prev_measurement = measurement

        diag = {
            "p": float(p_term),
            "i": float(i_term),
            "d": float(d_term),
            "u_unconstrained": float(u_unconstrained),
            "is_saturated": 1.0 if is_saturated else 0.0,
        }

        return u_actual, diag


# %% [Bloco de Execução Interativa / Demonstração no Spyder]
if __name__ == "__main__":
    print("=" * 70)
    print("DEMONSTRAÇÃO INTERATIVA SPYDER 6: Controlador PID Industrial")
    print("=" * 70)

    # 1. Configuração dos ganhos de sintonia (processo exotérmico -> Kp < 0 para ação reversa)
    gains_demo = PIDGains(kp=-6.5, ti=1.5, td=0.25, n_filter=10.0)
    limits_demo = ActuatorLimits(u_min=0.0, u_max=250.0, max_slew_rate=80.0)

    pid = PIDController(
        gains=gains_demo,
        actuator_limits=limits_demo,
        anti_windup=AntiWindupMethod.CLAMPING,
        derivative_on_measurement=True,
        u_bias=100.0,
    )

    # 2. Inicialização bumpless com medição inicial T = 350 K
    t_sp = 348.0   # Setpoint reduz em 2 K (requer mais refrigeração q_j)
    t_meas = 350.0 # Medição inicial
    pid.reset(initial_measurement=t_meas, initial_u=100.0)

    print(f"Ganhos: Kp={gains_demo.kp:.2f}, Ti={gains_demo.ti:.2f} min, "
          f"Td={gains_demo.td:.2f} min")
    print(f"Anti-Windup: {pid.anti_windup.value} | "
          f"Limites: [{limits_demo.u_min}, {limits_demo.u_max}] L/min")
    print(f"\nAplicando degrau de setpoint: SP = {t_sp:.1f} K (PV inicial = {t_meas:.1f} K)\n")

    # 3. Execução de passos de controle com dt = 0.1 min
    dt_step = 0.1
    for step in range(1, 6):
        u_cmd, diag_info = pid.compute(setpoint=t_sp, measurement=t_meas, dt=dt_step)
        print(
            f"Passo {step:02d} | P = {diag_info['p']:+6.2f} | "
            f"I = {diag_info['i']:+6.2f} | D = {diag_info['d']:+6.2f} | "
            f"u_uncon = {diag_info['u_unconstrained']:6.2f} | "
            f"u_real = {u_cmd:6.2f} L/min | Sat: {bool(diag_info['is_saturated'])}"
        )
        # Emula resposta parcial do processo (PV se aproximando suavemente do SP)
        t_meas += 0.2 * (t_sp - t_meas)

    print("\nDemonstração do controlador PID concluída com sucesso no Spyder 6.")
    print("=" * 70)
