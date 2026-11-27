"""Weather at each event: KSC Spaceport Weather Archive towers and wind profilers, airport METARs.

    ksc-rockets fetch-weather --events-file data/products/pilot_events.txt

For each event the files closest in time are downloaded once and kept under
``<out_root>/weather/`` (raw, as served); a one-row summary per event goes to
``<out_root>/tables/event_weather.csv`` and the sqlite table ``event_weather``:

* KSC weather towers (https://kscweather.ksc.nasa.gov/wxarchive, product ``midds/WINDS_TOWER``,
  1-minute files; ``WINDS_TOWER_5MIN`` when no 1-minute file is near): the minute closest to the
  event. Surface values = mean over towers of the lowest temperature/RH sensor (6 ft) and the
  vector mean of each tower's lowest wind sensor; also the tower nearest the pad.
* Airports (Iowa Environmental Mesonet ASOS service): the METAR closest to the event at the
  Cape Canaveral Skid Strip (XMR), else the Shuttle Landing Facility (TTS), Titusville (TIX),
  Patrick (COF), Melbourne (MLB).
* Wind profilers, saved for later analysis (not summarised yet): the 915 MHz boundary-layer
  profilers (``midds/915MHZ_WIND``, 15-min files, one per site prefix Q1..Q5) and the 48 MHz
  TDRWP (``midds/DRWP_5MIN``, hourly files), the file closest to the event of each.

The KSC archive states its data are not quality controlled; 999 marks missing values.
"""
from __future__ import annotations

import io
import math
import re
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

KSC = "https://kscweather.ksc.nasa.gov/wxarchive"
IEM = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
AIRPORTS = ("XMR", "TTS", "TIX", "COF", "MLB")       # fetched; ties go to the earlier (nearer the pads)
CAPE_AIRPORTS = ("XMR", "TTS", "TIX", "COF")           # within ~25 km of the pads; MLB (40 km) only as fallback
USER_AGENT = "ksc-rocket-catalog/0.1 (seismo-acoustic research catalog)"
STAMP = re.compile(r"(\d{12})\.dat$", re.I)                  # WT_1MIN_YYYYMMDDHHMM.dat (2023-)
LEGACY_STAMP = re.compile(r"^[A-Z]\d(\d{8})\.dat$", re.I)     # T1MMDDHHMM.dat, M5..., M6..., Q1..., M7...
LEGACY_TIME = re.compile(r"WIND TOWER DATA\s+(\d{4})Z\s+(\d{1,2}) (\w{3}) (\d{2})")
TOWER_PRODUCTS = (("WINDS_TOWER", ("WT_1MIN", "T1"), 900, "1 min"),
                  ("WINDS_TOWER_5MIN", ("WT_5MIN", "M6"), 3600, "5 min"),
                  ("WINDS_TOWER", ("M5",), 3600, "5 min"))
WEATHER_COLUMNS = [
    "event_id", "event_time_utc",
    "tower_product", "tower_obs_utc", "tower_offset_s", "tower_n", "tower_temp_c", "tower_rh_pct",
    "tower_temp_height_ft", "tower_wind_speed_mps", "tower_wind_from_deg", "tower_wind_heights_ft",
    "near_tower", "near_tower_km", "near_tower_temp_c", "near_tower_rh_pct", "near_tower_wind_speed_mps",
    "near_tower_wind_from_deg", "near_tower_wind_height_ft", "near_tower_lat", "near_tower_lon",
    "airport", "airport_obs_utc", "airport_offset_s", "airport_temp_c", "airport_rh_pct",
    "airport_wind_speed_mps", "airport_wind_from_deg", "airport_metar", "airport_lat", "airport_lon",
    "profiler_files", "files", "error"]


def _ksclib_weather():
    src = Path(__file__).resolve().parents[3] / "ksclib" / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from ksclib import weather
    return weather


def _utc(t) -> pd.Timestamp:
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def file_time(name: str, folder: str) -> pd.Timestamp | None:
    """UTC time stamp of an archive file name; the legacy names carry no year, taken from the
    folder (/midds/<product>/YYYY/MM/DD)."""
    m = STAMP.search(name)
    if m:
        return pd.Timestamp(m.group(1)[:8] + "T" + m.group(1)[8:], tz="UTC")
    m = LEGACY_STAMP.match(name)
    if m:
        year = re.search(r"/(\d{4})/\d{2}/\d{2}$", folder)
        if year:
            st = m.group(1)
            return pd.Timestamp(f"{year.group(1)}-{st[:2]}-{st[2:4]}T{st[4:6]}:{st[6:8]}", tz="UTC")
    return None


