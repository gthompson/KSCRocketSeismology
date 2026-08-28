import numpy as np


def compute_speed_of_sound(temperature_c, relative_humidity=0):
    """
    Estimate the speed of sound in humid air.

    Uses the simple empirical approximation:

        c = 331.3 + 0.606 * T_C + 1.26 * RH / 100

    where:
        T_C : temperature in degrees Celsius
        RH  : relative humidity in percent (0-100)

    Parameters
    ----------
    temperature_c : float or array_like
        Air temperature in degrees Celsius.
    relative_humidity : float or array_like, optional
        Relative humidity in percent. Defaults to 0.

    Returns
    -------
    float or ndarray
        Estimated speed of sound in m/s.
    """
    temperature_c = np.asarray(temperature_c)
    relative_humidity = np.asarray(relative_humidity)

    return 331.3 + 0.606 * temperature_c + 1.26 * relative_humidity / 100.0


def fahrenheit_to_celsius(temp_f):
    """
    Convert temperature from degrees Fahrenheit to Celsius.

    Parameters
    ----------
    temp_f : float or array_like
        Temperature in degrees Fahrenheit.

    Returns
    -------
    float or ndarray
        Temperature in degrees Celsius.
    """
    temp_f = np.asarray(temp_f)
    return (temp_f - 32.0) * (5.0 / 9.0)


def standard_atmosphere(
    z_max=3000,
    dz=1.0,
    T0=273.0,
    lapse_rate=-0.00651,
    P0=101000.0,
    g=9.81,
    R=287.0,
):
    """
    Compute a simple standard atmosphere assuming a constant lapse rate.

    Parameters
    ----------
    z_max : float
        Maximum altitude (m).
    dz : float
        Altitude increment (m).
    T0 : float
        Sea-level temperature (K).
    lapse_rate : float
        Temperature lapse rate (K/m).
    P0 : float
        Sea-level pressure (Pa).
    g : float
        Gravity (m/s²).
    R : float
        Gas constant for dry air (J kg⁻¹ K⁻¹).

    Returns
    -------
    z : ndarray
        Altitude (m).
    temperature : ndarray
        Temperature (K).
    pressure : ndarray
        Pressure (Pa).
    pressure_gradient : ndarray
        Pressure gradient (Pa/m).
    gradient_altitude : ndarray
        Midpoints of altitude bins (m).
    """
    z = np.arange(0, z_max + dz, dz)

    temperature = T0 + lapse_rate * z
    pressure = P0 * (temperature / T0) ** (-g / (R * lapse_rate))

    pressure_gradient = np.diff(pressure) / dz
    gradient_altitude = z[:-1] + dz / 2

    return (
        z,
        temperature,
        pressure,
        pressure_gradient,
        gradient_altitude,
    )

import numpy as np


def mach_vs_overpressure(
    speed_of_sound=348.8,
    gamma=1.4,
    ambient_pressure=100000.0,
    reference_distance=1400.0,
    reference_overpressure=1000.0,
):
    """
    Compute Mach number as a function of overpressure.

    Based on Marchetti & Yasur (2013, GRL).

    Returns
    -------
    results : dict
        Dictionary containing arrays and summary statistics.
    """

    overpressure = np.logspace(0, 5)
    underpressure = -overpressure[::-1]
    overpressure = np.concatenate((underpressure, overpressure))

    mach = np.sqrt(
        1.0 + (gamma + 1.0) / (2.0 * gamma) * overpressure / ambient_pressure
    )

    r = np.arange(10.0, reference_distance + 1.0)

    reduced_pressure = reference_overpressure * reference_distance
    pressure_along_ray = reduced_pressure / r

    mach_along_ray = np.sqrt(
        1.0 + (gamma + 1.0)
        / (2.0 * gamma)
        * pressure_along_ray
        / ambient_pressure
    )

    speed_at_array = 1.6 + mach_along_ray[-1] * speed_of_sound
    mean_speed = 1.6 + np.mean(mach_along_ray) * speed_of_sound

    return {
        "overpressure": overpressure,
        "mach": mach,
        "distance": r,
        "pressure_along_ray": pressure_along_ray,
        "mach_along_ray": mach_along_ray,
        "mach_at_array": mach_along_ray[-1],
        "speed_at_array": speed_at_array,
        "mean_mach": np.mean(mach_along_ray),
        "mean_speed": mean_speed,
    }

import numpy as np


