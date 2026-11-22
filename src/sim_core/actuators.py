# %% [Módulo e Importações]
"""Módulo de modelagem de atuadores com saturação estática e dinâmica de slew rate.

Implementa a representação física de uma válvula de controle industrial para
o fluido de resfriamento da camisa do reator CSTR. Modela duas não-linearidades
críticas encontradas na prática industrial:
    1. Saturação de Amplitude (Limites Físicos Absolutos):
       u_min <= u(t) <= u_max
    2. Limitação de Taxa de Variação (Slew Rate Limit):
       |du/dt| <= max_slew_rate
       Limitando o deslocamento máximo da haste da válvula por intervalo dt:
       |Delta u| <= max_slew_rate * dt

Adicionalmente, fornece a sinalização de saturação (flag is_saturated) indispensável
para acionar esquemas de anti-windup condicional (clamping) e recálculo (back-calculation).
"""

import logging
from dataclasses import dataclass
from typing import Tuple

logger = logging.getLogger(__name__)


# %% [Limites Físicos do Atuador]
@dataclass
class ActuatorLimits:
    """Configuração dos limites físicos e dinâmicos da válvula de controle.

    Attributes:
        u_min: Abertura mínima / vazão mínima permitida pelo atuador [L/min].
        u_max: Abertura máxima / vazão máxima permitida pelo atuador [L/min].
        max_slew_rate: Velocidade máxima de deslocamento da haste [L/min^2].
            Caso seja None ou inf, o atuador responde instantaneamente sem restrição de taxa.
        order: "sat_rate" (amplitude, then slew limit on the saturated command; the default) or
            "rate_sat" (slew limit on the raw command, then amplitude; the rate state can pass
            the stops).
    """

    u_min: float = 0.0
    u_max: float = 300.0
    max_slew_rate: float = 100.0
    order: str = "sat_rate"

    def __post_init__(self) -> None:
        """Rejects an unknown composition order."""
        if self.order not in ("sat_rate", "rate_sat"):
            raise ValueError(f"order must be 'sat_rate' or 'rate_sat', got {self.order!r}")


# %% [Simulador de Válvula de Controle Industrial]
class ValveActuator:
    """Simulador de dinâmica de válvula de controle com restrições estáticas e dinâmicas."""

    def __init__(self, limits: ActuatorLimits, initial_position: float = 100.0) -> None:
        """Inicializa o atuador da válvula de controle com seus limites operacionais.

        Args:
            limits: Especificação dos limites físicos de amplitude e slew rate.
            initial_position: Posição inicial / vazão nominal da válvula [L/min].
        """
        self.limits = limits
        self._current_position = float(
            max(self.limits.u_min, min(self.limits.u_max, initial_position))
        )
        self._rate_state = self._current_position  # slew-limiter state of the "rate_sat" order
        logger.info(
            "ValveActuator inicializado com u_min=%.2f, u_max=%.2f, atual=%.2f",
            self.limits.u_min,
            self.limits.u_max,
            self._current_position,
        )

    @property
    def current_position(self) -> float:
        """Retorna a posição física atual / vazão instantânea entregue pela válvula."""
        return self._current_position

    def apply(self, u_desired: float, dt: float) -> Tuple[float, bool]:
        """Aplica a ação de controle desejada considerando saturação e slew rate.

        Etapas de Cálculo Físico:
            1. Saturação de Amplitude:
               u_clamped = clip(u_desired, u_min, u_max)
               Se u_desired != u_clamped, a saturação estática é sinalizada.
            2. Limitação de Taxa (Slew Rate):
               Delta_max = max_slew_rate * dt
               Se |u_clamped - u_atual| > Delta_max, a velocidade máxima física
               é imposta e a flag de saturação dinâmica é ativada.
            3. Atualização de Estado:
               u_atualizado é retido para o próximo passo temporal.

        Args:
            u_desired: Ação de controle requisitada pelo controlador [L/min].
            dt: Intervalo de amostragem ou passo de integração temporal [min].

        Returns:
            Tuple[float, bool]:
                - actual_u: Vazão real restringida aplicada à planta [L/min].
                - is_saturated: True se a requisição sofreu saturação estática ou dinâmica.

        Raises:
            ValueError: Se o passo de amostragem dt for menor ou igual a zero.
        """
        u_actual, is_saturated = self.preview(u_desired, dt)
        if self.limits.order == "rate_sat":
            self._rate_state = self._rate_limited(u_desired, self._rate_state, dt)
        self._current_position = u_actual
        return self._current_position, is_saturated

    def _rate_limited(self, target: float, state: float, dt: float) -> float:
        """One slew-limited move of `state` towards `target`."""
        if self.limits.max_slew_rate is None or self.limits.max_slew_rate <= 0:
            return target
        d = self.limits.max_slew_rate * dt
        return state + min(max(target - state, -d), d)

    def preview(self, u_desired: float, dt: float) -> Tuple[float, bool]:
        """What `apply` would return for `u_desired`, without moving the valve.

        Args:
            u_desired: Ação de controle requisitada pelo controlador [L/min].
            dt: Intervalo de amostragem [min].

        Returns:
            Tuple[float, bool]: posição limitada (amplitude, depois slew rate) e a flag de corte.

        Raises:
            ValueError: Se o passo de amostragem dt for menor ou igual a zero.
        """
        if dt <= 0:
            raise ValueError(f"O passo temporal dt deve ser positivo, obtido {dt}")

        if self.limits.order == "rate_sat":
            r = self._rate_limited(u_desired, self._rate_state, dt)
            u_actual = min(max(r, self.limits.u_min), self.limits.u_max)
            return u_actual, u_actual != u_desired

        is_saturated = False

        # 1. Aplicação de saturação estática (clamping de amplitude)
        if u_desired > self.limits.u_max:
            u_clamped = self.limits.u_max
            is_saturated = True
        elif u_desired < self.limits.u_min:
            u_clamped = self.limits.u_min
            is_saturated = True
        else:
            u_clamped = u_desired

        # 2. Aplicação de saturação dinâmica de taxa (slew-rate limiting)
        if self.limits.max_slew_rate is not None and self.limits.max_slew_rate > 0:
            delta_max = self.limits.max_slew_rate * dt
            delta_req = u_clamped - self._current_position
            if abs(delta_req) > delta_max:
                u_actual = self._current_position + (delta_max if delta_req > 0 else -delta_max)
                is_saturated = True
            else:
                u_actual = u_clamped
        else:
            u_actual = u_clamped

        return u_actual, is_saturated

    def reset(self, position: float) -> None:
        """Reinicia a posição interna da válvula para um valor pré-especificado.

        Garante que a nova posição respeite rigorosamente os limites [u_min, u_max].

        Args:
            position: Posição-alvo para reset da válvula [L/min].
        """
        self._current_position = float(max(self.limits.u_min, min(self.limits.u_max, position)))
        self._rate_state = self._current_position
        logger.debug("ValveActuator reiniciado para %.2f", self._current_position)