def load_ksc_tower_legacy(filenames, coords: pd.DataFrame, *, prevailing_side_only: bool = True) -> pd.DataFrame:
    """Read the fixed-width tower files of the archive before 2023 (``T1MMDDHHMM.dat`` 1-minute,
    ``M5``/``M6`` 5-minute): several time blocks per file, each headed "WIND TOWER DATA hhmmZ dd MON
    yy", one line per tower and height ("0002 NW  SE": tower, sensor side, prevailing side; "39 B NW",
    "SLC 40"). No coordinates in these files: they come from `coords` (tower, lat, lon; the 2026
    tower list). Returns the columns of ksclib.weather.load_ksc_tower_1min."""
    w = _ksclib_weather()
    if isinstance(filenames, (str, Path)):
        filenames = [filenames]
    xy = {str(r.tower): (float(r.lat), float(r.lon)) for r in coords.itertuples()}
    rows = []
    for f in filenames:
        when, ends = None, None
        for line in Path(f).read_text(errors="replace").splitlines():
            m = LEGACY_TIME.search(line)
            if m:
                hhmm, dd, mon, yy = m.groups()
                when = pd.Timestamp(f"{dd} {mon} 20{yy} {hhmm[:2]}:{hhmm[2:]}", tz="UTC")
                continue
            if line.startswith("TOWER") and "HGT" in line:
                # fields are right-aligned and end where their header names end:
                # TOWER HGT AV DIR SPD DIR SPD DIR SPD DEV TMP DIF DP RH PRE
                ends, pos = [], 0
                for name in line.split():
                    pos = line.index(name, pos) + len(name); ends.append(pos)
                continue
            if when is None or ends is None or len(ends) < 14 or len(line) < 20 or not line[:4].strip():
                continue
            field = lambda i: line[ends[i - 1]:ends[i]].strip() if i > 1 else line[12:ends[1]].strip()  # noqa: E731
            hgt = field(1)
            if not hgt.isdigit():
                continue
            tid = line[:12]
            ddir, spd, tmp, rh = field(3), field(4), field(10), field(13)
            key = tid.split()
            numbered = key[0].isdigit() and len(key[0]) == 4          # "0002 NW  SE": tower, side, prevailing
            if numbered:
                tower, side, prev = key[0], (key[1] if len(key) > 1 else ""), (key[2] if len(key) > 2 else "")
            elif key[0] == "SLC":                                      # "SLC 40"
                tower, side, prev = "LC" + key[1], "", ""
            else:                                                      # "39 B NW": LC-39B, NW side
                tower, side, prev = "LC" + "".join(key[:2]), (key[2] if len(key) > 2 else ""), ""
            if prevailing_side_only and prev and side and side != prev:
                continue
            rows.append(dict(station=tower, sensor_side=side, datetime_utc=when, height_ft=hgt,
                             temperature_f=tmp, relative_humidity_percent=rh, wind_direction_from_deg=ddir, wind_speed_knots=spd))
    if not rows:
        return pd.DataFrame(columns=["station", "datetime_utc"])
    d = pd.DataFrame(rows)
    for c in ("height_ft", "temperature_f", "relative_humidity_percent", "wind_direction_from_deg", "wind_speed_knots"):
        d[c] = pd.to_numeric(d[c], errors="coerce").mask(lambda x: x >= 999)
    d["wind_direction_from_deg"] = d.wind_direction_from_deg % 360.0

    def where(r):
        for k in (r.station + r.sensor_side, r.station, r.station + "N", r.station + "NW", r.station + "NE"):
            if k in xy:
                return xy[k]
        return (np.nan, np.nan)
    ll = [where(r) for r in d.itertuples()]
    d["tower_latitude"] = [a for a, _ in ll]; d["tower_longitude"] = [b for _, b in ll]
    d["height_m"] = d.height_ft * w.FOOT_TO_M
    d["temperature_c"] = (d.temperature_f - 32.0) * 5.0 / 9.0
    d["wind_speed_mps"] = d.wind_speed_knots * w.KNOT_TO_MPS
    rad = np.deg2rad(d.wind_direction_from_deg)
    d["wind_u_east_mps"] = -d.wind_speed_mps * np.sin(rad)
    d["wind_v_north_mps"] = -d.wind_speed_mps * np.cos(rad)
    return d.drop_duplicates(["station", "height_ft", "datetime_utc"]).reset_index(drop=True)


