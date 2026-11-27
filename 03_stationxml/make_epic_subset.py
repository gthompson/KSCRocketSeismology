"""Write the 2016-2022 part of KSC.xml (networks 1R and AM) for the EarthScope archive of 1R_2016.

    python 03_stationxml/make_epic_subset.py   ->  03_stationxml/KSC_1R_2016-2022.xml
"""
import copy
from pathlib import Path

from obspy import UTCDateTime, read_inventory

HERE = Path(__file__).resolve().parent
CUT = UTCDateTime(2023, 1, 1)
inv = read_inventory(str(HERE / "KSC.xml"))
out = copy.deepcopy(inv)
out.networks = [n for n in out.networks if n.code in ("1R", "AM")]
for n in out:
    for s in n:
        s.channels = [c for c in s.channels if c.start_date < CUT]
    n.stations = [s for s in n.stations if s.channels and s.start_date < CUT]
out.source = "build_ksc_stationxml.py (ksc_stations_master_v3.xlsx); 1R and AM epochs starting before 2023"
path = HERE / "KSC_1R_2016-2022.xml"
out.write(str(path), format="STATIONXML", validate=True)
print(path.name, sum(len(s) for n in out for s in n), "channel epochs,", sum(len(n) for n in out), "station epochs")
