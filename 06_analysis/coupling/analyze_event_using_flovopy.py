import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from obspy import read, UTCDateTime, Trace, Stream, read_inventory
from obspy.signal.cross_correlation import xcorr_max, correlate
from obspy.signal.util import next_pow_2
from scipy.stats import linregress
import os
from flovopy.core.preprocessing import preprocess_stream, remove_low_quality_traces
from flovopy.core.enhanced import EnhancedStream

#from obspy import UTCDateTime, read_inventory
from flovopy.core.usf import get_stationXML_inventory, inventory2dataless_and_resp





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
    x = seis.data
    y = infra.data
    cc = correlate(x, y, shift=len(x)//2)
    X = np.fft.rfft(cc)
    freqs = np.fft.rfftfreq(len(cc), d=seis.stats.delta)
    spectrum = np.abs(X)
    peak_freq = freqs[np.argmax(spectrum)]
    return peak_freq

def trace_basic_metrics(tr):
    data = tr.data
    abs_data = np.abs(data)
    peak_amp = np.max(abs_data)
    peak_index = np.argmax(abs_data)
    peak_time = tr.stats.starttime + peak_index / tr.stats.sampling_rate

    nfft = next_pow_2(len(data))
    freqs = np.fft.rfftfreq(nfft, d=tr.stats.delta)
    spectrum = np.abs(np.fft.rfft(data, n=nfft))
    dom_freq = freqs[np.argmax(spectrum)]

    return {
        "trace_id": tr.id,
        "station": tr.stats.station,
        "channel": tr.stats.channel,
        "peak_amplitude": peak_amp,
        "time_of_peak": str(peak_time),
        "dominant_frequency": dom_freq
    }

def air_to_ground_coupling(seismic_trace, infrasound_trace, water_level=0.01, taper_fraction = 0.05, plot=False):
    
    npts = min(len(seismic_trace.data), len(infrasound_trace.data))
    dt = seismic_trace.stats.delta

    st1 = seismic_trace.copy()
    st2 = infrasound_trace.copy()


    s = st1.data
    i = st2.data

    S = np.fft.rfft(s)
    I = np.fft.rfft(i)

    I_mag = np.abs(I)


    # Optionally stabilize I first to prevent division by zero
    I_stabilized = np.where(np.abs(I) < 1e-10, 1e-10, I)

    # Clean non-finite values from I and S
    I_stabilized = np.nan_to_num(I_stabilized, nan=1e-10, posinf=1e10, neginf=-1e10)
    S = np.nan_to_num(S, nan=0.0, posinf=0.0, neginf=0.0)

    # Now safe to compute
    H = S / (I_stabilized * np.exp(1j * np.angle(I)))


    h = np.fft.irfft(H, n=npts)

    h_trace = Trace(data=h.astype(np.float32))
    h_trace.stats = seismic_trace.stats.copy()
    h_trace.stats.channel = f"H_{seismic_trace.stats.channel}"

    if plot:
        plt.figure(figsize=(10, 4))
        plt.plot(h_trace.times(), h_trace.data)
        plt.title(f"Impulse Response: {seismic_trace.id} vs {infrasound_trace.id}")
        plt.xlabel("Time (s")
        plt.ylabel("Amplitude")
        plt.grid()
        plt.tight_layout()
        plt.show()

    return h_trace



def main(stream, starttime, endtime, inventory):

    preprocess_stream(stream, inv=inventory, filterType='highpass', freq=[0.1, 100.0], 
                      outputType="DEF", bool_clean=True, taperFraction=0.05, bool_detrend=True)
    stream.plot(equal_scale=False)
    remove_low_quality_traces(stream, quality_threshold=4.0, verbose=True)
    est = EnhancedStream(stream=stream)
    print(est)
    #stream.write('/home/thompsong/Dropbox/launchenhanced.pkl', format='PICKLE')
    est.ampengfft()
    #stream.write('/home/thompsong/Dropbox/launchAEF.pkl', format='PICKLE')
    print(est)
    input('ENTER to continue')

    for tr in est:
        try:
            m = getattr(tr.stats, 'metrics', {})
            trace_metrics.append({
                "trace_id": tr.id,
                "station": tr.stats.station,
                "channel": tr.stats.channel,
                "peak_amplitude": m.get("peakamp"),
                "time_of_peak": m.get("peaktime"),
                "dominant_frequency": m.get("peakf")
            })
        except Exception as e:
            print(f"Trace metrics failed for {tr.id}: {e}")
        print(tr)
        print(tr.stats)
        #tr.plot()
        print()
    input('ENTER to continue')
    return est

    stations = set(tr.stats.station for tr in stream)
    all_metrics = []
    trace_metrics = []

    for station in stations:
        st_station = est.select(station=station)
        traces = st_station.select(channel="HH*") + st_station.select(channel="HD*")

        for i, tr1 in enumerate(traces):
            for j, tr2 in enumerate(traces):
                these_traces = Stream(traces=[tr1, tr2])
                these_traces.plot(equal_scale=False)
                try:
                    trace1_id = tr1.id
                    trace2_id = tr2.id
                    kind = "auto" if i == j else (
                        "seis-seis" if tr1.stats.channel.startswith("HH") and tr2.stats.channel.startswith("HH") else
                        "acou-acou" if tr1.stats.channel.startswith("HD") and tr2.stats.channel.startswith("HD") else
                        "seis-acou"
                    )

                    metrics = {
                        "station": station,
                        "trace1_id": trace1_id,
                        "trace2_id": trace2_id,
                        "type": kind
                    }


                    #if kind == "seis-acou":
                    if kind:
                        h_trace = air_to_ground_coupling(tr1, tr2, plot=True)
                        peak_amp, lag, duration = summarize_coupling_function(h_trace)
                        peak_freq = cross_spectral_peak(tr1, tr2)

                        minlen = min(len(tr1), len(tr2))
                        sr = tr1.stats.sampling_rate
                        x = tr1.data[:minlen]
                        y = tr2.data[:minlen]

                        slope, intercept, r_value, _, _ = linregress(x, y)
                        cc = correlate(x, y, shift=minlen // 2)
                        cc_max, lag_samples = xcorr_max(cc)
                        lag_time = lag_samples / sr

                        metrics.update({
                            "r_value": r_value,
                            "cc_max": cc_max,
                            "lag_s": lag_time,
                            "coupling_peak_amp": peak_amp,
                            "coupling_lag_s": lag,
                            "coupling_duration_s": duration,
                            "peak_crosscorr_freq_Hz": peak_freq
                        })

                    all_metrics.append(metrics)

                except Exception as e:
                    print(f"Failed {tr1.id} vs {tr2.id}: {e}")

    df = pd.DataFrame(all_metrics)
    df_traces = pd.DataFrame(trace_metrics)
    os.makedirs("output", exist_ok=True)
    df.to_csv("output/coupling_metrics.csv", index=False)
    df_traces.to_csv("output/trace_metrics.csv", index=False)
    print("Saved results to output/coupling_metrics.csv and output/trace_metrics.csv")
    return df, df_traces

if __name__ == "__main__":

    import os
    import platform
    from flovopy.core.usf import build_combined_infrabsu_centaur_stationxml, download_infraBSU_stationxml, get_stationXML_inventory, inventory2dataless_and_resp


    # Get user's home directory
    home = os.path.expanduser("~")

    # Adjust paths based on OS
    if platform.system() == 'Darwin':  # macOS
        metadata_dir = os.path.join(home, 'Dropbox', 'DATA', 'station_metadata')
    else:
        metadata_dir = '/data/station_metadata'
    os.makedirs(metadata_dir, exist_ok=True)

    xmlfile = os.path.join(metadata_dir, 'KSC.xml')
    # dataless = os.path.join(metadata_dir, 'KSC.dataless')
    respdir = os.path.join(metadata_dir, 'RESP')
    os.makedirs(respdir, exist_ok=True)

    metadata_csv = os.path.join(metadata_dir, 'ksc.csv')
    coord_csv = os.path.join(metadata_dir, 'ksc_coordinates_only.csv')

    NRLpath = os.path.join(metadata_dir, 'NRL')
    infraBSUstationXML = os.path.join(metadata_dir, 'infraBSU_21s_0.5inch.xml')

    # Always use $HOME/bin for converter JAR
    stationxml_seed_converter_jar = os.path.join(home, 'bin', 'stationxml-seed-converter.jar')

    print('### Building full inventories with responses ###')
    print('First try to get combined response for infraBSU and Centaur:')

    if not os.path.isfile(infraBSUstationXML):
        download_infraBSU_stationxml(save_path=infraBSUstationXML)

    if os.path.isfile(xmlfile):
        inv = read_inventory(xmlfile)
        print(f"[INFO] Loaded existing StationXML: {xmlfile}")
    else:
        print("[INFO] Creating new inventory from USF definitions...")
        inv = get_stationXML_inventory(xmlfile=xmlfile, overwrite=True, infraBSUstationxml=infraBSUstationXML, metadata_csv=metadata_csv, coord_csv=coord_csv, nrl_path=NRLpath)
        inventory2dataless_and_resp(inv, output_dir=respdir, stationxml_seed_converter_jar=stationxml_seed_converter_jar)

    # === USER-DEFINED OUTPUT DIRECTORY ===
    output_dir = os.path.expanduser("~/Dropbox/DATA/KSC/OUTPUTS")  # CHANGE AS NEEDED
    os.makedirs(output_dir, exist_ok=True)

    ################################
    # === PROCESSING STARTS HERE ===
    ################################

    infraBSU_centaur_inv = build_combined_infrabsu_centaur_stationxml(
        fsamp=100.0,
        vpp=40,
        stationxml_path=infraBSUstationXML,
        network="FL", station="S39A1", location="10", channel="HDF",
        latitude=0.0, longitude=0.0, elevation=0.0, depth=0.0,
        start_date=UTCDateTime(1970, 1, 1), 
        end_date=UTCDateTime(2100, 1, 1), 
        sitename=None)
    print(infraBSU_centaur_inv)
    chan = infraBSU_centaur_inv.select(network="FL", station="S39A1", location="10", channel="HDF")[0][0].channels[0]
    print(chan)
    print(chan.response)
    exit()


    eventtime = "2022-11-01T13:41:00"
    t0 = UTCDateTime(eventtime) - 300
    t1 = t0 + 500

    import glob
    dayfiles = glob.glob(os.path.join(home, 'Dropbox', 'DATA', 'KSC', 'dayfiles', 'FL.S39A1.*0.H*.305'))
    print(dayfiles)
    st = Stream()
    for file in dayfiles:
        this_st = read(file)
        st.append(this_st[0])
    #st = st.select(station='S39A*')
    
    # Subset to only station 'S39A1'
    inv = inv.select(station='S39A1')

    # Optionally, print to verify
    print(inv)

    """
    # This section of code was added only to remove a response stage from an InfraBSU sensor relating to a dummy Triullum Compact that had been used
    # But now this should get eliminated in the original function in usf.py that builds the combined Centaur/InfraBSU response

    # First, subset the inventory for station S39A1 and channel HDF
    chan = inv.select(network="FL", station="S39A1", location="10", channel="HDF")[0][0].channels[0]

    # Get the response object for the first matching channel
    response = chan.response

    # Keep only the PolesZeros that converts from Pa to V, and remove the one from M/S to V
    filtered_stages = []

    for stage in response.response_stages:
        if hasattr(stage, "input_units") and hasattr(stage, "output_units"):
            if stage.input_units.lower() == "m/s" and stage.output_units.lower() == "v":
                # skip this stage
                continue
        filtered_stages.append(stage)

    # Update the response stages
    response.response_stages = filtered_stages

    # To plot the full frequency response:
    response.plot(min_freq=0.01, output="DEF")  # or DISP/ACC as appropriate
    try:
        response.recalculate_overall_sensitivity() # fails for infrasound
    except:
        from obspy.core.inventory.response import InstrumentSensitivity

        # Example: 4.6e-5 V/Pa, total gain through system (e.g., incl. V→counts conversion)
        chan.response.instrument_sensitivity = InstrumentSensitivity(
            value=4.6e-5 * 40 * 400000,  # example: Pa→V × amp gain × digitizer gain
            frequency=1.0,
            input_units='Pa',
            output_units='COUNTS'
        )
    print(response)
    """
    

    #df_results, df_trace_metrics = main(st, t0, t1, inv)
    from flovopy.processing.spectrograms import icewebSpectrogram
    stime = UTCDateTime(2022,11,1,13,40,0)
    stlong = st.copy().trim(starttime=stime-400, endtime=stime+580)
    est = main(stlong, t0, t1, inv)
    stlong = est.copy()
    stlong.plot(equal_scale=False, outfile=os.path.join(output_dir, 'seismograms_long.png'))

    stlow = stlong.copy()
    stlow.detrend()
    stlow.taper(max_percentage=0.1)
    stlow.filter('bandpass', freqmin=0.002, freqmax=1.0)
    stlow.trim(starttime=stime, endtime=stime+180)
    stlow.plot(equal_scale=False, outfile=os.path.join(output_dir, 'seismograms_lowpass.png'))
    spobj = icewebSpectrogram(stream=stlow)
    sgramfile = os.path.join(output_dir, 'sgram_low.png')
    spobj.precompute(secsPerFFT=8)
    spobj.plot(outfile=sgramfile, log=True, fmin=0.005, fmax=1.0, cmap='seismic', dbscale=False)
    spobj.compute_amplitude_spectrum(compute_bandwidth=True)
    spobj.plot_amplitude_spectrum(normalize=True, title=None, outfile=os.path.join(output_dir, 'spectra_low.png'), logx=True)
    stlow.trim(starttime=stime+40, endtime=stime+90)
    stlow.plot(equal_scale=False, outfile=os.path.join(output_dir, 'seismograms_lowpass_details.png'))

    sthigh = stlong.copy()
    sthigh.detrend()
    sthigh.taper(max_percentage=0.1)
    sthigh.filter('bandpass', freqmin=0.5, freqmax=30.0) # high pass filter needed 
    sthigh.trim(starttime=stime+40, endtime=stime+90)
    sthigh.plot(equal_scale=False, outfile=os.path.join(output_dir, 'seismograms_lowpass.png'))
    spobj = icewebSpectrogram(stream=sthigh)
    sgramfile = os.path.join(output_dir, 'sgram_high.png')
    spobj.precompute(secsPerFFT=2.56)
    spobj.plot(outfile=sgramfile, log=True, fmin=0.5, fmax=50.0, cmap='seismic', dbscale=False)
    spobj.compute_amplitude_spectrum(compute_bandwidth=True)
    spobj.plot_amplitude_spectrum(normalize=True, title=None, outfile=os.path.join(output_dir, 'spectra_high.png'), logx=True)
    sthigh.trim(starttime=stime+40, endtime=stime+65)
    sthigh.plot(equal_scale=False, outfile=os.path.join(output_dir, 'seismograms_highpass_onset.png'))

    print(spobj)
    trz = spobj.stream.select(channel='HHZ')[0]
    Az = trz.stats.spectrum.A
    F = trz.stats.spectrum.F
    trP = spobj.stream.select(channel='HDF')[0]
    AP = trP.stats.spectrum.A    
    plt.close('all')
    plt.plot(F, Az/AP)
    plt.title('Spectral amplitude ratio (HHZ/HDF)')
    plt.savefig(os.path.join(output_dir, 'spectral_ratio.png'))

    #df_results, df_trace_metrics = main(stlong, t0, t1, inv)
    
    