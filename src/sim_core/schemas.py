"""Runtime data contracts and validation schemas for CSTR simulation and benchmarks.

Enforces strict physical bounds, monotonicity, and non-negativity across module
boundaries using Pydantic v2 and Pandera DataFrameModel schemas.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.typing import DataFrame, Series
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class CstrParameterContract(BaseModel):
    """Validated physical and kinetic parameter schema for non-isothermal CSTR."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    q: float = Field(default=100.0, gt=0.0, description="Process volumetric flow rate [L/min].")
    V: float = Field(default=100.0, gt=0.0, description="Reactor liquid volume [L].")
    k_0: float = Field(
        default=7.2e10, gt=0.0, description="Arrhenius pre-exponential factor [1/min]."
    )
    E_over_R: float = Field(default=8750.0, gt=0.0, description="Activation energy ratio E/R [K].")
    delta_H: float = Field(
        default=-5.0e4, lt=0.0, description="Exothermic reaction enthalpy [cal/mol]."
    )
    rho_cp: float = Field(
        default=500.0, gt=0.0, description="Volumetric heat capacity of mixture [cal/(L*K)]."
    )
    UA: float = Field(
        default=5.0e4, gt=0.0, description="Overall heat transfer coefficient * area [cal/(min*K)]."
    )
    V_j: float = Field(default=20.0, gt=0.0, description="Cooling jacket volume [L].")
    rho_j_cp_j: float = Field(
        default=500.0, gt=0.0, description="Coolant volumetric heat capacity [cal/(L*K)]."
    )
    C_Af: float = Field(
        default=1.0, gt=0.0, le=10.0, description="Feed reactant concentration [mol/L]."
    )
    T_f: float = Field(default=350.0, ge=250.0, le=500.0, description="Feed temperature [K].")
    T_jf: float = Field(
        default=300.0, ge=250.0, le=450.0, description="Jacket inlet coolant temperature [K]."
    )


class CstrTrajectorySchema(pa.DataFrameModel):
    """Pandera schema for closed-loop and open-loop CSTR time-series trajectories."""

    t: Series[float] = pa.Field(ge=0.0, coerce=True, description="Simulation time [min].")
    C_A: Series[float] = pa.Field(
        ge=0.0, le=10.0, coerce=True, description="Reactant A concentration [mol/L]."
    )
    T: Series[float] = pa.Field(
        ge=250.0, le=600.0, coerce=True, description="Reactor bulk temperature [K]."
    )
    T_j: Series[float] = pa.Field(
        ge=250.0, le=600.0, coerce=True, description="Cooling jacket temperature [K]."
    )
    q_j: Series[float] = pa.Field(
        ge=0.0, le=300.0, coerce=True, description="Manipulated coolant flow rate [L/min]."
    )
    setpoint: Series[float] = pa.Field(
        ge=250.0, le=600.0, coerce=True, nullable=True, description="Temperature setpoint [K]."
    )

    class Config:
        """Pandera model configuration."""

        strict = False
        coerce = True

    @pa.check("t", name="monotonic_increasing_time")
    @classmethod
    def check_monotonic_time(cls, s: Series[float]) -> bool:
        """Verifies that the time vector is monotonically non-decreasing."""
        if len(s) < 2:
            return True
        return bool(np.all(np.diff(s.to_numpy()) >= 0.0))


class BenchmarkMetricsSchema(pa.DataFrameModel):
    """Pandera schema for controller benchmark summary tables."""

    method: Series[str] = pa.Field(coerce=True, description="Controller or tuning identifier.")
    iae: Series[float] = pa.Field(ge=0.0, coerce=True, description="Integral of Absolute Error.")
    itae: Series[float] = pa.Field(
        ge=0.0, coerce=True, description="Integral of Time-weighted Absolute Error."
    )
    ise: Series[float] = pa.Field(ge=0.0, coerce=True, description="Integral of Squared Error.")
    tv: Series[float] = pa.Field(
        ge=0.0, coerce=True, description="Total Variation of control input [L/min]."
    )
    overshoot_pct: Series[float] = pa.Field(
        ge=0.0, coerce=True, description="Maximum percentage overshoot [%]."
    )
    ms: Series[float] = pa.Field(
        ge=1.0, nullable=True, coerce=True, description="Maximum sensitivity peak ||S||_inf."
    )

    class Config:
        """Pandera model configuration."""

        strict = False
        coerce = True


@pa.check_types
def validate_trajectory_dataframe(
    t: np.ndarray,
    states: np.ndarray,
    q_j: np.ndarray,
    setpoint: np.ndarray | None = None,
) -> DataFrame[CstrTrajectorySchema]:
    """Constructs and validates a CSTR trajectory DataFrame against CstrTrajectorySchema.

    Args:
        t: 1D time array [min].
        states: 2D state array of shape (N, 3) with columns [C_A, T, T_j].
        q_j: 1D manipulated coolant flow array [L/min].
        setpoint: Optional 1D temperature setpoint array [K].

    Returns:
        Validated DataFrame conforming to CstrTrajectorySchema.
    """
    sp_col = setpoint if setpoint is not None else states[:, 1]
    df = pd.DataFrame(
        {
            "t": np.asarray(t, dtype=np.float64),
            "C_A": np.asarray(states[:, 0], dtype=np.float64),
            "T": np.asarray(states[:, 1], dtype=np.float64),
            "T_j": np.asarray(states[:, 2], dtype=np.float64),
            "q_j": np.asarray(q_j, dtype=np.float64),
            "setpoint": np.asarray(sp_col, dtype=np.float64),
        }
    )
    return DataFrame[CstrTrajectorySchema](df)


@pa.check_types
def validate_benchmark_dataframe(df: pd.DataFrame) -> DataFrame[BenchmarkMetricsSchema]:
    """Validates a controller benchmark metrics DataFrame against BenchmarkMetricsSchema.

    Args:
        df: Raw DataFrame containing benchmark metrics.

    Returns:
        Validated DataFrame conforming to BenchmarkMetricsSchema.
    """
    return DataFrame[BenchmarkMetricsSchema](df)
