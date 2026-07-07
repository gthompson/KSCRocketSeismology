import numpy as np
import matplotlib.pyplot as plt
from obspy.signal.cross_correlation import xcorr_max, correlate
from obspy.signal.util import next_pow_2
from scipy.stats import linregress


def analyze_seismo_acoustic_pair(tr_seis, tr_acou, title="Seismo-Acoustic Analysis",
                                 freqmin=0.1, freqmax=30.0,
                                 window_duration=60.0, sliding=True):
    """
    Compare infrasound and seismic Trace objects using time series, amplitude regression,
    spectral ratios, and cross-correlation (with optional sliding window).

    Parameters:
    -----------
    tr_seis : obspy.Trace
        Seismic trace (e.g., vertical ground motion)
    tr_acou : obspy.Trace
        Infrasound trace (e.g., barometric pressure)
    title : str
        Title for all plots
    freqmin, freqmax : float
        Bandpass filter limits in Hz
    window_duration : float
        Duration in seconds to trim both traces (from starttime)
    sliding : bool
        If True, compute sliding window cross-correlation
    """

    # === Trim to common window ===
    t0 = max(tr_seis.stats.starttime, tr_acou.stats.starttime)
    t1 = t0 + window_duration
    tr_seis = tr_seis.copy().trim(t0, t1)
    tr_acou = tr_acou.copy().trim(t0, t1)

    # === Preprocess ===
    for tr in (tr_seis, tr_acou):
        tr.detrend("demean")
        tr.taper(0.05)
        tr.filter("bandpass", freqmin=freqmin, freqmax=freqmax, corners=4, zerophase=True)

    # === Match lengths ===
    minlen = min(len(tr_seis), len(tr_acou))
    x = tr_acou.data[:minlen]
    y = tr_seis.data[:minlen]
    sr = tr_seis.stats.sampling_rate
    times = np.arange(minlen) / sr

    # === Plot time series ===
    plt.figure(figsize=(10, 4))
    plt.plot(times, y, label=tr_seis.stats.channel)
    plt.plot(times, x, label=tr_acou.stats.channel, alpha=0.7)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title(f"Time Series: {title}")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()

    # === Amplitude regression ===
    slope, intercept, r_value, _, _ = linregress(x, y)
    abs_x = abs(x)
    abs_y = abs(y)
    plt.figure(figsize=(6, 6))
    plt.scatter(abs_x, abs_y, s=1, alpha=0.3, label="Samples")
    plt.plot(abs_x, slope * abs_x + intercept, color='red',
             label=f"Fit: y = {slope:.2f}x + {intercept:.2f}\nR² = {r_value**2:.3f}")
    plt.xlabel("Infrasound Amplitude")
    plt.ylabel("Seismic Amplitude")
    plt.title(f"Amplitude Scatter + Regression: {title}")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()

    # === Spectral ratio ===
    nfft = next_pow_2(minlen)
    freqs = np.fft.rfftfreq(nfft, d=1/sr)
    fft_seis = np.fft.rfft(y, n=nfft)
    fft_acou = np.fft.rfft(x, n=nfft)
    ratio_db = 20 * np.log10(np.abs(fft_seis) / np.abs(fft_acou))
    ratio_db[np.isinf(ratio_db)] = np.nan

    plt.figure(figsize=(10, 4))
    plt.semilogx(freqs, ratio_db)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Seismic / Infrasound Amplitude Ratio (dB)")
    plt.title(f"Spectral Ratio: {title}")
    plt.grid(which="both")
    plt.tight_layout()
    plt.show()

    # === Cross-correlation ===
    #cc_max, lag_samples = xcorr_max(x, y, shift=minlen // 2)
    cc = correlate(x, y, shift=minlen //2)
    cc_max, lag_samples = xcorr_max(cc)
    lag_time = lag_samples / sr
    print(f"Global Max Cross-Correlation = {cc_max:.3f}, Time Lag = {lag_time:.3f} s")

    if sliding:
        win_len = 5.0  # seconds
        step = 1.0     # seconds
        nwin = int(win_len * sr)
        nstep = int(step * sr)

        times_slide = []
        lags = []
        corrs = []

        for i in range(0, minlen - nwin, nstep):
            w1 = x[i:i + nwin]
            w2 = y[i:i + nwin]
            
            cc = correlate(w1, w2, shift=nwin // 2)
            cc_max, lag = xcorr_max(cc)

            times_slide.append(i / sr)
            lags.append(lag / sr)
            corrs.append(cc)

        # Plot sliding results
        plt.figure(figsize=(10, 5))
        plt.subplot(2, 1, 1)
        plt.plot(times_slide, corrs)
        plt.ylabel("Max Corr")
        plt.title(f"Sliding Cross-Correlation: {title}")
        plt.grid()

        plt.subplot(2, 1, 2)
        plt.plot(times_slide, lags)
        plt.xlabel("Time (s)")
        plt.ylabel("Lag (s)")
        plt.grid()

        plt.tight_layout()
        plt.show()

from obspy import Trace
import numpy as np
import matplotlib.pyplot as plt
from obspy.signal.invsim import cosine_taper

def air_to_ground_coupling(seismic_trace: Trace,
                            infrasound_trace: Trace,
                            water_level: float = 0.01,
                            plot: bool = False) -> Trace:
    """
    Deconvolve infrasound from seismic signal to estimate the air-to-ground coupling function.
    
    Parameters:
        seismic_trace (Trace): ObsPy Trace of seismic component (Z/N/E)
        infrasound_trace (Trace): ObsPy Trace of corresponding infrasound signal
        water_level (float): Stabilization parameter for deconvolution (default 0.01)
        plot (bool): If True, plot the resulting impulse response
    
    Returns:
        Trace: Impulse response (air-to-ground coupling function) as a new ObsPy Trace
    """
    # Align traces
    npts = min(len(seismic_trace.data), len(infrasound_trace.data))
    dt = seismic_trace.stats.delta
    if seismic_trace.stats.delta != infrasound_trace.stats.delta:
        raise ValueError("Traces must have the same sampling rate")

    # Apply taper to reduce edge artifacts
    taper = cosine_taper(npts, 0.1)
    s = seismic_trace.data[:npts] * taper
    i = infrasound_trace.data[:npts] * taper

    # FFT and spectral division
    S = np.fft.rfft(s)
    I = np.fft.rfft(i)

    I_mag = np.abs(I)
    I_stabilized = np.where(I_mag < water_level, water_level, I_mag)
    H = S / (I_stabilized * np.exp(1j * np.angle(I)))  # Stabilized spectral division

    # Inverse FFT to get coupling function
    h = np.fft.irfft(H, n=npts)

    # Wrap in ObsPy Trace
    h_trace = Trace(data=h.astype(np.float32))
    h_trace.stats.network = seismic_trace.stats.network
    h_trace.stats.station = seismic_trace.stats.station
    h_trace.stats.channel = f"H_{seismic_trace.stats.channel}"  # H for impulse response
    h_trace.stats.sampling_rate = 1.0 / dt
    h_trace.stats.starttime = seismic_trace.stats.starttime

    if plot:
        plt.figure(figsize=(10, 4))
        plt.plot(h_trace.times(), h_trace.data)
        plt.title(f"Air-to-Ground Coupling Function: {seismic_trace.stats.channel}")
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude")
        plt.grid()
        plt.tight_layout()
        plt.show()

    return h_trace

from obspy.core import Stream, UTCDateTime


def main(stream: Stream, starttime: UTCDateTime, endtime: UTCDateTime):
    """
    Analyze all seismo-acoustic trace pairs in the given stream between starttime and endtime.

    Parameters:
    -----------
    stream : obspy.Stream
        The input Stream containing multiple stations and channels
    starttime : obspy.UTCDateTime
        Start of analysis window
    endtime : obspy.UTCDateTime
        End of analysis window
    """

    print(f"Analyzing seismo-acoustic pairs from {starttime} to {endtime}")
    stream = stream.copy().trim(starttime, endtime)

    stations = set(tr.stats.station for tr in stream)
    print(f"Found {len(stations)} stations: {stations}")

    for station in stations:
        st_station = stream.select(station=station)
        seismic_traces = st_station.select(channel="HH*")  # e.g., BHZ, HHZ, EHZ
        infrasound_traces = st_station.select(channel="HD*")  # customize as needed

        if not seismic_traces or not infrasound_traces:
            print(f"Skipping station {station}: missing seismic or infrasound channel.")
            continue

        for tr_seis in seismic_traces:
            for tr_acou in infrasound_traces:
                print(f"\n>>> Station {station}: {tr_seis.id} vs {tr_acou.id}")
                print(tr_seis, tr_acou)
                print(tr_seis.stats, tr_acou.stats)

                # 
                try:
                    analyze_seismo_acoustic_pair(
                        tr_seis,                # deconvolve acoustic trace from seismic trace 
                try:
                    analyze_seismo_acoustic_pair(
                        tr_seis,
                        tr_acou,
                        title=f"{station}: {tr_seis.stats.channel} vs {tr_acou.stats.channel}"
                    )
                except Exception as e:
                    print(f"Failed analysis for {tr_seis.id} vs {tr_acou.id}: {e}")

                        tr_acou,
                        title=f"{station}: {tr_seis.stats.channel} vs {tr_acou.stats.channel}"
                    )
                except Exception as e:
                    print(f"Failed analysis for {tr_seis.id} vs {tr_acou.id}: {e}")

                # Deconvolve acoustic trace from seismic trace
                try:
                    h_trace = air_to_ground_coupling(
                        seismic_trace=tr_seis,
                        infrasound_trace=tr_acou,
                        water_level=0.01,
                        plot=True  # Set to False if you don’t want immediate plotting
                    )
                    print(f"Deconvolution complete: {h_trace.id}")
                    h_trace.write(f"{station}_{tr_seis.stats.channel}_vs_{tr_acou.stats.channel}_impulse.mseed", format="MSEED")

                except Exception as e:
                    print(f"Deconvolution failed for {tr_seis.id} vs {tr_acou.id}: {e}")


if __name__ == "__main__":
    from obspy import read, UTCDateTime
    eventtime = "2022-11-01T13:41:00"

    # Load your full dataset
    stS = read(f"/data/KSC/EROSION/EVENTS/{eventtime}/seismic.mseed")
    stI = read(f"/data/KSC/EROSION/EVENTS/{eventtime}/infrasound.mseed")
    st = stS + stI
    print(st)
    input('ENTER to continue')

    # Define time window (e.g., around a rocket launch)
    t0 = UTCDateTime(eventtime)
    t1 = t0 + 90  # 90-second window

    # Run the analysis
    main(st, starttime=t0, endtime=t1)
