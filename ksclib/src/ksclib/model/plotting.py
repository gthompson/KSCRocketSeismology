from __future__ import annotations
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from .model import RocketModel
from .trajectory import gravity_turn_trajectory
def plot_trajectory(model: RocketModel, t_max: float = 120.0, dt: float = 0.1):
    t = np.arange(0.0, t_max + dt, dt)
    s = gravity_turn_trajectory(t, model.trajectory)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(s["x_m"] / 1000.0, s["z_m"] / 1000.0, linewidth=2)
    ax.set_xlabel("East distance (km)")
    ax.set_ylabel("Altitude (km)")
    ax.set_title("Rocket trajectory")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig, ax

def plot_network_peaks(peak_metrics: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(peak_metrics["peak_distance_m"] / 1000.0, peak_metrics["peak_time_s"], s=70)
    for _, row in peak_metrics.iterrows():
        ax.text(row["peak_distance_m"] / 1000.0, row["peak_time_s"], str(row["station"]), fontsize=8, ha="left", va="bottom")
    ax.set_xlabel("Peak source-station distance (km)")
    ax.set_ylabel("Peak arrival time (s)")
    ax.set_title("Predicted peak arrival times")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig, ax

def plot_station_synthetic(df_station: pd.DataFrame):
    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(df_station["t_obs_s"], df_station["amplitude"], linewidth=2)
    ax1.set_xlabel("Observed time (s)")
    ax1.set_ylabel("Amplitude")
    ax1.set_title(f"Synthetic infrasound at {df_station['station'].iloc[0]}")
    ax1.grid(True, alpha=0.3)
    ax2 = ax1.twinx()
    ax2.plot(df_station["t_obs_s"], df_station["f_obs_hz"], linestyle="--")
    ax2.set_ylabel("Observed frequency (Hz)")
    fig.tight_layout()
    return fig, (ax1, ax2)
