from pathlib import Path
from rocket_infrasound_model.model import RocketModel, Station
from rocket_infrasound_model.plotting import plot_trajectory, plot_network_peaks, plot_station_synthetic

stations = [
    Station(name="WEST_3KM", x_m=-3000.0, z_m=0.0),
    Station(name="PAD", x_m=0.0, z_m=0.0),
    Station(name="EAST_3KM", x_m=3000.0, z_m=0.0),
    Station(name="EAST_8KM", x_m=8000.0, z_m=0.0),
]

model = RocketModel(c_mps=343.0, q0=1.0, phi0_deg=30.0, sigma_deg=20.0)
result = model.predict_network(stations, t_max=120.0, dt=0.1)
print(result.peak_metrics)

result.peak_metrics.to_csv("example_peak_metrics.csv", index=False)

fig1, ax1 = plot_trajectory(model, t_max=120.0, dt=0.1)
fig1.savefig("example_trajectory.png", dpi=200, bbox_inches="tight")

fig2, ax2 = plot_network_peaks(result.peak_metrics)
fig2.savefig("example_peak_times.png", dpi=200, bbox_inches="tight")

for sta_name, df_sta in result.time_series.items():
    fig, _ = plot_station_synthetic(df_sta)
    fig.savefig(f"example_{sta_name}.png", dpi=200, bbox_inches="tight")
