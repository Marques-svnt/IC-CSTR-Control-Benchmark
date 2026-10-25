"""Shell-and-tube heat exchanger: well-mixed shell and a two-cell tube (second test plant, v9).

Built for the anti-windup study as a reverse-acting, open-loop-stable plant without Arrhenius
kinetics; it is not a published benchmark. More coolant flow q_c lowers the tube outlet
temperature T_2. The shell is one well-mixed state T_c; the tube is two cells in series (not a
counter-current exchanger). The output is T_2 seen through a pure transport delay.

    dT1/dt = (2 qp/Vp)(Tp_in - T1) - [UA(qc)/2] / [rho_p Cp_p Vp/2] (T1 - Tc)
    dT2/dt = (2 qp/Vp)(T1 - T2)    - [UA(qc)/2] / [rho_p Cp_p Vp/2] (T2 - Tc)
    dTc/dt = (qc/Vc)(Tc_in - Tc) + UA(qc)/(rho_c Cp_c Vc) ((T1 + T2)/2 - Tc)
    UA(qc) = UA0 (max(qc, 5)/qc_ss)^0.8
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import fsolve


@dataclass(frozen=True)
class HeatExchangerParameters:
    """Nominal parameters (L, min, K, cal)."""

    v_p: float = 100.0
    v_c: float = 40.0
    q_p: float = 100.0
    t_p_in: float = 390.0
    t_c_in: float = 300.0
    rho_cp_p: float = 500.0
    rho_cp_c: float = 500.0
    ua0: float = 6.0e4
    q_c_ss: float = 100.0
    delay: float = 0.20  # min, transport delay on the outlet measurement


class HeatExchanger:
    """Three-state model; state x = [T1, T2, Tc] in K, input q_c in L/min."""

    def __init__(self, params: HeatExchangerParameters | None = None) -> None:
        self.p = params or HeatExchangerParameters()

    def ua(self, q_c: float) -> float:
        """Coolant-side film coefficient grows with flow; floor at 5 L/min."""
        return self.p.ua0 * (max(q_c, 5.0) / self.p.q_c_ss) ** 0.8

    def derivatives(self, x: np.ndarray, q_c: float) -> np.ndarray:
        """Right-hand side of the three balances."""
        p, (t1, t2, tc) = self.p, x
        ua = self.ua(q_c)
        cell = (ua / 2.0) / (p.rho_cp_p * p.v_p / 2.0)
        return np.array([
            (2.0 * p.q_p / p.v_p) * (p.t_p_in - t1) - cell * (t1 - tc),
            (2.0 * p.q_p / p.v_p) * (t1 - t2) - cell * (t2 - tc),
            (q_c / p.v_c) * (p.t_c_in - tc) + ua / (p.rho_cp_c * p.v_c) * ((t1 + t2) / 2.0 - tc),
        ])

    def steady_state(self, q_c: float) -> np.ndarray:
        """Equilibrium for a constant coolant flow."""
        x0 = np.array([370.0, 355.0, 330.0])
        x, _, ok, msg = fsolve(lambda x: self.derivatives(x, q_c), x0, full_output=True, xtol=1e-12)
        if ok != 1:
            raise RuntimeError(f"steady state not found at q_c = {q_c}: {msg}")
        return x

    def jacobian(self, x: np.ndarray, q_c: float, h: float = 1e-6) -> np.ndarray:
        """State Jacobian by central differences (the model is smooth in x)."""
        return np.column_stack([
            (self.derivatives(x + h * e, q_c) - self.derivatives(x - h * e, q_c)) / (2.0 * h)
            for e in np.eye(3)
        ])

    def step(self, x: np.ndarray, q_c: float, dt: float, substeps: int = 4) -> np.ndarray:
        """Advances the state over one sample with constant input (classical RK4, dt/substeps).

        shortcut: fixed-step RK4 (h = 0.005 min against time constants >= 0.16 min); switch to an
        adaptive solver if a stiffer parameter set is used.
        """
        h = dt / substeps
        for _ in range(substeps):
            k1 = self.derivatives(x, q_c)
            k2 = self.derivatives(x + 0.5 * h * k1, q_c)
            k3 = self.derivatives(x + 0.5 * h * k2, q_c)
            k4 = self.derivatives(x + h * k3, q_c)
            x = x + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        return x
