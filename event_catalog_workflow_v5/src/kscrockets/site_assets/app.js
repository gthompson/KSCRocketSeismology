// Event catalog: filters on the index page, click-to-sort on every table.sortable.
(function () {
  function cellValue(td) {
    const v = td.dataset.v !== undefined ? td.dataset.v : td.textContent.trim();
    const n = parseFloat(v.replace(/[^0-9eE.+-]/g, ""));
    return v === "" ? null : (isNaN(n) || /[a-df-z]/i.test(v.replace(/e[+-]?\d/i, "")) ? v.toLowerCase() : n);
  }
  document.querySelectorAll("table.sortable").forEach(function (table) {
    table.querySelectorAll("th").forEach(function (th, col) {
      th.addEventListener("click", function () {
        const asc = !th.classList.contains("sorted-asc");
        table.querySelectorAll("th").forEach(function (h) { h.classList.remove("sorted-asc", "sorted-desc"); });
        th.classList.add(asc ? "sorted-asc" : "sorted-desc");
        const body = table.tBodies[0];
        const rows = Array.from(body.rows);
        rows.sort(function (a, b) {
          const x = cellValue(a.cells[col]), y = cellValue(b.cells[col]);
          if (x === null && y === null) return 0;
          if (x === null) return 1;          // blanks last either way
          if (y === null) return -1;
          const c = (typeof x === "number" && typeof y === "number") ? x - y : String(x).localeCompare(String(y));
          return asc ? c : -c;
        });
        rows.forEach(function (r) { body.appendChild(r); });
      });
    });
  });

  if (typeof ROWS === "undefined") return;
  const q = document.getElementById("q"), year = document.getElementById("f-year"),
        type = document.getElementById("f-type"), pad = document.getElementById("f-pad"),
        data = document.getElementById("f-data"), count = document.getElementById("count");
  const rows = Array.from(document.querySelectorAll("#catalog tbody tr"));
  const params = new URLSearchParams(location.hash.slice(1));
  [["q", q], ["year", year], ["type", type], ["pad", pad], ["data", data]].forEach(function (p) {
    if (params.get(p[0])) p[1].value = params.get(p[0]);
  });
  function apply() {
    const s = q.value.trim().toLowerCase();
    let n = 0;
    rows.forEach(function (tr) {
      const r = ROWS[+tr.dataset.i];
      const ok = (!year.value || r.year === year.value) && (!type.value || r.type === type.value) &&
                 (!pad.value || r.pad === pad.value) && (!data.value || r[data.value]) &&
                 (!s || tr.textContent.toLowerCase().includes(s) || tr.innerHTML.toLowerCase().includes(s));
      tr.hidden = !ok; if (ok) n++;
    });
    count.textContent = n + " shown";
    const h = new URLSearchParams();
    [["q", q], ["year", year], ["type", type], ["pad", pad], ["data", data]].forEach(function (p) { if (p[1].value) h.set(p[0], p[1].value); });
    history.replaceState(null, "", h.toString() ? "#" + h.toString() : location.pathname);
  }
  [q, year, type, pad, data].forEach(function (el) { el.addEventListener("input", apply); });
  apply();
})();

// Event page: station map (Leaflet, loaded only on pages with EVENT_MAP).
(function () {
  if (typeof EVENT_MAP === "undefined" || typeof L === "undefined") return;
  const el = document.getElementById("map"); if (!el) return;
  const map = L.map(el, { scrollWheelZoom: false });
  const osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    { maxZoom: 18, attribution: "© OpenStreetMap contributors" });
  const sat = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 18, attribution: "Imagery © Esri" });
  sat.addTo(map);
  L.control.layers({ "Satellite": sat, "Map": osm }).addTo(map);
  L.control.scale({ imperial: false }).addTo(map);
  const pts = [];
  EVENT_MAP.stations.forEach(function (s) {
    const color = s.p >= 3 ? "#2b6cb0" : (s.s >= 3 ? "#2f9e44" : "#adb5bd");
    const m = L.circleMarker([s.lat, s.lon], { radius: 6, color: "#222", weight: 1, fillColor: color, fillOpacity: 0.95 }).addTo(map);
    m.bindTooltip(s.name, { permanent: true, direction: "right", className: "sta", offset: [6, 0] });
    m.bindPopup("<b>" + (s.net ? s.net + "." : "") + s.name + "</b><br>" + s.km + " km from the pad<br>best SNR: pressure " +
                (s.p || "–") + ", seismic " + (s.s || "–") + "<br><a href='#sta-" + s.name + "'>waveforms ↓</a>");
    pts.push([s.lat, s.lon]);
  });
  if (EVENT_MAP.pad) {
    const p = EVENT_MAP.pad;
    L.marker([p.lat, p.lon], { icon: L.divIcon({ className: "", html: "<div style='font-size:22px;color:#e8590c;text-shadow:0 0 3px #000'>★</div>", iconSize: [22, 22], iconAnchor: [11, 13] }) })
      .bindTooltip("Pad " + p.name, { direction: "top" }).addTo(map);
    pts.push([p.lat, p.lon]);
  }
  (EVENT_MAP.sites || []).forEach(function (w) {
    L.marker([w.lat, w.lon], { icon: L.divIcon({ className: "", html: "<div style='font-size:15px;color:#f8f9fa;text-shadow:0 0 3px #000'>◆</div>", iconSize: [15, 15], iconAnchor: [7, 8] }) })
      .bindTooltip(w.name, { direction: "top" }).addTo(map);
  });
  if (pts.length > 1) map.fitBounds(pts, { padding: [30, 30], maxZoom: 14 }); else map.setView(pts[0], 12);
})();