def load_towers(files, coords: pd.DataFrame) -> pd.DataFrame:
    """Tower files of either format, one row per tower, height and time step."""
    w = _ksclib_weather()
    new = [f for f in files if Path(f).name.upper().startswith("WT_")]
    old = [f for f in files if f not in new]
    frames = []
    if new:
        frames.append(w.load_ksc_tower_1min(new))
    if old:
        frames.append(load_ksc_tower_legacy(old, coords))
    frames = [f for f in frames if len(f)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["station", "datetime_utc"])


def _km(lat0, lon0, lat1, lon1) -> float:
    r = 6371.0
    p0, p1 = math.radians(lat0), math.radians(lat1)
    a = math.sin((p1 - p0) / 2) ** 2 + math.cos(p0) * math.cos(p1) * math.sin(math.radians(lon1 - lon0) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class KSCArchive:
    """Client of the archive's Explorer pages: list a folder, download up to 15 files as a zip."""

    def __init__(self, cache: Path, pause_s: float = 0.5):
        import requests
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.cache = Path(cache)
        self.pause = pause_s
        self._listing: dict[str, list[str]] = {}
        self.s.get(f"{KSC}/Explorer/LandingIndex", params={"path": r"midds\WINDS_TOWER"}, timeout=60)

    def list(self, folder: str) -> list[str]:
        """File (or sub-folder) names in an archive folder such as /midds/WINDS_TOWER/2026/03/14."""
        if folder not in self._listing:
            r = self.s.post(f"{KSC}/Explorer/GetFiles", data={"path": folder}, timeout=60)
            r.raise_for_status()
            self._listing[folder] = re.findall(r'name="fileCheck"[^>]*type="checkbox" value="([^"]+)"', r.text)
            time.sleep(self.pause)
        return self._listing[folder]

    def local(self, path: str) -> Path:
        return self.cache / path.strip("/")

    def fetch(self, paths: list[str]) -> list[Path]:
        """Download archive files (full paths) not already cached; returns their local paths."""
        want = [p for p in paths if not self.local(p).exists()]
        for i in range(0, len(want), 15):
            chunk = want[i:i + 15]
            self.s.post(f"{KSC}/Explorer/LoadActionLinks",
                        data={"path": "", **{f"list[{k}]": p for k, p in enumerate(chunk)}}, timeout=60)
            r = self.s.get(f"{KSC}/Explorer/Download", params={"jlist": ""}, timeout=300)
            r.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(r.content))
            names = {Path(n).name: n for n in z.namelist()}
            for p in chunk:
                n = names.get(Path(p).name)
                if n is not None:
                    out = self.local(p)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(z.read(n))
            time.sleep(self.pause)
        return [self.local(p) for p in paths if self.local(p).exists()]

    def nearest(self, product: str, t: pd.Timestamp, prefix="", max_dt_s: float = 3600,
                n: int = 1) -> list[tuple[str, float]]:
        """The `n` files of `product` with a time stamp closest to `t` (same and adjacent UTC days),
        as (full path, offset s = file time - t), within `max_dt_s`."""
        cands = []
        for day in (t - pd.Timedelta(days=1), t, t + pd.Timedelta(days=1)):
            folder = f"/midds/{product}/{day:%Y/%m/%d}"
            try:
                names = self.list(folder)
            except Exception:
                continue
            for name in names:
                if prefix and not name.upper().startswith(tuple(p.upper() for p in ((prefix,) if isinstance(prefix, str) else prefix))):
                    continue
                ft = file_time(name, folder)
                if ft is None:
                    continue
                dt = (ft - t).total_seconds()
                if abs(dt) <= max_dt_s:
                    cands.append((f"{folder}/{name}", dt))
        return sorted(cands, key=lambda c: abs(c[1]))[:n]


def fetch_airports(t: pd.Timestamp, cache: Path, hours: float = 3.0) -> Path | None:
    """IEM ASOS METARs of AIRPORTS within `hours` of `t` (cached CSV)."""
    import requests
    out = Path(cache) / "airports" / f"asos_{t:%Y%m%dT%H%M}.csv"
    if out.exists():
        return out
    a, b = t - pd.Timedelta(hours=hours), t + pd.Timedelta(hours=hours)
    params = [("station", s) for s in AIRPORTS] + [("data", d) for d in ("tmpf", "dwpf", "relh", "drct", "sknt", "gust", "mslp", "metar")]
    params += [("tz", "Etc/UTC"), ("format", "onlycomma"), ("latlon", "yes"), ("missing", "M"), ("trace", "T"),
               ("report_type", "3"), ("report_type", "4"),
               ("sts", a.strftime("%Y-%m-%dT%H:%MZ")), ("ets", b.strftime("%Y-%m-%dT%H:%MZ"))]
    r = requests.get(IEM, params=params, headers={"User-Agent": USER_AGENT}, timeout=120)
    r.raise_for_status()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(r.text)
    return out


