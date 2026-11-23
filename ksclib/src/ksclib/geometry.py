"""Station geometry relative to the source site, and moving-source geometry along a trajectory."""
from __future__ import annotations

import numpy as np
import pandas as pd


def station_table(event, sheet=None):
    """Stations with east/north offsets (m), distance (km) and azimuth (deg) from the event site."""
    from obspy.geodetics import gps2dist_azimuth
    sta = pd.read_excel(event.station_file, sheet_name=sheet or event.station_sheet)
    rows = []
    for _, r in sta.iterrows():
        d, az, _ = gps2dist_azimuth(event.site_lat, event.site_lon, r.lat, r.lon)
        rows.append(dict(station=r.station, lat=r.lat, lon=r.lon, distance_km=d / 1000, azimuth_deg=az,
                         east_m=d * np.sin(np.radians(az)), north_m=d * np.cos(np.radians(az))))
    return pd.DataFrame(rows).set_index("station")


def source_geometry(event, station, ts=None, c=343.0, az=None, stations=None):
    """Per source time t_s: source position, distance, arrival time, emission angle, ray elevation.

    Launch events use the gravity-turn trajectory (event.trajectory overrides
    GravityTurnParameters) along `az` (default event.launch_azimuth_deg); static
    events keep the source at the site (emission angle measured from vertical).
    Straight rays at sound speed `c`; t_s = 0 at event.origin_time.
    """
    from .model.trajectory import GravityTurnParameters, gravity_turn_trajectory
    ts = np.arange(0.0, 200.0 + 1e-9, 0.1) if ts is None else np.asarray(ts, float)
    r = (stations if stations is not None else station_table(event)).loc[station]
    if event.kind == "static":
        g = {k: np.zeros_like(ts) for k in ("x_m", "z_m", "vx_mps", "vz_mps", "speed_mps", "mach")}
        az = 0.0
    else:
        az = event.launch_azimuth_deg if az is None else az
        tt = np.arange(0.0, ts.max() + 0.2, 0.1)
        s = gravity_turn_trajectory(tt, GravityTurnParameters(**event.trajectory))
        g = {k: np.interp(ts, tt, s[k]) for k in ("x_m", "z_m", "vx_mps", "vz_mps", "speed_mps", "mach")}
    sa, ca = np.sin(np.radians(az)), np.cos(np.radians(az))
    dx, dy, dz = r.east_m - g["x_m"] * sa, r.north_m - g["x_m"] * ca, -g["z_m"]
    R = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    sp = np.maximum(g["speed_mps"], 1e-6)
    moving = g["speed_mps"] >= 1
    ux = np.where(moving, -g["vx_mps"] * sa / sp, 0.0)
    uy = np.where(moving, -g["vx_mps"] * ca / sp, 0.0)
    uz = np.where(moving, -g["vz_mps"] / sp, -1.0)
    cosphi = np.clip((ux * dx + uy * dy + uz * dz) / R, -1, 1)
    return pd.DataFrame(dict(t_s=ts, t_obs=ts + R / c, r_m=R, alt_km=g["z_m"] / 1000,
                             downrange_km=g["x_m"] / 1000, speed_mps=g["speed_mps"], mach=g["mach"],
                             phi_deg=np.degrees(np.arccos(cosphi)),
                             elevation_deg=np.degrees(np.arcsin(g["z_m"] / R))))
