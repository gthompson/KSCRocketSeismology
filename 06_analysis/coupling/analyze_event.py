import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from obspy import read, UTCDateTime, Trace, Stream
from obspy.signal.cross_correlation import xcorr_max #, correlate
from scipy.signal import correlate
from obspy.signal.invsim import cosine_taper
from obspy.signal.util import next_pow_2
from scipy.stats import linregress
import os

def analyze_seismo_acoustic_pair(tr1, tr2, freqmin=0.1, freqmax=30.0, duration=60.0):
    t0 = max(tr1.stats.starttime, tr2.stats.starttime)
    t1 = t0 + duration
    tr1 = tr1.copy().trim(t0, t1)
    tr2 = tr2.copy().trim(t0, t1)

    for tr in (tr1, tr2):
        tr.detrend("demean")
        tr.taper(0.05)
        tr.filter("bandpass", freqmin=freqmin, freqmax=freqmax, corners=4, zerophase=True)

    minlen = min(len(tr1), len(tr2))
    x = tr1.data[:minlen]
    y = tr2.data[:minlen]
    sr = tr1.stats.sampling_rate

    # Amplitude regression
    slope, intercept, r_value, _, _ = linregress(x, y)

    # Cross-correlation
    cc = correlate(x, y, shift=minlen // 2)
    cc_max, lag_samples = xcorr_max(cc)
    lag_time = lag_samples / sr

    return r_value, cc_max, lag_time

def summarize_coupling_function(h_trace, energy_percent=0.9):
    h = h_trace.data
    t = h_trace.times()
    abs_h = np.abs(h)
    peak_amp = np.max(abs_h)
    lag_time = t[np.argmax(abs_h)]

    energy = h**2
    cumulative_energy = np.cumsum(energy)
    total_energy = cumulative_energy[-1]
    start_idx = np.argmax(cumulative_energy >= (1 - energy_percent) * total_energy)
    end_idx = np.argmax(cumulative_energy >= energy_percent * total_energy)
    duration = t[end_idx] - t[start_idx]

    return peak_amp, lag_time, duration

def cross_spectral_peak(seis, infra):
    xcorr = correlate(seis.data, infra.data, mode="same")
    X = np.fft.rfft(xcorr)
    freqs = np.fft.rfftfreq(len(xcorr), d=seis.stats.delta)
    spectrum = np.abs(X)
    peak_freq = freqs[np.argmax(spectrum)]
    return peak_freq

def air_to_ground_coupling(seismic_trace, infrasound_trace, water_level=0.01, plot=False):
    npts = min(len(seismic_trace.data), len(infrasound_trace.data))
    dt = seismic_trace.stats.delta
    if not np.all(np.isfinite(seismic_trace.data)) or not np.all(np.isfinite(infrasound_trace.data)):
        raise ValueError("Trace contains NaNs or Infs")


    taper = cosine_taper(npts, 0.1)
    s = seismic_trace.data[:npts] * taper
    i = infrasound_trace.data[:npts] * taper

    S = np.fft.rfft(s)
    I = np.fft.rfft(i)

    I_mag = np.abs(I)
    I_stabilized = np.where(I_mag < water_level, water_level, I_mag)
    H = S / (I_stabilized * np.exp(1j * np.angle(I)))
    h = np.fft.irfft(H, n=npts)

    h_trace = Trace(data=h.astype(np.float32))
    h_trace.stats = seismic_trace.stats.copy()
    h_trace.stats.channel = f"H_{seismic_trace.stats.channel}"

    if plot:
        plt.figure(figsize=(10, 4))
        plt.plot(h_trace.times(), h_trace.data)
        plt.title(f"Impulse Response: {seismic_trace.id} vs {infrasound_trace.id}")
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude")
        plt.grid()
        plt.tight_layout()
        plt.show()

    return h_trace

def main(stream, starttime, endtime):
    stream = stream.copy().trim(starttime, endtime)
    stations = set(tr.stats.station for tr in stream)
    all_metrics = []

    for station in stations:
        st_station = stream.select(station=station)
        traces = st_station.select(channel="HH*") + st_station.select(channel="HD*")

        for i, tr1 in enumerate(traces):
            for j, tr2 in enumerate(traces):
                try:
                    trace1_id = tr1.id
                    trace2_id = tr2.id
                    kind = "auto" if i == j else (
                        "seis-seis" if tr1.stats.channel.startswith("HH") and tr2.stats.channel.startswith("HH") else
                        "acou-acou" if tr1.stats.channel.startswith("HD") and tr2.stats.channel.startswith("HD") else
                        "seis-acou"
                    )

                    r_value, cc_max, lag_s = analyze_seismo_acoustic_pair(tr1, tr2)

                    metrics = {
                        "station": station,
                        "trace1_id": trace1_id,
                        "trace2_id": trace2_id,
                        "type": kind,
                        "r_value": r_value,
                        "cc_max": cc_max,
                        "lag_s": lag_s
                    }

                    if kind == "seis-acou":
                        h_trace = air_to_ground_coupling(tr1, tr2)
                        peak_amp, lag, duration = summarize_coupling_function(h_trace)
                        peak_freq = cross_spectral_peak(tr1, tr2)

                        metrics.update({
                            "coupling_peak_amp": peak_amp,
                            "coupling_lag_s": lag,
                            "coupling_duration_s": duration,
                            "peak_crosscorr_freq_Hz": peak_freq
                        })

                    all_metrics.append(metrics)

                except Exception as e:
                    print(f"Failed {tr1.id} vs {tr2.id}: {e}")

    df = pd.DataFrame(all_metrics)
    os.makedirs("output", exist_ok=True)
    df.to_csv("output/coupling_metrics.csv", index=False)
    print("Saved results to output/coupling_metrics.csv")
    return df

if __name__ == "__main__":
    eventtime = "2022-11-01T13:41:00"
    t0 = UTCDateTime(eventtime)
    t1 = t0 + 90

    stS = read(f"/data/KSC/EROSION/EVENTS/{eventtime}/seismic.mseed")
    stI = read(f"/data/KSC/EROSION/EVENTS/{eventtime}/infrasound.mseed")
    st = stS + stI

    df_results = main(st, t0, t1)
