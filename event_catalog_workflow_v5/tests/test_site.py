"""kscrockets.site on a two-event sqlite: one processed event with plots, one with no data."""
import sqlite3

import pandas as pd

from kscrockets.site import build_site, event_summary

EVENT_COLUMNS = ("event_id event_type launch_designator event_time_utc event_time_source event_time_quality "
                 "event_time_precision time_definition event_time_basis consensus_time_utc consensus_time_source "
                 "consensus_time_precision known_time_utc known_time_source detected_time_utc detected_time_method "
                 "window_start_utc window_end_utc event_end_utc route window_start window_end name mission vehicle pad "
                 "provider launch_success landing_attempt landing_success landing_pad landing_type source source_url "
                 "notes time_spread_s time_conflict source_count").split()


def _db(tmp_path):
    ev = pd.DataFrame([{c: "" for c in EVENT_COLUMNS} | dict(event_id="ksc-a", event_type="orbital_launch",
                        event_time_utc="2020-01-01T00:00:00Z", event_time_basis="consensus", name="Rocket <A>", pad="LC40"),
                       {c: "" for c in EVENT_COLUMNS} | dict(event_id="ksc-b", event_type="scrub",
                        event_time_utc="2024-01-01T00:00:00Z", event_time_basis="consensus", name="Scrub B", pad="LC39A")])
    plot = tmp_path / "out/2020/ksc-a/plots/station_S1.png"
    plot.parent.mkdir(parents=True); plot.write_bytes(b"png")
    base = dict(event_id="ksc-a", seed_id="1R.S1.00.HDF", station="S1", channel="HDF", kind="pressure",
                distance_km=1.5, qc_flag="")
    meas = pd.DataFrame([base | dict(metric="peak", value=120.0, qc_flag="lower_bound"),
                         base | dict(metric="snr_peak", value=50.0), base | dict(metric="spl_peak_db", value=135.6),
                         base | dict(seed_id="1R.S2.00.HHZ", station="S2", kind="seismic_Z", metric="pgv", value=1e-3),
                         base | dict(seed_id="1R.S2.00.HHZ", station="S2", kind="seismic_Z", metric="snr_peak", value=2.0)])
    db = tmp_path / "c.sqlite"
    with sqlite3.connect(db) as con:
        ev.to_sql("events", con, index=False)
        pd.DataFrame(dict(event_id=["ksc-a", "ksc-b"], n_stations=[2, 0], archive=["/sds", ""],
                          stations=["1R.S1;1R.S2", ""])).to_sql("event_waveform_availability", con, index=False)
        pd.DataFrame([dict(event_id="ksc-a", run_id="r1", status="ok", detected_time_utc="2019-12-31T23:59:58Z",
                           detected_offset_s=-2.0, detected_used_by_catalog="True")]).to_sql("event_processing", con, index=False)
        meas.to_sql("measurements", con, index=False)
        pd.DataFrame([dict(event_id="ksc-a", product_type="station_waveform_spectrogram", path=str(plot), station="S1")]
                     ).to_sql("event_products", con, index=False)
    return db, meas


def test_site_pages_and_relative_plot_links(tmp_path):
    db, _ = _db(tmp_path)
    index = build_site(db, tmp_path / "out")
    html = index.read_text()
    assert "2 events" in html and "1 with waveform data" in html and "1 processed" in html
    assert "Rocket &lt;A&gt;" in html                                   # escaped
    a = (tmp_path / "out/site/events/ksc-a.html").read_text()
    assert "../../2020/ksc-a/plots/station_S1.png" in a                 # opens from disk
    assert "used by the catalog" in a and "120+" in a                    # lower bound marked
    b = (tmp_path / "out/site/events/ksc-b.html").read_text()
    assert "No day files in our archives" in b
    assert (tmp_path / "out/site/assets/app.js").exists()


def test_event_summary_ignores_low_snr_channels(tmp_path):
    _, meas = _db(tmp_path)
    s = event_summary(meas).set_index("event_id")
    assert s.at["ksc-a", "max_pa"] == 120.0 and bool(s.at["ksc-a", "max_pa_lower_bound"])
    assert s.at["ksc-a", "max_pgv"] != s.at["ksc-a", "max_pgv"]         # NaN: the seismic channel has SNR 2


def test_web_build_webp_plots_and_external_data_links(tmp_path):
    from PIL import Image
    db, _ = _db(tmp_path)
    Image.new("RGB", (2200, 600), "white").save(tmp_path / "out/2020/ksc-a/plots/station_S1.png")
    m = tmp_path / "out/2020/ksc-a/raw_counts.mseed"; m.write_bytes(b"x")
    with sqlite3.connect(db) as con:
        pd.DataFrame([dict(event_id="ksc-a", product_type="raw_counts_mseed", path=str(m), station="")]
                     ).to_sql("event_products", con, index=False, if_exists="append")
    url = "https://zenodo.org/records/1/files/ksc_event_waveforms_2020.zip?download=1"
    build_site(db, tmp_path / "out", web=True, waveform_urls={"2020": url})
    site = tmp_path / "out/site_web"
    a = (site / "events/ksc-a.html").read_text()
    assert "../plots/ksc-a/station_S1.webp" in a and "2020/ksc-a" not in a.replace("ksc_event_waveforms_2020", "")
    assert url in a and "ksc-a/raw_counts.mseed" in a                     # file inside the year zip
    w = Image.open(site / "plots/ksc-a/station_S1.webp")
    assert w.width == 1100 and (site / ".nojekyll").exists()


def test_package_waveforms_one_zip_per_year(tmp_path):
    import zipfile
    from kscrockets.package import package_waveforms
    for y, eid in (("2019", "ksc-a"), ("2019", "ksc-b"), ("2026", "ksc-c")):
        d = tmp_path / y / eid; d.mkdir(parents=True)
        (d / "manifest.json").write_text('{"run_id": "r1"}'); (d / "raw_counts.mseed").write_bytes(b"abc")
    idx = package_waveforms(tmp_path)
    assert sorted(idx.archive.unique()) == ["ksc_event_waveforms_2019.zip", "ksc_event_waveforms_2026.zip"]
    names = zipfile.ZipFile(tmp_path / "archive/ksc_event_waveforms_2019.zip").namelist()
    assert "ksc-b/raw_counts.mseed" in names and "README.txt" in names and len(idx.sha256.iloc[0]) == 64