# %% [Bloco de Execução Interativa / Demonstração no Spyder]
if __name__ == "__main__":
    print("=" * 70)
    print("DEMONSTRAÇÃO INTERATIVA SPYDER 6: Atuador Não-Linear de Válvula")
    print("=" * 70)

    # Configuração com limites físicos e slew rate de 60 L/min^2
    limits = ActuatorLimits(u_min=10.0, u_max=200.0, max_slew_rate=60.0)
    valve = ValveActuator(limits=limits, initial_position=50.0)
    dt_step = 0.5  # minutos (máximo deslocamento por passo = 60 * 0.5 = 30 L/min)

    print(f"Posição inicial da válvula: {valve.current_position:.1f} L/min")
    print(
        f"Limites: [{limits.u_min}, {limits.u_max}] L/min | Slew: {limits.max_slew_rate} L/min²\n"
    )

    # Aplicação de comando em degrau para 250 L/min (ultrapassa u_max e testa slew rate)
    u_req = 250.0
    print(f"Requisitando comando u_desired = {u_req:.1f} L/min (degrau acentuado):")

    for step in range(1, 8):
        u_out, sat = valve.apply(u_desired=u_req, dt=dt_step)
        print(
            f"  Passo {step} (t = {step * dt_step:.1f} min): "
            f"u_real = {u_out:.2f} L/min | Saturado: {sat}"
        )

    print("\nDemonstração do atuador concluída com sucesso no Spyder 6.")
    print("=" * 70)


class StictionValve:
    """Two-parameter stiction model of Choudhury, Thornhill and Shah (Control Eng. Pract., 2005).

    Input: the valve command u (here the controller's u_act, after amplitude and slew limits);
    output: the stem position x. S is the deadband plus stickband and J the slip jump, both in
    the units of u. When the command reverses, the valve sticks until |u - u_s| > S; when the
    command rests and then moves on in the same direction, until |u - u_s| > J; on breaking free
    the position jumps to u - sign(u - u_s) (S - J)/2 and then follows u with that offset. The
    valve starts at rest, treated as a reversal (band S). The position is kept inside the stops.
    """

    def __init__(self, s_band: float, j_jump: float, u0: float, limits: ActuatorLimits) -> None:
        """Valve at rest at u0, stuck."""
        self.s, self.j, self.limits = s_band, j_jump, limits
        self.x = self.u_prev = self.u_s = float(u0)
        self.direction, self.stuck, self.reversal = 0.0, True, True

    def apply(self, u: float) -> float:
        """Position for the new command u (one sample)."""
        du = float(u) - self.u_prev
        d = float((du > 0) - (du < 0))
        if d == 0.0 and not self.stuck:
            self.stuck, self.u_s, self.reversal = True, self.u_prev, False
        elif d != 0.0 and self.direction != 0.0 and d != self.direction and not self.stuck:
            self.stuck, self.u_s, self.reversal = True, self.u_prev, True
        elif d != 0.0 and self.direction != 0.0 and d != self.direction and self.stuck:
            self.u_s, self.reversal = self.u_prev, True  # reversal while stuck: new reference
        if self.stuck:
            if abs(u - self.u_s) > (self.s if self.reversal else self.j):
                self.stuck = False
                self.x = u - (1.0 if u > self.u_s else -1.0) * (self.s - self.j) / 2.0
        elif d != 0.0:
            self.x = u - d * (self.s - self.j) / 2.0
        self.x = min(max(self.x, self.limits.u_min), self.limits.u_max)
        if d != 0.0:
            self.direction = d
        self.u_prev = float(u)
        return self.x