def _r(x, nd=1):
    """Rounded float, None for NaN/None (nd=0 gives an int)."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(x):
        return None
    return int(round(x)) if nd == 0 else round(x, nd)


def _vector_mean(speed, from_deg):
    speed, d = np.asarray(speed, float), np.deg2rad(np.asarray(from_deg, float))
    u, v = np.nanmean(-speed * np.sin(d)), np.nanmean(-speed * np.cos(d))
    return math.hypot(u, v), (math.degrees(math.atan2(-u, -v)) % 360.0)


def tower_summary(towers: pd.DataFrame, pad_lat=None, pad_lon=None) -> dict:
    """Surface values from one time step of tower data (ksclib.weather.load_ksc_tower_1min)."""
    t = towers.dropna(subset=["tower_latitude"])
    temp = t.dropna(subset=["temperature_c"])
    low_t = temp[temp.height_ft == temp.groupby("station").height_ft.transform("min")]
    low_t = low_t[low_t.height_ft <= 10] if (low_t.height_ft <= 10).any() else low_t
    wind = t.dropna(subset=["wind_speed_knots", "wind_direction_from_deg"])
    low_w = wind[wind.height_ft == wind.groupby("station").height_ft.transform("min")]
    low_w = low_w[low_w.height_ft <= 60]
    out = dict(tower_n=int(low_t.station.nunique()),
               tower_temp_c=_r(low_t.temperature_c.mean(), 1) if len(low_t) else None,
               tower_rh_pct=_r(low_t.relative_humidity_percent.mean(), 0) if len(low_t) else None,
               tower_temp_height_ft=",".join(str(int(h)) for h in sorted(low_t.height_ft.unique())))
    if len(low_w):
        sp, dr = _vector_mean(low_w.wind_speed_mps, low_w.wind_direction_from_deg)
        out.update(tower_wind_speed_mps=round(sp, 1), tower_wind_from_deg=round(dr),
                   tower_wind_heights_ft=",".join(str(int(h)) for h in sorted(low_w.height_ft.unique())))
    if pad_lat is not None and len(t):
        st = t.groupby("station").agg(lat=("tower_latitude", "first"), lon=("tower_longitude", "first")).reset_index()
        st["km"] = [_km(pad_lat, pad_lon, a, b) for a, b in zip(st.lat, st.lon)]
        # nearest tower that has both a temperature and a wind
        ok = set(low_t.station) & set(low_w.station)
        st = st[st.station.isin(ok)].sort_values("km") if ok else st.sort_values("km")
        if len(st):
            n = st.iloc[0]
            tt = low_t[low_t.station == n.station]; ww = low_w[low_w.station == n.station]
            out.update(near_tower=n.station, near_tower_km=_r(n.km, 2), near_tower_lat=n.lat, near_tower_lon=n.lon,
                       near_tower_temp_c=_r(tt.temperature_c.mean(), 1) if len(tt) else None,
                       near_tower_rh_pct=_r(tt.relative_humidity_percent.mean(), 0) if len(tt) else None)
            if len(ww):
                w = ww.iloc[0]
                out.update(near_tower_wind_speed_mps=_r(w.wind_speed_mps, 1),
                           near_tower_wind_from_deg=_r(w.wind_direction_from_deg, 0),
                           near_tower_wind_height_ft=int(w.height_ft))
    return out


def airport_summary(asos: pd.DataFrame, t: pd.Timestamp) -> dict:
    """The METAR closest in time to `t` among the Cape airports (CAPE_AIRPORTS; Melbourne only if
    none of them reported); ties go to the airport nearer the pads."""
    if asos.empty:
        return {}
    a = asos.dropna(subset=["temperature_c"]).copy()
    if a.empty:
        return {}
    a["offset_s"] = (a.datetime_utc - t).dt.total_seconds()
    cape = a[a.station.isin(CAPE_AIRPORTS)]
    a = cape if len(cape) else a
    a = a.assign(rank=a.station.map({c: i for i, c in enumerate(AIRPORTS)}).fillna(99), absdt=a.offset_s.abs())
    pick = a.sort_values(["absdt", "rank"]).iloc[0]
    return dict(airport=pick.station, airport_obs_utc=pick.datetime_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                airport_offset_s=_r(pick.offset_s, 0), airport_temp_c=_r(pick.temperature_c, 1),
                airport_rh_pct=_r(pick.relative_humidity_percent, 0) if pick.relative_humidity_percent == pick.relative_humidity_percent else None,
                airport_wind_speed_mps=_r(pick.wind_speed_mps, 1) if pick.wind_speed_mps == pick.wind_speed_mps else None,
                airport_wind_from_deg=_r(pick.wind_direction_from_deg, 0) if pick.wind_direction_from_deg == pick.wind_direction_from_deg else None,
                airport_metar=str(pick.get("metar", "")), airport_lat=pick.tower_latitude, airport_lon=pick.tower_longitude)


def _towers_near(archive: KSCArchive, t: pd.Timestamp, pad_lat, pad_lon, files: list, coords) -> dict:
    """Tower time step closest to `t`: 1-minute data if any within 15 min, else 5-minute data."""
    for product, prefixes, max_dt, label in TOWER_PRODUCTS:
        near = archive.nearest(product, t, prefix=prefixes, max_dt_s=max_dt, n=4)
        if not near:
            continue
        local = archive.fetch([p for p, _ in near])
        towers = load_towers(local, coords)
        if towers.empty:
            continue
        times = pd.Series(sorted(towers.datetime_utc.unique()))
        obs = times.iloc[(times - t).abs().argmin()]
        files += [str(p) for p in local]
        out = dict(tower_product=f"{product} ({label})", tower_obs_utc=pd.Timestamp(obs).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   tower_offset_s=round((pd.Timestamp(obs) - t).total_seconds()))
        out.update(tower_summary(towers[towers.datetime_utc == obs], pad_lat, pad_lon))
        return out
    return {}


def event_weather(event: dict, cache: Path, archive: KSCArchive | None, pad_lat=None, pad_lon=None,
                  coords: pd.DataFrame | None = None) -> dict:
    """Fetch (or reuse) the weather files closest to one event and summarise them."""
    w = _ksclib_weather()
    t = _utc(event["event_time_utc"])
    if coords is None:
        coords = pd.read_csv(Path(__file__).resolve().parents[2] / "data/raw/ksc_weather_towers.csv", dtype={"tower": str})
    row = dict(event_id=event["event_id"], event_time_utc=t.strftime("%Y-%m-%dT%H:%M:%SZ"))
    files, errors = [], []
    if archive is not None:
        try:
            row.update(_towers_near(archive, t, pad_lat, pad_lon, files, coords))
            if "tower_obs_utc" not in row:
                errors.append("no tower data within 1 h")
        except Exception as exc:                      # archive down or format change: keep going
            errors.append(f"towers: {exc}")
        try:
            prof = []
            for q in ("Q1", "Q2", "Q3", "Q4", "Q5"):
                prof += archive.nearest("915MHZ_WIND", t, prefix=q, max_dt_s=1800)
            prof += archive.nearest("DRWP_5MIN", t, max_dt_s=3600)
            got = archive.fetch([p for p, _ in prof])
            row["profiler_files"] = ";".join(f"{Path(p).name}@{dt:+.0f}s" for p, dt in prof)
            files += [str(p) for p in got]
        except Exception as exc:
            errors.append(f"profilers: {exc}")
    try:
        f = fetch_airports(t, cache)
        if f is not None:
            raw = pd.read_csv(f, na_values=["M", "T"])
            asos = w.load_iem_asos_csv(f)
            if "metar" in raw:
                asos["metar"] = raw["metar"].values
            row.update(airport_summary(asos, t))
            files.append(str(f))
    except Exception as exc:
        errors.append(f"airports: {exc}")
    row["files"] = ";".join(files)
    row["error"] = " | ".join(errors)
    return row


def save_weather(tables: Path, rows: list[dict]) -> Path:
    """Upsert per-event weather rows into <tables>/event_weather.csv."""
    p = Path(tables) / "event_weather.csv"
    new = pd.DataFrame(rows, columns=WEATHER_COLUMNS)
    if p.exists() and p.stat().st_size:
        old = pd.read_csv(p, dtype=str, keep_default_na=False)
        old = old[~old.event_id.isin(new.event_id)]
        new = pd.concat([old, new.astype(object)], ignore_index=True)
    p.parent.mkdir(parents=True, exist_ok=True)
    new.sort_values("event_time_utc").to_csv(p, index=False)
    return p