def effective_sound_speed_along_ray(
    temperature_f,
    relative_humidity_percent=0,
    wind_direction_from_deg=150,
    wind_speed_knots=10,
    ray_azimuth_deg=None,
    reference_distance=None,
    reference_overpressure=None,
):
    """
    Compute effective acoustic speed along a raypath, including wind advection.

    Wind direction is meteorological: direction FROM which wind blows.
    Ray azimuth is direction of propagation, e.g. SLC40 -> BCHH.

    Returns
    -------
    dict
        Includes still-air sound speed, wind vector, projected wind component,
        and effective sound speed along the ray.
    """

    # windless speed of sound
    c0 = compute_speed_of_sound(
        fahrenheit_to_celsius(temperature_f),
        relative_humidity=relative_humidity_percent,
    )

    # account for shockwave
    if reference_distance and reference_overpressure:
        results = mach_vs_overpressure(
            reference_distance=reference_distance,
            reference_overpressure=reference_overpressure,
            speed_of_sound=c0,
        )
        c1 = results['mean_mach']*c0
        print(c1)
        print('****')
    else:
        c1 = c0


    # account for wind vector
    wind_speed_mps = wind_speed_knots * 0.514444

    # Convert meteorological FROM direction to direction wind is blowing TOWARD
    wind_direction_to_deg = (wind_direction_from_deg + 180.0) % 360.0

    if ray_azimuth_deg is None:
        raise ValueError("ray_azimuth_deg must be supplied for SLC40 -> BCHH")

    # Wind component along ray
    angle_diff_rad = np.deg2rad(wind_direction_to_deg - ray_azimuth_deg)
    wind_along_ray_mps = wind_speed_mps * np.cos(angle_diff_rad)

    c_effective = c1 + wind_along_ray_mps

    print(
        f"Still-air sound speed: {c0:.1f} m/s, "
        f"Still-air shock speed: {c1:.1f} m/s, "
        f"wind along ray: {wind_along_ray_mps:.1f} m/s, "
        f"effective sound speed: {c_effective:.1f} m/s"
    )

    return {
        "speed_of_sound_still_air_mps": c0,
        "wind_speed_mps": wind_speed_mps,
        "wind_direction_to_deg": wind_direction_to_deg,
        "ray_azimuth_deg": ray_azimuth_deg,
        "wind_along_ray_mps": wind_along_ray_mps,
        "effective_sound_speed_mps": c_effective,
        "shockwave_speed_mps": c1,
        "acoustic_speed_with_wind_mps": c0 + wind_along_ray_mps,
    }


if __name__ == "__main__":
    z, T, P, dPdz, zg = standard_atmosphere()
    # plot
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 6))
    plt.subplot(1, 2, 1)
    plt.plot(T, z)
    plt.xlabel('Temperature (K)')
    plt.ylabel('Altitude (m)')
    plt.title('Standard Atmosphere - Temperature')
    plt.grid(True)

    plt.subplot(1, 2, 2)
    plt.plot(P, z)
    plt.xlabel('Pressure (Pa)')
    plt.ylabel('Altitude (m)')
    plt.title('Standard Atmosphere - Pressure')
    plt.grid(True)

    plt.tight_layout()
    plt.show()


    RelativeHumidityPercent = 92
    TemperatureF = 80
    WindDirectionFromDeg = 150
    WindDirectionDeg = WindDirectionFromDeg + 180 % 360
    WindSpeedKnots = 10
    WindSpeedMps = WindSpeedKnots * 0.514444
    speed_of_sound = compute_speed_of_sound(fahrenheit_to_celsius(TemperatureF), relative_humidity=RelativeHumidityPercent)
    print(f"(no wind) Speed of sound at {TemperatureF} F and {RelativeHumidityPercent}% RH: {speed_of_sound:.1f} m/s")

    results = mach_vs_overpressure(
        reference_distance=1400.0,
        reference_overpressure=1400.0,
        speed_of_sound=speed_of_sound,
    )

    print(
        f"At array: Mach = {results['mach_at_array']:.3f}, "
        f"speed = {results['speed_at_array']:.1f} m/s"
    )

    print(
        f"Along raypath: Mean Mach = {results['mean_mach']:.3f}, "
        f"speed = {results['mean_speed']:.1f} m/s"
    )

    # Replace with actual SLC40 -> BCHH azimuth
    ray_azimuth_deg = 19.0

    result = effective_sound_speed_along_ray(
        TemperatureF,
        relative_humidity_percent=RelativeHumidityPercent,
        wind_direction_from_deg=WindDirectionFromDeg,
        wind_speed_knots=WindSpeedKnots,
        ray_azimuth_deg=ray_azimuth_deg,
        reference_distance=1400.0,
        reference_overpressure=1400.0,
    )

    from pprint import pprint
    pprint(result)