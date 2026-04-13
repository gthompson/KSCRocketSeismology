from __future__ import annotations
import numpy as np

def angle_between_exhaust_and_station(ux, uz, rx, rz):
    rnorm = np.sqrt(rx**2 + rz**2)
    with np.errstate(divide="ignore", invalid="ignore"):
        cosphi = (ux * rx + uz * rz) / rnorm
    cosphi = np.clip(cosphi, -1.0, 1.0)
    return np.arccos(cosphi)

def gaussian_cone_directivity(phi_rad, phi0_deg: float = 30.0, sigma_deg: float = 20.0):
    phi0 = np.deg2rad(phi0_deg)
    sigma = np.deg2rad(sigma_deg)
    return np.exp(-0.5 * ((phi_rad - phi0) / sigma) ** 2)

def doppler_shift(f0_hz: float, c_mps: float, radial_velocity_mps):
    denom = c_mps - radial_velocity_mps
    with np.errstate(divide="ignore", invalid="ignore"):
        return f0_hz * c_mps / denom
