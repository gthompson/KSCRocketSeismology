import numpy as np
import matplotlib.pyplot as plt
from obspy import read, UTCDateTime
from obspy.signal.cross_correlation import xcorr_max
from obspy.core.stream import Stream

# === PARAMETERS ===
file = "your_rocket_data.mseed"
start_offset = 100       # seconds after file start
duration = 60            # length of analysis window (s)
win_len = 5.0            # sliding window length (s)
win_step = 1.0           # step size for sliding window (s)
freqmin = 0.1            # bandpass filter min
freqmax = 10.0           # bandpass filter max
reference_channel = "BDF"  # e.g., infrasound as reference

# === LOAD AND PREPARE STREAM ===
st = read(file)
st.detrend("demean")
st.taper(0.05)

# Select time window around launch
t0 = st[0].stats.starttime + start_offset
t1 = t0 + duration
st.trim(t0, t1)

# Filter all traces
st.filter("bandpass", freqmin=freqmin, freqmax=freqmax, corners=4, zerophase=True)

# Identify channels
channels = {tr.stats.channel: tr for tr in st}
ref_tr = channels[reference_channel]

# === SLIDING WINDOW CROSS-CORRELATION ===
results = {}

for ch_name, tr in channels.items():
    if ch_name == reference_channel:
        continue  # skip self-correlation

    corr_vals = []
    lag_vals = []
    times = []

    for t in np.arange(0, duration - win_len, win_step):
        win_start = t0 + t
        win_end = win_start + win_len

        ref_win = ref_tr.copy().trim(win_start, win_end).data
        tr_win = tr.copy().trim(win_start, win_end).data

        # Match lengths
        if len(ref_win) != len(tr_win):
            minlen = min(len(ref_win), len(tr_win))
            ref_win = ref_win[:minlen]
            tr_win = tr_win[:minlen]

        # Compute cross-correlation
        cc_max, lag = xcorr_max(ref_win, tr_win, shift=len(ref_win)//2)
        lag_time = lag / tr.stats.sampling_rate

        corr_vals.append(cc_max)
        lag_vals.append(lag_time)
        times.append(t)

    results[ch_name] = {
        "time": np.array(times),
        "correlation": np.array(corr_vals),
        "lag_sec": np.array(lag_vals)
    }

# === PLOT RESULTS ===
fig, ax = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

for ch, data in results.items():
    ax[0].plot(data["time"], data["correlation"], label=ch)
    ax[1].plot(data["time"], data["lag_sec"], label=ch)

ax[0].set_ylabel("Max Correlation Coefficient")
ax[0].legend()
ax[0].grid()

ax[1].set_ylabel("Lag Time (s)")
ax[1].set_xlabel("Time since launch start (s)")
ax[1].grid()

plt.suptitle(f"Cross-correlation relative to {reference_channel}")
plt.tight_layout()
plt.show()
