from pathlib import Path
from obspy import read

root = Path("data/waveforms/raw")

for mseed in sorted(root.glob("*/*/raw.mseed")):
    st = read(str(mseed), headonly=True)

    stations = sorted({tr.stats.station for tr in st})
    channels = sorted({tr.id for tr in st})

    print(
        mseed.parent.parent.name,
        f"stations={stations}",
        f"channels={len(channels)}",
        f"segments={len(st)}",
    )


import json
from pathlib import Path

root = Path("data/waveforms/raw/ksc-bb9fcefb0a9c")

for manifest in root.glob("*/extraction.json"):
    print("\nManifest:", manifest)
    data = json.loads(manifest.read_text())

    print(json.dumps(data.get("request", {}), indent=2))

import json
from pathlib import Path

manifest = Path(
    "data/waveforms/raw/"
    "ksc-bb9fcefb0a9c/"
    "a7f1277dfd71/"
    "extraction.json"
)

data = json.loads(manifest.read_text())

print("Top-level keys:", list(data.keys()))
print(json.dumps(data, indent=2))
