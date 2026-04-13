from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

#from .trajectory import RocketTrajectoryParameters, rocket_state, gravity_turn_trajectory
from .trajectory import GravityTurnParameters, gravity_turn_trajectory
from .directivity import angle_between_exhaust_and_station, gaussian_cone_directivity, doppler_shift

@dataclass
class Station:
    name: str
    x_m: float
    z_m: float = 0.0

@dataclass
class NetworkResult:
    peak_metrics: pd.DataFrame
    time_series: dict[str, pd.DataFrame]

class RocketModel:
    def __init__(
        self,
        trajectory: GravityTurnParameters | None = None,
        c_mps: float = 343.0,
        q0: float = 1.0,
        phi0_deg: float = 30.0,
        sigma_deg: float = 20.0,
        q_rise_tau: float = 8.0,
        q_decay_tau: float | None = None,
        f0_hz: float = 20.0,
        source_model: str = "point",
        plume_length_m: float = 100.0,
        n_plume_sources: int = 10,
        plume_decay_scale: float = 3.0,
    ) -> None:
        self.trajectory = trajectory or GravityTurnParameters()
        self.c_mps = float(c_mps)
        self.q0 = float(q0)
        self.phi0_deg = float(phi0_deg)
        self.sigma_deg = float(sigma_deg)
        self.q_rise_tau = float(q_rise_tau)
        self.q_decay_tau = q_decay_tau
        self.f0_hz = float(f0_hz)

        self.source_model = str(source_model).lower()
        self.plume_length_m = float(plume_length_m)
        self.n_plume_sources = int(n_plume_sources)
        self.plume_decay_scale = float(plume_decay_scale)

    def source_strength(self, t_s):
        t_s = np.asarray(t_s, dtype=float)
        rise = 1.0 - np.exp(-t_s / self.q_rise_tau)
        if self.q_decay_tau is None:
            decay = np.ones_like(t_s)
        else:
            decay = np.exp(-t_s / self.q_decay_tau)
        return self.q0 * rise * decay

    def predict_station(self, station: Station, t_max: float = 120.0, dt: float = 0.1) -> pd.DataFrame:
        t_s = np.arange(0.0, t_max + dt, dt)

        state = gravity_turn_trajectory(t_s, self.trajectory)
        q = self.source_strength(t_s)

        # --------------------------------------------------------------
        # POINT SOURCE MODEL
        # --------------------------------------------------------------
        if self.source_model == "point":
            rx = station.x_m - state["x_m"]
            rz = station.z_m - state["z_m"]

            r_m = np.sqrt(rx**2 + rz**2)
            t_obs = t_s + r_m / self.c_mps

            phi = angle_between_exhaust_and_station(
                state["ux"], state["uz"], rx, rz
            )

            directivity = gaussian_cone_directivity(
                phi,
                phi0_deg=self.phi0_deg,
                sigma_deg=self.sigma_deg,
            )

            with np.errstate(divide="ignore", invalid="ignore"):
                amplitude = q * directivity / r_m
                radial_velocity = (
                    state["vx_mps"] * rx + state["vz_mps"] * rz
                ) / r_m

            f_obs = doppler_shift(self.f0_hz, self.c_mps, radial_velocity)

            return pd.DataFrame({
                "station": station.name,
                "t_source_s": t_s,
                "t_obs_s": t_obs,
                "x_source_m": state["x_m"],
                "z_source_m": state["z_m"],
                "vx_source_mps": state["vx_mps"],
                "vz_source_mps": state["vz_mps"],
                "theta_deg": np.rad2deg(state["theta_rad"]),
                "distance_m": r_m,
                "phi_deg": np.rad2deg(phi),
                "directivity": directivity,
                "source_strength": q,
                "amplitude": amplitude,
                "radial_velocity_mps": radial_velocity,
                "f_obs_hz": f_obs,
                "source_model": "point",
            })

        # --------------------------------------------------------------
        # DISTRIBUTED PLUME MODEL
        # --------------------------------------------------------------
        elif self.source_model == "plume":
            nsrc = self.n_plume_sources
            if nsrc < 1:
                raise ValueError("n_plume_sources must be >= 1")

            # storage for each plume source contribution
            amplitude_sum = np.zeros_like(t_s, dtype=float)
            radial_velocity_sum = np.zeros_like(t_s, dtype=float)
            directivity_sum = np.zeros_like(t_s, dtype=float)
            distance_sum = np.zeros_like(t_s, dtype=float)
            phi_sum = np.zeros_like(t_s, dtype=float)
            t_obs_sum = np.zeros_like(t_s, dtype=float)

            weight_sum = np.zeros_like(t_s, dtype=float)

            # plume coordinate: frac=0 near nozzle, frac=1 far downstream
            if nsrc == 1:
                fracs = np.array([0.0])
            else:
                fracs = np.linspace(0.0, 1.0, nsrc)

            for frac in fracs:
                plume_offset_m = frac * self.plume_length_m

                # source element lies behind rocket along exhaust axis
                x_src = state["x_m"] + plume_offset_m * state["ux"]
                z_src = state["z_m"] + plume_offset_m * state["uz"]

                rx = station.x_m - x_src
                rz = station.z_m - z_src

                r_m = np.sqrt(rx**2 + rz**2)
                t_obs = t_s + r_m / self.c_mps

                phi = angle_between_exhaust_and_station(
                    state["ux"], state["uz"], rx, rz
                )

                directivity = gaussian_cone_directivity(
                    phi,
                    phi0_deg=self.phi0_deg,
                    sigma_deg=self.sigma_deg,
                )

                # simple weighting: strongest near nozzle, decays downstream
                w = np.exp(-self.plume_decay_scale * frac)

                with np.errstate(divide="ignore", invalid="ignore"):
                    amp_i = w * q * directivity / r_m
                    vr_i = (
                        state["vx_mps"] * rx + state["vz_mps"] * rz
                    ) / r_m

                amplitude_sum += np.nan_to_num(amp_i, nan=0.0, posinf=0.0, neginf=0.0)
                radial_velocity_sum += w * np.nan_to_num(vr_i, nan=0.0, posinf=0.0, neginf=0.0)
                directivity_sum += w * np.nan_to_num(directivity, nan=0.0, posinf=0.0, neginf=0.0)
                distance_sum += w * np.nan_to_num(r_m, nan=0.0, posinf=0.0, neginf=0.0)
                phi_sum += w * np.nan_to_num(phi, nan=0.0, posinf=0.0, neginf=0.0)
                t_obs_sum += w * np.nan_to_num(t_obs, nan=0.0, posinf=0.0, neginf=0.0)
                weight_sum += w

            # weighted averages for descriptive columns
            with np.errstate(divide="ignore", invalid="ignore"):
                radial_velocity = radial_velocity_sum / weight_sum
                directivity = directivity_sum / weight_sum
                distance_m = distance_sum / weight_sum
                phi = phi_sum / weight_sum
                t_obs = t_obs_sum / weight_sum

            f_obs = doppler_shift(self.f0_hz, self.c_mps, radial_velocity)

            return pd.DataFrame({
                "station": station.name,
                "t_source_s": t_s,
                "t_obs_s": t_obs,
                "x_source_m": state["x_m"],
                "z_source_m": state["z_m"],
                "vx_source_mps": state["vx_mps"],
                "vz_source_mps": state["vz_mps"],
                "theta_deg": np.rad2deg(state["theta_rad"]),
                "distance_m": distance_m,
                "phi_deg": np.rad2deg(phi),
                "directivity": directivity,
                "source_strength": q,
                "amplitude": amplitude_sum,
                "radial_velocity_mps": radial_velocity,
                "f_obs_hz": f_obs,
                "source_model": "plume",
            })

        else:
            raise ValueError("source_model must be 'point' or 'plume'")


    def predict_network(self, stations: list[Station], t_max: float = 120.0, dt: float = 0.1) -> NetworkResult:
        time_series = {}
        rows = []
        for sta in stations:
            df = self.predict_station(sta, t_max=t_max, dt=dt)
            time_series[sta.name] = df
            i_peak = int(np.nanargmax(df["amplitude"].to_numpy()))
            peak = df.iloc[i_peak]
            rows.append({
                "station": sta.name,
                "peak_time_s": float(peak["t_obs_s"]),
                "peak_amplitude": float(peak["amplitude"]),
                "peak_distance_m": float(peak["distance_m"]),
                "peak_source_time_s": float(peak["t_source_s"]),
                "peak_phi_deg": float(peak["phi_deg"]),
                "peak_f_obs_hz": float(peak["f_obs_hz"]),
            })
        peak_metrics = pd.DataFrame(rows).sort_values("peak_time_s").reset_index(drop=True)
        return NetworkResult(peak_metrics=peak_metrics, time_series=time_series)
