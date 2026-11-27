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
