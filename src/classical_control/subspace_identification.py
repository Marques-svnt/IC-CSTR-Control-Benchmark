"""Subspace (N4SID, MOESP) and ARMAX system identification for CSTR via SIPPY.

Provides persistent excitation (PRBS symmetric and asymmetric) and multi-step
identification benchmarks comparing subspace state-space models (order n=2, 3)
and ARMAX against first-order FOPTD models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np
import sippy_unipi as sippy

from src.classical_control.foptd import FOPTDModel

logger = logging.getLogger(__name__)

IdentificationMethod = Literal["N4SID", "MOESP", "ARMAX", "OE"]


@dataclass(frozen=True)
class SubspaceIdentificationResult:
    """Identified discrete-time model and fit metrics from SIPPY.

    Attributes:
        method: Identification algorithm identifier ('N4SID', 'MOESP', 'ARMAX', 'OE').
        order: Model state-space order or polynomial degree.
        y_hat: Predicted output trajectory in engineering units [K].
        rmse: Root Mean Square Error [K].
        nrmse_fit_pct: Normalized NRMSE fit percentage in [0, 100] %.
        A: Discrete state matrix A (if state-space model).
        B: Discrete input matrix B (if state-space model).
        C: Discrete output matrix C (if state-space model).
        D: Discrete feedthrough matrix D (if state-space model).
    """

    method: str
    order: int
    y_hat: np.ndarray
    rmse: float
    nrmse_fit_pct: float
    A: Optional[np.ndarray] = None
    B: Optional[np.ndarray] = None
    C: Optional[np.ndarray] = None
    D: Optional[np.ndarray] = None


def generate_prbs_signal(
    n_samples: int,
    u_nominal: float = 100.0,
    delta_plus: float = 15.0,
    delta_minus: float = 15.0,
    min_switch_steps: int = 8,
    seed: int = 42,
) -> np.ndarray:
    """Generates a symmetric or asymmetric Pseudo-Random Binary Sequence (PRBS).

    Supports asymmetric thermal excitation around the nominal coolant flow rate
    `u_nominal` to capture Arrhenius non-linear gain asymmetry in the CSTR.

    Args:
        n_samples: Total number of discrete time samples.
        u_nominal: Baseline coolant flow rate [L/min].
        delta_plus: Positive perturbation amplitude (+Delta q_j) [L/min].
        delta_minus: Negative perturbation amplitude (-Delta q_j) [L/min].
        min_switch_steps: Minimum holding period (in samples) between binary transitions.
        seed: Random generator seed for reproducibility.

    Returns:
        1D NumPy array of shape (n_samples,) with coolant flow rate trajectory [L/min].

    Raises:
        ValueError: If `n_samples` < 2 or amplitudes are negative.
    """
    if n_samples < 2:
        raise ValueError(f"n_samples must be >= 2, got {n_samples}")
    if delta_plus < 0.0 or delta_minus < 0.0:
        raise ValueError("PRBS amplitudes delta_plus and delta_minus must be non-negative.")

    rng = np.random.default_rng(seed)
    signal = np.full(n_samples, u_nominal, dtype=np.float64)
    hold = max(1, int(min_switch_steps))

    idx = 0
    state_high = True
    while idx < n_samples:
        # Randomize holding duration between 1x and 3x min_switch_steps
        duration = int(rng.integers(hold, 3 * hold + 1))
        end_idx = min(n_samples, idx + duration)
        signal[idx:end_idx] = u_nominal + delta_plus if state_high else u_nominal - delta_minus
        if rng.random() < 0.65:
            state_high = not state_high
        idx = end_idx

    return np.clip(signal, 0.0, 300.0)


def identify_subspace_or_armax(
    u: np.ndarray,
    y: np.ndarray,
    method: IdentificationMethod = "N4SID",
    order: int = 2,
    u_baseline: Optional[float] = None,
    y_baseline: Optional[float] = None,
) -> SubspaceIdentificationResult:
    """Identifies a multi-step linear model via SIPPY (N4SID, MOESP, ARMAX, OE).

    Args:
        u: 1D input excitation sequence [L/min].
        y: 1D measured process output sequence [K].
        method: SIPPY identification method ('N4SID', 'MOESP', 'ARMAX', 'OE').
        order: System order (typically 2 or 3 for CSTR + jacket dynamics).
        u_baseline: Nominal operating input for deviation variable centering.
        y_baseline: Nominal operating output for deviation variable centering.

    Returns:
        SubspaceIdentificationResult containing predicted trajectory, RMSE, NRMSE fit,
        and state-space matrices (when applicable).
    """
    u_arr = np.asarray(u, dtype=np.float64).ravel()
    y_arr = np.asarray(y, dtype=np.float64).ravel()
    if len(u_arr) != len(y_arr) or len(u_arr) < 15:
        raise ValueError("Input u and output y must have equal length >= 15 samples.")

    u0 = float(u_arr[0]) if u_baseline is None else float(u_baseline)
    y0 = float(y_arr[0]) if y_baseline is None else float(y_baseline)

    du = u_arr - u0
    dy = y_arr - y0

    if method in ("N4SID", "MOESP"):
        sys_id = sippy.system_identification(
            dy,
            du,
            method,
            SS_fixed_order=order,
            SS_f=max(order + 2, 5),
            SS_p=max(order + 2, 5),
        )
        A_mat = np.asarray(sys_id.A, dtype=np.float64)
        B_mat = np.asarray(sys_id.B, dtype=np.float64)
        C_mat = np.asarray(sys_id.C, dtype=np.float64)
        D_mat = np.asarray(sys_id.D, dtype=np.float64)
        if hasattr(sys_id, "Yid"):
            dy_hat = np.asarray(sys_id.Yid, dtype=np.float64).ravel()
        else:
            n_pts = len(du)
            x0_est = getattr(sys_id, "x0", None)
            if x0_est is not None and np.size(x0_est) == order:
                x_k = np.asarray(x0_est, dtype=np.float64).reshape(order, 1)
            else:
                x_k = np.zeros((order, 1), dtype=np.float64)
            dy_hat = np.zeros(n_pts, dtype=np.float64)
            for k in range(n_pts):
                u_k = np.array([[du[k]]], dtype=np.float64)
                y_k = C_mat @ x_k + D_mat @ u_k
                dy_hat[k] = float(np.asarray(y_k).ravel()[0])
                x_k = A_mat @ x_k + B_mat @ u_k
    else:
        sys_id = sippy.system_identification(
            dy,
            du,
            method,
            na_ord=[order],
            nb_ord=[[order]],
            nc_ord=[order] if method == "ARMAX" else [0],
            nf_ord=[order] if method == "OE" else [0],
            delays=[[1]],
            max_iterations=100,
        )
        dy_hat = np.asarray(getattr(sys_id, "Yid", dy), dtype=np.float64).ravel()
        A_mat, B_mat, C_mat, D_mat = None, None, None, None

    y_hat = y0 + dy_hat
    rmse = float(np.sqrt(np.mean((y_arr - y_hat) ** 2)))
    denom = float(np.linalg.norm(y_arr - np.mean(y_arr)))
    if denom > 1e-12:
        nrmse_fit = float(max(0.0, (1.0 - np.linalg.norm(y_arr - y_hat) / denom) * 100.0))
    else:
        nrmse_fit = 100.0 if rmse < 1e-9 else 0.0

    logger.info(
        "SIPPY %s (order=%d) identified: RMSE=%.4f K, Fit=%.2f%%",
        method,
        order,
        rmse,
        nrmse_fit,
    )
    return SubspaceIdentificationResult(
        method=method,
        order=order,
        y_hat=y_hat,
        rmse=rmse,
        nrmse_fit_pct=nrmse_fit,
        A=A_mat,
        B=B_mat,
        C=C_mat,
        D=D_mat,
    )


def compare_foptd_vs_subspace(
    t: np.ndarray,
    u: np.ndarray,
    y: np.ndarray,
    foptd: FOPTDModel,
    u_nominal: float = 100.0,
    y_nominal: Optional[float] = None,
) -> dict[str, SubspaceIdentificationResult]:
    """Benchmarks multi-step prediction of N4SID, MOESP, and ARMAX against FOPTD.

    Args:
        t: Time vector [min].
        u: Input coolant flow trajectory [L/min].
        y: Measured reactor temperature trajectory [K].
        foptd: Previously identified FOPTD model.
        u_nominal: Baseline coolant flow [L/min].
        y_nominal: Baseline reactor temperature [K].

    Returns:
        Dictionary mapping model name ('FOPTD', 'N4SID', 'MOESP', 'ARMAX') to result.
    """
    y0 = float(y[0]) if y_nominal is None else float(y_nominal)
    dt = float(t[1] - t[0]) if len(t) > 1 else 0.02

    # Simulate discrete FOPTD response under arbitrary input u(t)
    n = len(t)
    y_foptd = np.full(n, y0, dtype=np.float64)
    delay_steps = int(round(foptd.theta / dt))
    alpha = float(np.exp(-dt / foptd.tau))
    for k in range(1, n):
        u_delayed = u[k - 1 - delay_steps] if k - 1 - delay_steps >= 0 else u_nominal
        du_k = u_delayed - u_nominal
        y_foptd[k] = y0 + alpha * (y_foptd[k - 1] - y0) + foptd.k_p * (1.0 - alpha) * du_k

    rmse_foptd = float(np.sqrt(np.mean((y - y_foptd) ** 2)))
    denom = float(np.linalg.norm(y - np.mean(y))) or 1.0
    fit_foptd = float(max(0.0, (1.0 - np.linalg.norm(y - y_foptd) / denom) * 100.0))

    results: dict[str, SubspaceIdentificationResult] = {
        "FOPTD": SubspaceIdentificationResult(
            method="FOPTD",
            order=1,
            y_hat=y_foptd,
            rmse=rmse_foptd,
            nrmse_fit_pct=fit_foptd,
        )
    }
    for m_name in ("N4SID", "MOESP", "ARMAX"):
        results[m_name] = identify_subspace_or_armax(
            u=u,
            y=y,
            method=m_name,
            order=2,
            u_baseline=u_nominal,
            y_baseline=y0,
        )
    return results
