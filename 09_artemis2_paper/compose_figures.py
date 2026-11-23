"""Refresh the papers' figures from the notebook outputs and build the composites.

FIGURES lists every file in figures/ that the papers use (directly or inside a
composite) and the notebook output it comes from, relative to the Artemis II output
folder (artemis2.yaml `output`, or $ARTEMIS2_OUT_DIR). Each notebook writes into its
own subfolder, so same-named files from different notebooks (50 and 51) don't clash.

    python compose_figures.py            # copy the latest outputs, then build composites
    python compose_figures.py --no-copy  # only rebuild composites from figures/

Each composite stacks (or places side by side) PNGs from figures/ and adds panel
letters. The crackle and arrays figures are drawn natively by notebooks 55 and 60.
"""
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FIG = Path(__file__).resolve().parent / "figures"
FONT_PATHS = ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

FIGURES = {
    # figures/ name: source under the output folder
    "station_map.pdf": "25_make_plots/artemis2_infrasound_map_abs_peak.pdf",
    "clipping_timeline.png": "20_infrasound_clipping/clipping_timeline.png",
    "clipping_validation_B01.png": "20_infrasound_clipping/clipping_validation_B01.png",
    "data_overview.png": "22_data_overview/data_overview.png",
    "enclosure_summary.png": "30_enclosure_comparison/enclosure_summary.png",
    "enclosure_vs_frequency.png": "30_enclosure_comparison/enclosure_vs_frequency.png",
    "enclosure_B29__HDF_vs_B29__HDI.png": "30_enclosure_comparison/enclosure_B29__HDF_vs_B29__HDI.png",
    "trajectory.png": "35_synthetize/trajectory.png",
    "velocity_vs_time.png": "35_synthetize/velocity_vs_time.png",
    "synthetic_envelopes.png": "35_synthetize/synthetic_envelopes.png",
    "synthetic_amplitude_vs_distance.png": "35_synthetize/synthetic_amplitude_vs_distance.png",
    "synthetic_peaktime_vs_distance.png": "35_synthetize/synthetic_peaktime_vs_distance.png",
    "amplitude_field.png": "40_moving_source_amplitudes/amplitude_field.png",
    "model_data_directivity.png": "40_moving_source_amplitudes/model_data_directivity.png",
    "moving_source_directivity.png": "40_moving_source_amplitudes/moving_source_directivity.png",
    "moving_source_record_section.png": "40_moving_source_amplitudes/moving_source_record_section.png",
    "moving_source_reduced_pressure.png": "40_moving_source_amplitudes/moving_source_reduced_pressure.png",
    "snr_spectra.png": "42_signal_to_noise_spectra/snr_spectra.png",
    "snr_band_energy.png": "42_signal_to_noise_spectra/snr_band_energy.png",
    "bandwidth_psd.png": "45_sampling_rate_and_bandwidth/bandwidth_psd.png",
    "bandwidth_cumulative_energy.png": "45_sampling_rate_and_bandwidth/bandwidth_cumulative_energy.png",
    "bandwidth_simulated_sensors_B01.png": "45_sampling_rate_and_bandwidth/bandwidth_simulated_sensors_B01.png",
    "smartsolo_vs_trillium_B01_transfer.png": "45_sampling_rate_and_bandwidth/smartsolo_vs_trillium_B01_transfer.png",
    "smartsolo_vs_trillium_B01_waveforms.png": "45_sampling_rate_and_bandwidth/smartsolo_vs_trillium_B01_waveforms.png",
    "near_far.png": "48_near_far_figures/near_far.png",
    "near_far_centroid.png": "48_near_far_figures/near_far_centroid.png",
    "coupling_summary.png": "50_air_ground_coupling/coupling_summary.png",
    "coupling_transfer_functions.png": "50_air_ground_coupling/coupling_transfer_functions.png",
    "coupling_vs_time.png": "50_air_ground_coupling/coupling_vs_time.png",
    "crackle_figure.png": "55_crackle/crackle_figure.png",
    "arrays_figure.png": "60_array_tracking/arrays_figure.png",
}

COMPOSITES = {
    # name: (layout, [panel files])
    "composite_overflow": ("row", ["clipping_timeline", "clipping_validation_B01"]),
    "composite_enclosure": ("column", ["enclosure_summary", "enclosure_vs_frequency"]),
    "composite_bandwidth": ("column", ["bandwidth_cumulative_energy", "bandwidth_simulated_sensors_B01"]),
    "composite_near_far": ("column", ["near_far", "near_far_centroid"]),
}


def copy_figures():
    """Copy each FIGURES source into figures/; return the names whose source is missing."""
    sys.path.insert(0, str(FIG.parent))
    import artemis2_config as cfg
    missing = []
    for name, src in FIGURES.items():
        src = cfg.OUT_DIR / src
        if src.exists():
            shutil.copy2(src, FIG / name)
        else:
            missing.append(f"{name} <- {src}")
    print(f"copied {len(FIGURES) - len(missing)} of {len(FIGURES)} figures from {cfg.OUT_DIR}")
    for m in missing:
        print("  MISSING", m)
    return missing


def font(size):
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def compose(layout, names, gap=40, margin=70):
    ims = [Image.open(FIG / f"{n}.png").convert("RGB") for n in names]
    if layout == "row":
        h = max(im.height for im in ims)
        ims = [im.resize((round(im.width * h / im.height), h), Image.LANCZOS) for im in ims]
        W = sum(im.width for im in ims) + gap * (len(ims) - 1)
        out = Image.new("RGB", (W, h + margin), "white")
        x = 0
        pos = []
        for im in ims:
            out.paste(im, (x, margin)); pos.append((x, 0)); x += im.width + gap
    else:
        w = max(im.width for im in ims)
        ims = [im.resize((w, round(im.height * w / im.width)), Image.LANCZOS) for im in ims]
        H = sum(im.height + margin for im in ims) + gap * (len(ims) - 1)
        out = Image.new("RGB", (w, H), "white")
        y = 0
        pos = []
        for im in ims:
            out.paste(im, (0, y + margin)); pos.append((0, y)); y += im.height + margin + gap
    d = ImageDraw.Draw(out)
    f = font(margin - 14)
    for i, (x, y) in enumerate(pos):
        d.text((x + 10, y + 4), f"({chr(97 + i)})", fill="black", font=f)
    return out


if __name__ == "__main__":
    if "--no-copy" not in sys.argv:
        copy_figures()
    for name, (layout, names) in COMPOSITES.items():
        compose(layout, names).save(FIG / f"{name}.png", dpi=(200, 200))
        print("wrote", name)
