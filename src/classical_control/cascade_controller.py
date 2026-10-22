# %% [Módulo e Importações]
"""Controlador em cascata industrial para reator CSTR exotérmico (T -> T_j -> q_j).

Implementa a arquitetura de controle em cascata clássica da engenharia química:
    - Controlador Primário (Mestre):
      Mede a temperatura do reator T (PV_master) e compara com o setpoint desejado T_sp.
      Calcula a temperatura de referência requerida para a jaqueta de resfriamento T_j,sp.
    - Controlador Secundário (Escravo):
      Mede a temperatura real da jaqueta T_j (PV_slave) e compara com T_j,sp.
      Atua diretamente na válvula de vazão de resfriamento q_j sujeita aos limites
      físicos de saturação de amplitude [u_min, u_max] e taxa de posicionamento (slew-rate).

Ambos os controladores incorporam proteção anti-windup por travamento condicional (clamping)
e filtragem derivativa no controlador primário.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

from src.classical_control.pid_controller import (
    AntiWindupMethod,
    PIDController,
    PIDGains,
)
from src.sim_core.actuators import ActuatorLimits

logger = logging.getLogger(__name__)


# %% [Dataclass de Ganhos da Cascata]
@dataclass
class CascadePIDGains:
    """Conjunto estruturado de ganhos para as malhas mestre e escrava da cascata.

    Attributes:
        master_gains: Ganhos do controlador primário (temperatura do reator T -> T_j,sp).
        slave_gains: Ganhos do controlador secundário (temperatura da jaqueta T_j -> q_j).
        t_j_min: Limite inferior de saturação para o setpoint da camisa [K]. Padrão: 300.0 K (T_jf).
        t_j_max: Limite superior de saturação para o setpoint da camisa [K]. Padrão: 380.0 K.
    """

    master_gains: PIDGains
    slave_gains: PIDGains
    t_j_min: float = 300.0
    t_j_max: float = 380.0


# %% [Classe do Controlador em Cascata]
class CascadePIDController:
    """Controlador em cascata desacoplado mestre-escravo para controle térmico do CSTR."""

    def __init__(
        self,
        gains: CascadePIDGains,
        actuator_limits: Optional[ActuatorLimits] = None,
        anti_windup: AntiWindupMethod = AntiWindupMethod.CLAMPING,
        u_bias: float = 100.0,
        t_j_bias: float = 348.33,
    ) -> None:
        """Inicializa as malhas mestre e escrava com seus respectivos parâmetros.

        Args:
            gains: Dataclass contendo os ganhos de ambas as malhas e limites de T_j,sp.
            actuator_limits: Limites físicos de amplitude e slew-rate da válvula de resfriamento.
            anti_windup: Método de prevenção de saturação integral.
            u_bias: Vazão nominal de resfriamento q_j,ss [L/min].
            t_j_bias: Temperatura nominal de resfriamento da camisa T_j,ss [K].
        """
        self.gains = gains
        self.u_bias = u_bias
        self.t_j_bias = t_j_bias
        self.t_j_min = gains.t_j_min
        self.t_j_max = gains.t_j_max

        # Controlador Mestre: saída é T_j,sp (delta em relação a t_j_bias)
        # Como o erro do mestre é e_1 = T_sp - T, se o reator esquenta (T > T_sp, e_1 < 0),
        # queremos resfriar a jaqueta, logo T_j,sp deve diminuir: K_p,master > 0.
        master_limits = ActuatorLimits(
            u_min=self.t_j_min,
            u_max=self.t_j_max,
            max_slew_rate=100.0,  # Dinâmica de setpoint de temperatura (K/min)
        )
        self.master_controller = PIDController(
            gains=gains.master_gains,
            actuator_limits=master_limits,
            anti_windup=anti_windup,
            derivative_on_measurement=True,
            u_bias=t_j_bias,
        )

        # Controlador Escravo: saída é q_j atuando sobre a válvula física
        # Erro do escravo é e_2 = T_j,sp - T_j. Se T_j > T_j,sp (e_2 < 0),
        # a jaqueta está muito quente, logo a vazão de refrigerante q_j deve AUMENTAR.
        # Portanto, o ganho de controle K_p,slave deve ser NEGATIVO.
        self.slave_controller = PIDController(
            gains=gains.slave_gains,
            actuator_limits=actuator_limits or ActuatorLimits(),
            anti_windup=anti_windup,
            derivative_on_measurement=True,
            u_bias=u_bias,
        )

    def reset(
        self,
        initial_t: Optional[float] = None,
        initial_tj: Optional[float] = None,
        initial_u: Optional[float] = None,
    ) -> None:
        """Reinicia o estado interno dos integradores de ambas as malhas."""
        t_init = initial_t if initial_t is not None else 396.65
        tj_init = initial_tj if initial_tj is not None else self.t_j_bias
        u_init = initial_u if initial_u is not None else self.u_bias

        self.master_controller.reset(initial_measurement=t_init, initial_u=tj_init)
        self.slave_controller.reset(initial_measurement=tj_init, initial_u=u_init)

    def compute(
        self,
        t_sp: float,
        t_pv: float,
        tj_pv: float,
        dt: float,
    ) -> Tuple[float, Dict[str, Any]]:
        """Calcula o comando da cascata executando as malhas mestre e escrava.

        Args:
            t_sp: Setpoint desejado da temperatura do reator [K].
            t_pv: Medição atual da temperatura do reator [K].
            tj_pv: Medição atual da temperatura da jaqueta [K].
            dt: Período de discretização / amostragem [min].

        Returns:
            Tuple[float, Dict[str, Any]]:
                - q_j_applied: Vazão real aplicada à válvula após limites físicos [L/min].
                - diagnostics: Dicionário detalhado contendo T_j,sp e variáveis de estado.
        """
        # 1. Executa o controlador Mestre (Reactor Temperature Loop)
        tj_sp_cmd, master_diag = self.master_controller.compute(
            setpoint=t_sp,
            measurement=t_pv,
            dt=dt,
        )
        # Garante saturação física em T_j,sp
        tj_sp_clamped = float(np.clip(tj_sp_cmd, self.t_j_min, self.t_j_max))

        # 2. Executa o controlador Escravo (Jacket Temperature Loop)
        q_j_applied, slave_diag = self.slave_controller.compute(
            setpoint=tj_sp_clamped,
            measurement=tj_pv,
            dt=dt,
        )

        diagnostics: Dict[str, Any] = {
            "t_sp": t_sp,
            "t_pv": t_pv,
            "tj_sp": tj_sp_clamped,
            "tj_pv": tj_pv,
            "q_j_applied": q_j_applied,
            "q_j_unconstrained": slave_diag.get("u_unconstrained", q_j_applied),
            "master_error": t_sp - t_pv,
            "slave_error": tj_sp_clamped - tj_pv,
            "master_is_saturated": master_diag.get("is_saturated", False),
            "slave_is_saturated": slave_diag.get("is_saturated", False),
        }

        return q_j_applied, diagnostics
