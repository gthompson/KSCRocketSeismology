from __future__ import annotations
from dataclasses import dataclass
import numpy as np


def air_density_isa_simple(z_m: np.ndarray | float, rho0: float = 1.225, H: float = 8500.0):
    """
    Simple exponential atmosphere.
    """
    z = np.maximum(np.asarray(z_m, dtype=float), 0.0)
    return rho0 * np.exp(-z / H)


def speed_of_sound_simple(z_m: np.ndarray | float):
    """
    Very simple sound-speed profile for lower/middle atmosphere.
    Good enough for a first-order drag model.

    Troposphere/lower stratosphere approximation.
    """
    z = np.maximum(np.asarray(z_m, dtype=float), 0.0)

    # Temperature profile approximation
    T = np.where(
        z < 11000.0,
        288.15 - 0.0065 * z,
        216.65
    )

    gamma = 1.4
    R = 287.05
    return np.sqrt(gamma * R * T)


def drag_coefficient_mach(mach: np.ndarray | float):
    """
    Crude rocket Cd model:
    - subsonic ~0.3
    - transonic spike
    - supersonic decline
    """
    M = np.asarray(mach, dtype=float)

    Cd = np.full_like(M, 0.30)

    # Transonic rise
    m1 = (M >= 0.8) & (M < 1.2)
    Cd[m1] = 0.30 + (0.60 - 0.30) * (M[m1] - 0.8) / 0.4

    # Mild decline into supersonic
    m2 = (M >= 1.2) & (M < 3.0)
    Cd[m2] = 0.60 + (0.35 - 0.60) * (M[m2] - 1.2) / 1.8

    # Higher supersonic / hypersonic, flatten a bit
    m3 = M >= 3.0
    Cd[m3] = 0.35

    return Cd


@dataclass
class RocketTrajectoryParameters:
    a_z: float = 20.0
    a_x: float = 4.0
    theta_max_deg: float = 75.0
    tau_theta: float = 45.0

    def theta_rad(self, t: np.ndarray | float) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        theta_max = np.deg2rad(self.theta_max_deg)
        return theta_max * (1.0 - np.exp(-t / self.tau_theta))

def rocket_state(t: np.ndarray | float, params: RocketTrajectoryParameters) -> dict[str, np.ndarray]:
    t = np.asarray(t, dtype=float)
    x = 0.5 * params.a_x * t**2
    z = 0.5 * params.a_z * t**2
    vx = params.a_x * t
    vz = params.a_z * t
    theta = params.theta_rad(t)
    ux = -np.sin(theta)
    uz = -np.cos(theta)
    return {
        "x_m": x,
        "z_m": z,
        "vx_mps": vx,
        "vz_mps": vz,
        "ax_mps2": np.full_like(t, params.a_x, dtype=float),
        "az_mps2": np.full_like(t, params.a_z, dtype=float),
        "theta_rad": theta,
        "ux": ux,
        "uz": uz,
    }

from dataclasses import dataclass
import numpy as np


@dataclass
class GravityTurnParameters:
    #thrust_N: float = 3.914e7   # ~8.8 million lbf → ~39 MN # peak
    thrust_N: float = 3.74e7     # 8.4 million lbf / 37.4 MN average for 2 minutes
    m0_kg: float = 2.61e6      # initial mass (~SLS scale)
    mdot_kgps: float = 1.2081e4       # mass flow rate (kg/s)
    g: float = 9.81

    t_vertical: float = 6.0
    t_pitchover: float = 10.0
    pitch_rate_deg: float = 0.45
    max_pitch_deg: float = 80.0

    area_m2: float = 78.0         # SLS stack reference area
    rho0: float = 1.225           # sea-level density
    scale_height_m: float = 8500.0

def throttle_factor(t):
    if t < 60:
        return 1.0
    elif t < 80:
        return 0.88
    elif t < 128:
        return 0.95
    return 1.0

def gravity_turn_trajectory(t, params: GravityTurnParameters):
    """
    Gravity-turn trajectory with:
    - constant average thrust
    - falling mass
    - exponential atmosphere
    - Mach-dependent drag
    """
    t = np.asarray(t, dtype=float)
    if t.ndim != 1 or len(t) < 2:
        raise ValueError("t must be a 1D array with at least 2 samples")

    dt = t[1] - t[0]

    x = np.zeros_like(t)
    z = np.zeros_like(t)
    vx = np.zeros_like(t)
    vz = np.zeros_like(t)
    theta = np.zeros_like(t)

    ax_arr = np.zeros_like(t)
    az_arr = np.zeros_like(t)
    mass = np.zeros_like(t)
    rho = np.zeros_like(t)
    speed = np.zeros_like(t)
    mach = np.zeros_like(t)
    cd = np.zeros_like(t)
    drag_force = np.zeros_like(t)

    mass[0] = params.m0_kg

    for i in range(1, len(t)):
        ti = t[i]

        # Mass depletion
        mass[i] = max(params.m0_kg - params.mdot_kgps * ti, 0.25 * params.m0_kg)

        # Pitch program
        if ti < params.t_vertical:
            theta[i] = 0.0
        elif ti < params.t_pitchover:
            theta[i] = np.deg2rad(2.0)
        else:
            theta[i] = theta[i - 1] + np.deg2rad(params.pitch_rate_deg) * dt

        theta[i] = min(theta[i], np.deg2rad(params.max_pitch_deg))

        # Thrust acceleration along body axis
        a_thrust = throttle_factor(ti) * params.thrust_N / mass[i]
        ax_thrust = a_thrust * np.sin(theta[i])
        az_thrust = a_thrust * np.cos(theta[i])

        # Atmosphere and drag
        rho[i] = air_density_isa_simple(z[i - 1], rho0=params.rho0, H=params.scale_height_m)

        speed[i - 1] = np.sqrt(vx[i - 1]**2 + vz[i - 1]**2)
        a_sound = speed_of_sound_simple(z[i - 1])
        mach[i] = speed[i - 1] / max(a_sound, 1e-6)
        cd[i] = drag_coefficient_mach(mach[i])

        q = 0.5 * rho[i] * speed[i - 1]**2
        drag_force[i] = q * cd[i] * params.area_m2
        a_drag = drag_force[i] / mass[i]

        if speed[i - 1] > 1e-6:
            ax_drag = -a_drag * vx[i - 1] / speed[i - 1]
            az_drag = -a_drag * vz[i - 1] / speed[i - 1]
        else:
            ax_drag = 0.0
            az_drag = 0.0

        # Total acceleration
        ax = ax_thrust + ax_drag
        az = az_thrust - params.g + az_drag

        ax_arr[i] = ax
        az_arr[i] = az

        # Integrate
        vx[i] = vx[i - 1] + ax * dt
        vz[i] = vz[i - 1] + az * dt

        x[i] = x[i - 1] + vx[i] * dt
        z[i] = max(0.0, z[i - 1] + vz[i] * dt)

    speed = np.sqrt(vx**2 + vz**2)

    # Exhaust direction opposite to velocity
    ux = -vx / np.maximum(speed, 1e-6)
    uz = -vz / np.maximum(speed, 1e-6)

    return {
        "x_m": x,
        "z_m": z,
        "vx_mps": vx,
        "vz_mps": vz,
        "ax_mps2": ax_arr,
        "az_mps2": az_arr,
        "theta_rad": theta,
        "mass_kg": mass,
        "rho_kgm3": rho,
        "speed_mps": speed,
        "mach": mach,
        "cd": cd,
        "drag_force_N": drag_force,
        "ux": ux,
        "uz": uz,
    }