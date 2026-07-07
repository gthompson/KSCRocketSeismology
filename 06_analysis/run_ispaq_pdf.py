import subprocess
import os
import shutil
from datetime import datetime, timedelta
from obspy import UTCDateTime, read_inventory, read
import glob

ALL_METRICS = (
    "amplifier_saturation,calibration_signal,clock_locked,cross_talk,dead_channel_gsn,"
    "dead_channel_lin,digital_filter_charging,digitizer_clipping,event_begin,event_end,"
    "event_in_progress,glitches,max_gap,max_overlap,max_range,max_stalta,missing_padded_data,"
    "num_gaps,num_overlaps,num_spikes,orientation_check,pct_above_nhnm,pct_below_nlnm,pdf,"
    "percent_availability,polarity_check,pressure_effects,psd_corrected,psd_uncorrected,"
    "sample_max,sample_mean,sample_median,sample_min,sample_rate_channel,sample_rate_resp,"
    "sample_rms,sample_snr,sample_unique,spikes,suspect_time_tag,telemetry_sync_error,"
    "timing_correction,timing_quality,transfer_function"
)

def validate_data_availability(sds_path, stationxml_path, start_date, duration_days, net_sta_pattern):
    print("\n[INFO] Checking data and metadata availability...")
    start = UTCDateTime(start_date)
    end = start + duration_days * 86400

    inv = read_inventory(stationxml_path)
    net, sta = net_sta_pattern.split(".")[:2]
    matches = inv.select(network=net, station=sta)
    if not matches:
        print(f"[WARNING] No matching station {net_sta_pattern} found in StationXML")
        return

    sncls = []
    for net in matches:
        for sta in net:
            for cha in sta:
                sncls.append((net.code, sta.code, cha.location_code or "--", cha.code))

    for sncl in sncls:
        net, sta, loc, chan = sncl
        year = start.year
        day = start.julday
        pattern = f"{sds_path}/{year}/{net}/{sta}/{chan[:3]}.D/{net}.{sta}.{loc}.{chan}.D.{year}.{day:03d}"
        files = glob.glob(pattern)
        if files:
            print(f"[OK] Found data for {net}.{sta}.{loc}.{chan}: {files[0]}")
            try:
                st = read(files[0], starttime=start, endtime=end)
                print(f"    -> Loaded {len(st)} traces with {sum(tr.stats.npts for tr in st)} samples")
            except Exception as e:
                print(f"    -> Error loading MiniSEED: {e}")
        else:
            print(f"[MISSING] No files matched: {pattern}")

def run_ispaq_on_sds(
    sds_path,
    stationxml_path,
    output_dir="output/ispaq",
    start_date="2022-11-01",
    duration_days=1,
    stations="FL.S39A1.*.H*",
    metrics=ALL_METRICS,
    generate_psd=True,
    generate_pdf=True
):
    os.makedirs(output_dir, exist_ok=True)
    csv_dir = os.path.join(output_dir, "csv")
    psd_dir = os.path.join(output_dir, "psd") if generate_psd else None
    pdf_dir = os.path.join(output_dir, "pdf") if generate_pdf else None

    if generate_pdf:
        r_installed = shutil.which("R") is not None
        try:
            import rpy2
            rpy2_installed = True
        except ImportError:
            rpy2_installed = False

        if not (r_installed and rpy2_installed):
            print("[WARNING] PDF generation skipped: R or rpy2 not available")
            generate_pdf = False
            pdf_dir = None

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = start + timedelta(days=duration_days)

    ispaq_script = "/home/thompsong/Developer/ispaq/run_ispaq.py"

    if not os.path.isfile(ispaq_script):
        raise FileNotFoundError(f"ISPAQ script not found at {ispaq_script}")

    cmd = [
        "python", ispaq_script,
        "--dataselect_url", sds_path,
        "--sds_files",
        "--station_url", stationxml_path,
        "--metrics", metrics,
        "--stations", stations,
        "--starttime", start.strftime("%Y-%m-%dT%H:%M:%S"),
        "--endtime", end.strftime("%Y-%m-%dT%H:%M:%S"),
        "--output", "csv",
        "--csv_dir", csv_dir,
        "--log-level", "DEBUG",
    ]

    if generate_psd:
        os.makedirs(psd_dir, exist_ok=True)
        cmd += ["--psd_dir", psd_dir]

    if generate_pdf:
        os.makedirs(pdf_dir, exist_ok=True)
        cmd += ["--pdf_dir", pdf_dir, "--pdf_type", "plot,text", "--pdf_interval", "daily"]
    cmd += ["--sncl_format", "N.S.L.C"]

    print("Running ISPAQ with cmyStations: IU.ANMO.10.BHZ.M, IU.*.00.BH?.M, IU.ANMO.*.?HZ, II.PFO.??.*ommand:")
    print(" ".join(cmd))

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("\n[STDOUT]\n" + result.stdout)
    print("\n[STDERR]\n" + result.stderr)
    if result.returncode != 0:
        print("[ERROR] ISPAQ failed")
        raise subprocess.CalledProcessError(result.returncode, cmd)

if __name__ == "__main__":
    sds_path = "/data/SDS_SAFE"
    stationxml_path="/data/KSC/EROSION/KSC_stations_patched.xml"
    start_date="2022-11-01"
    duration_days=1
    validate_data_availability(
        sds_path=sds_path,
        stationxml_path=stationxml_path,
        start_date=start_date,
        duration_days=duration_days,
        net_sta_pattern="FL.S39A1"
    )
    run_ispaq_on_sds(
        sds_path=sds_path,
        stationxml_path=stationxml_path,
        start_date=start_date,
        duration_days=duration_days,
        stations="FL.S39A1.*.H*",
        metrics=ALL_METRICS,
        generate_psd=True,
        generate_pdf=True
    )


