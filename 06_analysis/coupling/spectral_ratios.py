import numpy as np
import matplotlib.pyplot as plt
from obspy import read, Trace
from obspy.signal.util import next_pow_2
from obspy.signal.invsim import cosine_taper

# Load traces (replace with your own files or stream slicing)
st = read("your_data.mseed")  # or load directly with Stream from memory
tr_water = st.select(channel="??Z")[0]     # e.g., vibrating wire sensor
tr_air = st.select(channel="??D")[0]       # e.g., infrasound sensor

# Trim to time window of interest (e.g., rocket launch)
starttime = tr_water.stats.starttime + 100
endtime = starttime + 60  # 60 seconds
tr_water = tr_water.copy().trim(starttime, endtime)
tr_air = tr_air.copy().trim(starttime, endtime)

# Detrend and taper
tr_water.detrend("demean")
tr_air.detrend("demean")
tr_water.taper(max_percentage=0.05, type="hann")
tr_air.taper(max_percentage=0.05, type="hann")

# Get sampling rate and FFT length
npts = min(len(tr_water.data), len(tr_air.data))
nfft = next_pow_2(npts)
df = tr_water.stats.sampling_rate
freqs = np.fft.rfftfreq(nfft, d=1.0/df)

# Compute FFTs
fft_water = np.fft.rfft(tr_water.data, n=nfft)
fft_air = np.fft.rfft(tr_air.data, n=nfft)

# Compute spectral amplitude ratio (magnitude only)
amplitude_ratio = np.abs(fft_water) / np.abs(fft_air)
amplitude_ratio_db = 20 * np.log10(amplitude_ratio)

# Optional: mask low-coherence or zero-divide problems
amplitude_ratio_db = np.where(np.isfinite(amplitude_ratio_db), amplitude_ratio_db, np.nan)

# Plot
plt.figure(figsize=(10, 6))
plt.semilogx(freqs, amplitude_ratio_db, label="Water/Air Spectral Ratio")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Amplitude Ratio (dB)")
plt.title("Spectral Amplitude Ratio: Vibrating Wire / Infrasound")
plt.grid(True, which="both", ls="--")
plt.axhline(0, color='k', linestyle=':')
plt.legend()
plt.tight_layout()
plt.show()
