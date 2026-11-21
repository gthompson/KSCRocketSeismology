"""Combine notebook figures into labelled multi-panel figures for the two papers.

Each composite stacks (or places side by side) PNGs from the figures/ folder and adds
panel letters. Run after copying the notebook outputs into figures/:

    python compose_figures.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FIG = Path(__file__).resolve().parent / "figures"
FONT_PATHS = ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

COMPOSITES = {
    # name: (layout, [panel files])
    "composite_overflow": ("row", ["clipping_timeline", "clipping_validation_B01"]),
    "composite_enclosure": ("column", ["enclosure_summary", "enclosure_vs_frequency"]),
    "composite_bandwidth": ("column", ["bandwidth_cumulative_energy", "bandwidth_simulated_sensors_B01"]),
    "composite_arrays": ("row", ["array_backazimuth", "array_map"]),
    "composite_crackle": ("row", ["crackle_waveforms", "crackle_vs_source_time"]),
    "composite_near_far": ("column", ["near_far", "near_far_centroid"]),
}


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
    for name, (layout, names) in COMPOSITES.items():
        compose(layout, names).save(FIG / f"{name}.png", dpi=(200, 200))
        print("wrote", name)
