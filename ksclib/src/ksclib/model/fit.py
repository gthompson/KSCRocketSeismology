from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from .trajectory import RocketTrajectoryParameters
from .model import RocketModel, Station

@dataclass
class FitResult:
    x: np.ndarray
    success: bool
    cost: float
    message: str

def build_model_from_parameter_vector(p: np.ndarray) -> RocketModel:
    traj = RocketTrajectoryParameters(
        a_z=float(p[0]),
        a_x=float(p[1]),
        theta_max_deg=float(p[2]),
        tau_theta=float(p[3]),
    )
    return RocketModel(
        trajectory=traj,
        c_mps=float(p[4]),
        q0=float(p[5]),
        phi0_deg=float(p[6]),
        sigma_deg=float(p[7]),
    )

def fit_peak_times_and_amplitudes(stations_df: pd.DataFrame, observed_df: pd.DataFrame, x0: np.ndarray, t_max: float = 120.0, dt: float = 0.1, weight_time: float = 1.0, weight_amp: float = 1.0) -> FitResult:
    station_map = {row.station: Station(row.station, float(row.x_m), float(row.z_m)) for row in stations_df.itertuples(index=False)}
    obs = observed_df.copy()

    def residuals(p: np.ndarray) -> np.ndarray:
        model = build_model_from_parameter_vector(p)
        stations = [station_map[name] for name in obs["station"] if name in station_map]
        pred = model.predict_network(stations, t_max=t_max, dt=dt).peak_metrics
        merged = obs.merge(pred, on="station", suffixes=("_obs", "_pred"))
        r_time = weight_time * (merged["peak_time_s_obs"] - merged["peak_time_s_pred"]).to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            r_amp = weight_amp * (np.log10(merged["peak_amplitude_obs"]) - np.log10(merged["peak_amplitude_pred"])).to_numpy()
        return np.concatenate([r_time, r_amp])

    result = least_squares(residuals, x0=x0)
    return FitResult(x=result.x, success=bool(result.success), cost=float(result.cost), message=str(result.message))
