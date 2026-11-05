/* =============================================================
   Zomato Bangalore Command Center: front end
   Live data from Power BI Desktop (DAX over ADOMD) via the Flask API.
   ============================================================= */
(() => {
"use strict";

const C = {
  red: "#E23744", red600: "#CB2A38", red700: "#A3121F", red800: "#7E0D18",
  red300: "#EE7B85", red200: "#F6B3B9", red100: "#FCE1E4", red50: "#FFF5F6",
  ink: "#1D1D22", ink2: "#4A4B54", muted: "#8B8C96", line: "#EEEEF1",
};
// Online ordering: ordinal pair (validated light->dark): No = light, Yes = deep
const ONLINE = { No: C.red300, Yes: C.red700 };

// UI filter key <-> model column (mirrors queries.FILTER_COLUMNS)
const FILTER_COL = {
  location: "location", format: "primary_rest_type", cuisine: "primary_cuisine",
  listing: "listed_in(type)", online: "online_order", booking: "book_table",
  cost: "Cost_Bracket", rating: "Rating_Bracket",
};
const FILTER_LABEL = {
  location: "Location", format: "Format", cuisine: "Cuisine", listing: "Listing",
  online: "Online ordering", booking: "Table booking", cost: "Price tier", rating: "Rating",
};

const state = {
  filters: readHash(),
  data: null,
  status: null,
  views: {},          // chart key -> "chart" | "table" | "dax"
  lastJson: "",
  animate: true,
  loading: false,
};

/* ---------------- utils ---------------- */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtInt = (v) => v == null ? "—" : Math.round(v).toLocaleString("en-IN");
const fmtCompact = (v) => {
  if (v == null) return "—";
  const a = Math.abs(v);
  if (a >= 1e7) return (v / 1e7).toFixed(2).replace(/\.?0+$/, "") + " Cr";
  if (a >= 1e5) return (v / 1e5).toFixed(1).replace(/\.0$/, "") + " L";
  if (a >= 1e3) return (v / 1e3).toFixed(1).replace(/\.0$/, "") + "K";
  return String(Math.round(v));
};
const fmtCompactIntl = (v) => {
  if (v == null) return "—";
  const a = Math.abs(v);
  if (a >= 1e6) return (v / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
  if (a >= 1e3) return (v / 1e3).toFixed(1).replace(/\.0$/, "") + "K";
  return String(Math.round(v));
};
const fmtRate = (v) => v == null ? "—" : v.toFixed(2);
const fmtPct = (v, d = 1) => v == null ? "—" : (v * 100).toFixed(d) + "%";
const fmtRs = (v) => v == null ? "—" : "₹" + Math.round(v).toLocaleString("en-IN");
const fmtSigned = (v) => v == null ? "—" : (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(2);
const shortLabel = (s, n = 18) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
const stripParen = (s) => s.replace(/\s*\(.*?\)\s*/g, " ").trim();

function niceTicks(min, max, count = 5) {
  const span = max - min || 1;
  const step0 = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const err = step0 / mag;
  const step = (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1) * mag;
  const lo = Math.floor(min / step) * step, hi = Math.ceil(max / step) * step;
  const out = [];
  for (let v = lo; v <= hi + step / 2; v += step) out.push(+v.toFixed(10));
  return out;
}
const scale = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);

// rounded data-end bar path (square at the baseline)
function barV(x, y, w, h, r = 4) {
  if (h <= 0) return "";
  r = Math.min(r, w / 2, h);
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}
function barH(x, y, w, h, r = 4) {
  if (w <= 0) return "";
  r = Math.min(r, h / 2, w);
  return `M${x},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h - r}Q${x + w},${y + h} ${x + w - r},${y + h}H${x}Z`;
}
function mixHex(a, b, t) {
  const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const A = p(a), B = p(b);
  return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, "0")).join("");
}
function lum(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

// tooltip payload: {t: title, c: color, rows: [[k, v]], hint}
const tipAttr = (o) => `data-tip="${esc(JSON.stringify(o))}"`;
const fAttr = (key, val) => `data-fk="${esc(key)}" data-fv="${esc(val)}" tabindex="0" role="button"`;
const isSel = (key, val) => state.filters[key] === val;
const dimCls = (key) => (state.filters[key] ? " dim" : "");

/* ---------------- hash <-> filters ---------------- */
function readHash() {
  const out = {};
  const p = new URLSearchParams(location.hash.slice(1));
  for (const k of Object.keys(FILTER_COL)) if (p.get(k)) out[k] = p.get(k);
  return out;
}
function writeHash() {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(state.filters)) if (v) p.set(k, v);
  history.replaceState(null, "", p.toString() ? "#" + p.toString() : location.pathname);
}

/* ---------------- tooltip ---------------- */
const tip = $("#tooltip");
function showTip(el, ev) {
  let o;
  try { o = JSON.parse(el.getAttribute("data-tip")); } catch { return; }
  tip.innerHTML =
    `<div class="tt-title"><i style="background:${o.c || C.red}"></i>${esc(o.t)}</div>` +
    (o.rows || []).map(([k, v]) => `<div class="tt-row"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("") +
    (el.hasAttribute("data-fk") ? `<div class="tt-hint">${isSel(el.dataset.fk, el.dataset.fv) ? "Click to clear filter" : "Click to filter the page"}</div>` : "");
  tip.classList.add("on");
  moveTip(ev);
}
function moveTip(ev) {
  const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
  let x = ev.clientX + pad, y = ev.clientY + pad;
  if (x + w > innerWidth - 8) x = ev.clientX - w - pad;
  if (y + h > innerHeight - 8) y = ev.clientY - h - pad;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
document.addEventListener("pointerover", (e) => {
  const el = e.target.closest("[data-tip]");
  if (el) showTip(el, e);
});
document.addEventListener("pointermove", (e) => { if (tip.classList.contains("on")) moveTip(e); });
document.addEventListener("pointerout", (e) => {
  const el = e.target.closest("[data-tip]");
  if (el && !el.contains(e.relatedTarget)) tip.classList.remove("on");
});
document.addEventListener("focusin", (e) => {
  const el = e.target.closest("[data-tip]");
  if (el) { const r = el.getBoundingClientRect(); showTip(el, { clientX: r.right, clientY: r.top }); }
});
document.addEventListener("focusout", () => tip.classList.remove("on"));

/* ---------------- cross-filter clicks ---------------- */
function toggleFilter(key, val) {
  if (state.filters[key] === val) delete state.filters[key];
  else state.filters[key] = val;
  tip.classList.remove("on");
  syncControls();
  load();
}
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-fk]");
  if (!el) return;
  if (el.dataset.fk2) { // heatmap cell sets two filters at once
    const same = state.filters[el.dataset.fk] === el.dataset.fv && state.filters[el.dataset.fk2] === el.dataset.fv2;
    if (same) { delete state.filters[el.dataset.fk]; delete state.filters[el.dataset.fk2]; }
    else { state.filters[el.dataset.fk] = el.dataset.fv; state.filters[el.dataset.fk2] = el.dataset.fv2; }
    tip.classList.remove("on"); syncControls(); load(); return;
  }
  toggleFilter(el.dataset.fk, el.dataset.fv);
});
document.addEventListener("keydown", (e) => {
  if ((e.key === "Enter" || e.key === " ") && e.target.matches("[data-fk]")) { e.preventDefault(); e.target.click(); }
});

/* ---------------- toast ---------------- */
let toastT;
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("on");
  clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("on"), 3200);
}

/* ---------------- count-up ---------------- */
function countUp(el, to, fmt, dur = 900) {
  if (to == null) { el.textContent = "—"; el._v = null; return; }
  const from = el._v ?? 0; el._v = to;
  if (!state.animate || matchMedia("(prefers-reduced-motion: reduce)").matches) { el.textContent = fmt(to); return; }
  const t0 = performance.now();
  const step = (t) => {
    const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
    el.textContent = fmt(from + (to - from) * e);
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/* ================= CHART RENDERERS ================= */
// Each returns HTML for the card body. w = available width in px.

// 1 · Columns (counts)
function columns(rows, { w, h = 250, label, value, fmt, tipRows, fkey, fval, color = C.red, xLabel = (s) => s }) {
  if (!rows.length) return emptyMsg();
  const m = { t: 22, r: 8, b: 44, l: 44 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const max = Math.max(...rows.map(value)) || 1;
  const ticks = niceTicks(0, max, 4);
  const y = scale(0, ticks[ticks.length - 1], ih, 0);
  const band = iw / rows.length, bw = Math.min(56, band * 0.62);
  const sel = fkey && state.filters[fkey];
  let s = `<svg width="${w}" height="${h}" class="${sel ? "dim" : ""}"><g transform="translate(${m.l},${m.t})">`;
  for (const t of ticks) s += `<line class="grid-line" x1="0" x2="${iw}" y1="${y(t)}" y2="${y(t)}"/><text class="tick" x="-8" y="${y(t) + 4}" text-anchor="end"><tspan class="tick">${fmtCompactIntl(t)}</tspan></text>`;
  rows.forEach((r, i) => {
    const v = value(r), x = i * band + (band - bw) / 2, yy = y(v), hh = ih - yy;
    const fv = fval ? fval(r) : null, selected = sel && fv === sel;
    const tipo = { t: label(r), c: color, rows: tipRows(r) };
    s += `<g class="mark${fkey ? " click" : ""}${selected ? " sel" : ""}" ${tipAttr(tipo)} ${fkey ? fAttr(fkey, fv) : ""}>`;
    s += `<rect class="hit" x="${i * band}" y="0" width="${band}" height="${ih}"/>`;
    s += `<path class="grow-y" style="--i:${i}" d="${barV(x, yy, bw, hh)}" fill="${color}"/>`;
    s += `<text class="lbl fade" style="--i:${i}" x="${x + bw / 2}" y="${yy - 7}" text-anchor="middle">${fmt(v)}</text>`;
    s += `</g>`;
    s += `<text class="cat" x="${x + bw / 2}" y="${ih + 18}" text-anchor="middle">${esc(shortLabel(xLabel(label(r)), Math.max(6, Math.floor(band / 6.6))))}</text>`;
  });
  s += `<line class="base-line" x1="0" x2="${iw}" y1="${ih}" y2="${ih}"/></g></svg>`;
  return s;
}

// 2 · Ranked horizontal bars
function hbars(rows, { w, label, value, fmt, max, tipRows, fkey, fval, color = C.red, extra, ref, refLabel, labelW = 150 }) {
  if (!rows.length) return emptyMsg();
  const rowH = 30, gap = 0, m = { t: ref != null ? 18 : 4, r: extra ? 96 : 50, b: 4, l: labelW };
  const iw = Math.max(60, w - m.l - m.r), h = m.t + rows.length * (rowH + gap) + m.b;
  const mx = max ?? Math.max(...rows.map(value));
  const x = scale(0, mx, 0, iw);
  const sel = fkey && state.filters[fkey];
  let s = `<svg width="${w}" height="${h}" class="${sel ? "dim" : ""}"><g transform="translate(${m.l},${m.t})">`;
  if (ref != null) {
    s += `<line class="ref-line" x1="${x(ref)}" x2="${x(ref)}" y1="-6" y2="${rows.length * rowH}"/>`;
    s += `<text class="ref-label" x="${x(ref)}" y="-8" text-anchor="middle">${esc(refLabel)}</text>`;
  }
  rows.forEach((r, i) => {
    const v = value(r), yy = i * rowH, bh = 14, by = yy + (rowH - bh) / 2;
    const fv = fval ? fval(r) : null, selected = sel && fv === sel;
    s += `<g class="mark${fkey ? " click" : ""}${selected ? " sel" : ""}" ${tipAttr({ t: label(r), c: color, rows: tipRows(r) })} ${fkey ? fAttr(fkey, fv) : ""}>`;
    s += `<rect class="hit" x="${-m.l}" y="${yy}" width="${w}" height="${rowH}"/>`;
    s += `<text class="cat" x="-10" y="${yy + rowH / 2 + 4}" text-anchor="end">${esc(shortLabel(label(r), Math.floor(labelW / 7)))}</text>`;
    s += `<path class="grow-x" style="--i:${i}" d="${barH(0, by, x(v), bh)}" fill="${color}"/>`;
    s += `<text class="lbl fade" style="--i:${i}" x="${x(v) + 8}" y="${yy + rowH / 2 + 4}">${fmt(v)}</text>`;
    if (extra) s += `<text class="lbl muted fade" style="--i:${i}" x="${iw + m.r - 4}" y="${yy + rowH / 2 + 4}" text-anchor="end">${esc(extra(r))}</text>`;
    s += `</g>`;
  });
  s += `<line class="base-line" x1="0" x2="0" y1="0" y2="${rows.length * rowH}"/></g></svg>`;
  return s;
}

// 3 · Line(s) over ordered categories
function lines(series, cats, { w, h = 250, fmt, tipRows, catLabel = (c) => c, endLabels = true }) {
  const all = series.flatMap((s) => s.points.map((p) => p.v)).filter((v) => v != null);
  if (!all.length) return emptyMsg();
  const m = { t: 20, r: series.length > 1 ? 44 : 24, b: 44, l: 40 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  let lo = Math.min(...all), hi = Math.max(...all);
  const pad = Math.max(0.08, (hi - lo) * 0.15);
  const ticks = niceTicks(lo - pad, hi + pad, 4);
  const y = scale(ticks[0], ticks[ticks.length - 1], ih, 0);
  const x = (i) => (cats.length === 1 ? iw / 2 : (i / (cats.length - 1)) * iw);
  let s = `<svg width="${w}" height="${h}"><g transform="translate(${m.l},${m.t})">`;
  for (const t of ticks) s += `<line class="grid-line" x1="0" x2="${iw}" y1="${y(t)}" y2="${y(t)}"/><text class="tick" x="-8" y="${y(t) + 4}" text-anchor="end">${t.toFixed(1)}</text>`;
  cats.forEach((c, i) => {
    s += `<text class="cat" x="${x(i)}" y="${ih + 18}" text-anchor="middle">${esc(shortLabel(catLabel(c), Math.max(6, Math.floor(iw / cats.length / 6.4))))}</text>`;
  });
  series.forEach((ser, si) => {
    const pts = ser.points.map((p, i) => (p.v == null ? null : [x(i), y(p.v), p])).filter(Boolean);
    if (pts.length > 1) {
      const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join("");
      s += `<path class="draw" pathLength="1" d="${d}" fill="none" stroke="${ser.color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" style="animation-delay:${si * 0.15 + 0.1}s"/>`;
    }
    pts.forEach(([px, py, p], i) => {
      s += `<g class="mark" ${tipAttr({ t: `${catLabel(cats[p.i])}${ser.name ? " · " + ser.name : ""}`, c: ser.color, rows: tipRows(p.row, ser) })}>`;
      s += `<circle class="hit" cx="${px}" cy="${py}" r="14"/>`;
      s += `<circle class="pop" style="--i:${i + si * 2}" cx="${px}" cy="${py}" r="5" fill="${ser.color}" stroke="#fff" stroke-width="2"/>`;
      s += `</g>`;
    });
    // multi-series: label line ends only when they sit far enough apart (else legend + tooltip carry it)
    const lastYs = series.map((o) => { const q = o.points.filter((p) => p.v != null); return q.length ? y(q[q.length - 1].v) : null; });
    const crowded = series.length > 1 && lastYs.some((v, j) => j !== si && v != null && lastYs[si] != null && Math.abs(v - lastYs[si]) < 16);
    if (endLabels && pts.length && !crowded) {
      const first = pts[0], last = pts[pts.length - 1];
      const off = series.length > 1 ? (si === 0 ? 16 : -10) : -12;
      if (series.length === 1) s += `<text class="lbl fade" style="--i:2" x="${first[0]}" y="${first[1] + off}" text-anchor="start">${fmt(first[2].v)}</text>`;
      s += `<text class="lbl fade" style="--i:4" x="${last[0] + (series.length > 1 ? 10 : 0)}" y="${last[1] + (series.length > 1 ? 4 : off)}" text-anchor="${series.length > 1 ? "start" : "end"}">${fmt(last[2].v)}</text>`;
    }
  });
  s += `</g></svg>`;
  return s;
}

// 4 · 100% stacked horizontal bars
function stacked(rows, { w, label, parts, tipRows, fkey, fval, labelW = 150 }) {
  if (!rows.length) return emptyMsg();
  const rowH = 38, m = { t: 2, r: 8, b: 2, l: labelW };
  const iw = w - m.l - m.r, h = m.t + rows.length * rowH + m.b;
  const sel = fkey && state.filters[fkey];
  let s = `<svg width="${w}" height="${h}" class="${sel ? "dim" : ""}"><g transform="translate(${m.l},${m.t})">`;
  rows.forEach((r, i) => {
    const yy = i * rowH, bh = 24, by = yy + (rowH - bh) / 2;
    const fv = fval(r), selected = sel && fv === sel;
    s += `<g class="mark click${selected ? " sel" : ""}" ${tipAttr({ t: label(r), rows: tipRows(r) })} ${fAttr(fkey, fv)}>`;
    s += `<rect class="hit" x="${-m.l}" y="${yy}" width="${w}" height="${rowH}"/>`;
    s += `<text class="cat" x="-10" y="${yy + rowH / 2 + 4}" text-anchor="end">${esc(shortLabel(label(r), Math.floor(labelW / 7)))}</text>`;
    let x0 = 0;
    parts.forEach((p, pi) => {
      const v = p.value(r) ?? 0, ww = Math.max(0, v * iw - (pi < parts.length - 1 ? 2 : 0));
      const isFirst = pi === 0, isLast = pi === parts.length - 1, rr = 5;
      // rounded outer ends only
      let d;
      if (ww <= 0) d = "";
      else if (isFirst && isLast) d = `M${x0 + rr},${by}H${x0 + ww - rr}Q${x0 + ww},${by} ${x0 + ww},${by + rr}V${by + bh - rr}Q${x0 + ww},${by + bh} ${x0 + ww - rr},${by + bh}H${x0 + rr}Q${x0},${by + bh} ${x0},${by + bh - rr}V${by + rr}Q${x0},${by} ${x0 + rr},${by}Z`;
      else if (isFirst) d = `M${x0 + ww},${by}V${by + bh}H${x0 + rr}Q${x0},${by + bh} ${x0},${by + bh - rr}V${by + rr}Q${x0},${by} ${x0 + rr},${by}Z`;
      else if (isLast) d = barH(x0, by, ww, bh, rr);
      else d = `M${x0},${by}h${ww}v${bh}h${-ww}Z`;
      s += `<path class="grow-x" style="--i:${i}" d="${d}" fill="${p.color}"/>`;
      const txt = fmtPct(v, 0);
      if (ww > txt.length * 7.5 + 14) s += `<text class="lbl fade inside" style="--i:${i};fill:${lum(p.color) > 0.35 ? C.ink : "#fff"}" x="${x0 + 8}" y="${by + bh / 2 + 4}">${txt}</text>`;
      x0 += ww + 2;
    });
    s += `</g>`;
  });
  s += `</g></svg>`;
  return s;
}

// 5 · Bubble scatter (locations)
function scatter(rows, { w, h = 360, ref }) {
  if (!rows.length) return emptyMsg();
  const m = { t: 28, r: 18, b: 46, l: 46 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const xs = rows.map((r) => r.cost), ys = rows.map((r) => r.avg), ns = rows.map((r) => r.n);
  const xt = niceTicks(Math.min(...xs) * 0.9, Math.max(...xs) * 1.05, 5);
  const yt = niceTicks(Math.min(...ys) - 0.05, Math.max(...ys) + 0.05, 4);
  const x = scale(xt[0], xt[xt.length - 1], 0, iw), y = scale(yt[0], yt[yt.length - 1], ih, 0);
  const nMax = Math.max(...ns);
  const rad = (n) => 5 + Math.sqrt(n / nMax) * 22;
  const sel = state.filters.location;
  const labelSet = new Set([...rows].sort((a, b) => b.n - a.n).slice(0, 4).map((r) => r.location)
    .concat([...rows].sort((a, b) => b.avg - a.avg).slice(0, 2).map((r) => r.location)));
  if (sel) labelSet.add(sel);
  let s = `<svg width="${w}" height="${h}" class="${sel ? "dim" : ""}"><g transform="translate(${m.l},${m.t})">`;
  for (const t of yt) s += `<line class="grid-line" x1="0" x2="${iw}" y1="${y(t)}" y2="${y(t)}"/><text class="tick" x="-8" y="${y(t) + 4}" text-anchor="end">${t.toFixed(1)}</text>`;
  for (const t of xt) s += `<text class="tick" x="${x(t)}" y="${ih + 18}" text-anchor="middle">₹${fmtCompactIntl(t)}</text>`;
  s += `<text class="tick" x="${iw}" y="${ih + 38}" text-anchor="end">Average cost for two →</text>`;
  s += `<text class="tick" x="0" y="-4" text-anchor="start" style="font-weight:600">↑ Avg rating</text>`;
  if (ref) {
    s += `<line class="ref-line" x1="0" x2="${iw}" y1="${y(ref.avg)}" y2="${y(ref.avg)}"/><text class="ref-label" x="${iw - 4}" y="${y(ref.avg) - 6}" text-anchor="end">avg ${fmtRate(ref.avg)}</text>`;
  }
  [...rows].sort((a, b) => b.n - a.n).forEach((r, i) => {
    const cx = x(r.cost), cy = y(r.avg), rr = rad(r.n), selected = sel === r.location;
    s += `<g class="mark click${selected ? " sel" : ""}" ${tipAttr({ t: r.location, rows: [["Avg rating", fmtRate(r.avg)], ["Avg cost for two", fmtRs(r.cost)], ["Restaurants", fmtInt(r.n)]] })} ${fAttr("location", r.location)}>`;
    s += `<circle class="pop" style="--i:${i * 0.4}" cx="${cx}" cy="${cy}" r="${rr}" fill="${selected ? C.red700 : C.red}" fill-opacity="${selected ? 0.95 : 0.62}" stroke="#fff" stroke-width="2"/>`;
    s += `</g>`;
  });
  // label selectively, skipping any label whose box would collide with one already placed
  const placed = [];
  [...rows].filter((r) => labelSet.has(r.location))
    .sort((a, b) => (b.location === sel) - (a.location === sel) || b.n - a.n)
    .forEach((r, i) => {
      const txt = shortLabel(r.location, 22), tw = txt.length * 6.6 + 4;
      const cx = x(r.cost), cy = y(r.avg), rr = rad(r.n);
      for (const right of [cx < iw - 140, !(cx < iw - 140)]) {
        const lx = right ? cx + rr + 6 : cx - rr - 6 - tw;
        const box = { x0: lx, x1: lx + tw, y0: cy - 9, y1: cy + 7 };
        if (box.x0 < 0 || box.x1 > iw) continue;
        if (placed.some((b) => !(box.x1 < b.x0 || box.x0 > b.x1 || box.y1 < b.y0 || box.y0 > b.y1))) continue;
        placed.push(box);
        s += `<text class="lbl fade" style="--i:${8 + i}" x="${lx}" y="${cy + 4}">${esc(txt)}</text>`;
        break;
      }
    });
  s += `<line class="base-line" x1="0" x2="${iw}" y1="${ih}" y2="${ih}"/></g></svg>`;
  return s;
}

function emptyMsg(msg = "No restaurants match these filters") {
  return `<div class="empty">${esc(msg)}</div>`;
}

/* ================= CHART DEFINITIONS ================= */
const byAvg = (rows) => [...rows].sort((a, b) => (b.avg ?? 0) - (a.avg ?? 0));
const ratingCats = (rows) => rows.map((r) => r.Rating_Bracket);
const CHARTS = {
  rating_dist: {
    n: 1, title: "How ratings are distributed",
    sub: (d) => {
      const r = d.rating_dist; if (!r.length) return "";
      const top = r.reduce((a, b) => (b.n > a.n ? b : a));
      return `Most restaurants sit in <strong>${esc(top.Rating_Bracket)}</strong>. <strong>${fmtPct(d.kpis.top_rated_share)}</strong> are rated 4.0 or higher.`;
    },
    render: (d, w) => columns(d.rating_dist, {
      w, h: 270, label: (r) => r.Rating_Bracket, value: (r) => r.n, fmt: fmtCompactIntl,
      tipRows: (r) => [["Restaurants", fmtInt(r.n)], ["Avg rating", fmtRate(r.avg)]],
      fkey: "rating", fval: (r) => r.Rating_Bracket,
    }),
    table: (d) => [["Rating bracket", "Restaurants", "Avg rating"], d.rating_dist.map((r) => [r.Rating_Bracket, fmtInt(r.n), fmtRate(r.avg)])],
  },

  service: {
    n: 2, title: "Booking × online ordering",
    sub: (d) => d.kpis.booking_lift == null ? "Average rating for each combination" :
      `Table booking adds <strong>${fmtSigned(d.kpis.booking_lift)}</strong> rating points`,
    render: (d) => {
      const rows = d.service; if (!rows.length) return emptyMsg();
      const get = (b, o) => rows.find((r) => r.book_table === b && r.online_order === o);
      const vals = rows.map((r) => r.avg);
      const lo = Math.min(...vals), hi = Math.max(...vals);
      const sb = state.filters.booking, so = state.filters.online;
      let s = `<div class="heat${sb || so ? " dim" : ""}"><div></div><div class="hh">Online · Yes</div><div class="hh">Online · No</div>`;
      let i = 0;
      for (const b of ["Yes", "No"]) {
        s += `<div class="rh">Table<br>booking · ${b}</div>`;
        for (const o of ["Yes", "No"]) {
          const r = get(b, o);
          if (!r) { s += `<div class="cell" style="--i:${i++};background:${C.line};cursor:default"><span class="v" style="color:${C.muted}">—</span><span class="n" style="color:${C.muted}">none</span></div>`; continue; }
          const t = hi > lo ? (r.avg - lo) / (hi - lo) : 1;
          const bg = mixHex("#FBD3D7", C.red800, 0.15 + t * 0.85);
          const fg = lum(bg) > 0.35 ? C.ink : "#fff";
          const selected = (!sb || sb === b) && (!so || so === o) && (sb || so);
          s += `<div class="cell${selected ? " sel" : ""}" style="--i:${i++};background:${bg};color:${fg}" ${tipAttr({ t: `Booking ${b} · Online ${o}`, c: bg, rows: [["Avg rating", fmtRate(r.avg)], ["Restaurants", fmtInt(r.n)]] })} data-fk="booking" data-fv="${b}" data-fk2="online" data-fv2="${o}" tabindex="0" role="button">`;
          s += `<span class="v">${fmtRate(r.avg)}</span><span class="n">${fmtInt(r.n)} restaurants</span></div>`;
        }
      }
      return s + `</div><div class="hint">Darker = higher average rating · click a cell to filter</div>`;
    },
    table: (d) => [["Table booking", "Online ordering", "Restaurants", "Avg rating"], d.service.map((r) => [r.book_table, r.online_order, fmtInt(r.n), fmtRate(r.avg)])],
  },

  votes: {
    n: 3, title: "More votes, higher rating",
    sub: (d) => {
      const r = d.votes; if (r.length < 2) return "Average rating by vote count";
      return `Rating climbs from <strong>${fmtRate(r[0].avg)}</strong> to <strong>${fmtRate(r[r.length - 1].avg)}</strong> as engagement grows`;
    },
    render: (d, w) => lines([{ name: "", color: C.red, points: d.votes.map((r, i) => ({ v: r.avg, row: r, i })) }],
      d.votes.map((r) => r.Vote_Bracket), {
        w, fmt: fmtRate, catLabel: (c) => stripParen(c),
        tipRows: (r) => [["Avg rating", fmtRate(r.avg)], ["Restaurants", fmtInt(r.n)]],
      }),
    table: (d) => [["Votes", "Restaurants", "Avg rating"], d.votes.map((r) => [r.Vote_Bracket, fmtInt(r.n), fmtRate(r.avg)])],
  },

  cost_online: {
    n: 4, title: "Price × online ordering",
    sub: () => "Average rating at each price tier, with and without online ordering",
    legend: [["Online ordering · Yes", ONLINE.Yes], ["Online ordering · No", ONLINE.No]],
    render: (d, w) => {
      const cats = [...new Map(d.cost_online.map((r) => [r.Cost_Bracket_Sort, r.Cost_Bracket])).entries()].sort((a, b) => a[0] - b[0]).map((e) => e[1]);
      const ser = ["Yes", "No"].map((o) => ({
        name: "Online " + o, color: ONLINE[o],
        points: cats.map((c, i) => { const r = d.cost_online.find((x) => x.Cost_Bracket === c && x.online_order === o); return { v: r ? r.avg : null, row: r, i }; }),
      })).filter((s) => s.points.some((p) => p.v != null));
      return lines(ser, cats, {
        w, fmt: fmtRate, catLabel: (c) => c.split(" (")[0],
        tipRows: (r) => [["Avg rating", fmtRate(r.avg)], ["Restaurants", fmtInt(r.n)]],
      });
    },
    table: (d) => [["Price tier", "Online ordering", "Restaurants", "Avg rating"], d.cost_online.map((r) => [r.Cost_Bracket, r.online_order, fmtInt(r.n), fmtRate(r.avg)])],
  },

  cost: {
    n: 5, title: "Restaurants by price tier",
    sub: (d) => {
      const r = d.cost; if (!r.length) return "";
      const top = r.reduce((a, b) => (b.n > a.n ? b : a));
      return `<strong>${esc(top.Cost_Bracket.split(" (")[0])}</strong> is the biggest tier · avg cost ${fmtRs(d.kpis.avg_cost)}`;
    },
    render: (d, w) => columns(d.cost, {
      w, label: (r) => r.Cost_Bracket, value: (r) => r.n, fmt: fmtCompactIntl, xLabel: (s) => s.split(" (")[0],
      tipRows: (r) => [["Restaurants", fmtInt(r.n)], ["Avg rating", fmtRate(r.avg)], ["Rated ≥ 4.0", fmtPct(r.top_share)]],
      fkey: "cost", fval: (r) => r.Cost_Bracket,
    }),
    table: (d) => [["Price tier", "Restaurants", "Avg rating", "Rated ≥ 4.0"], d.cost.map((r) => [r.Cost_Bracket, fmtInt(r.n), fmtRate(r.avg), fmtPct(r.top_share)])],
  },

  top_share: {
    n: 6, title: "Share rated 4.0+ by price tier",
    sub: (d) => {
      const r = d.cost; if (r.length < 2) return "";
      return `From <strong>${fmtPct(r[0].top_share, 0)}</strong> in ${esc(r[0].Cost_Bracket.split(" (")[0])} to <strong>${fmtPct(r[r.length - 1].top_share, 0)}</strong> in ${esc(r[r.length - 1].Cost_Bracket.split(" (")[0])}`;
    },
    legend: [["Rated 4.0+", C.red700], ["Below 4.0", C.red200]],
    render: (d, w) => stacked(d.cost, {
      w, label: (r) => r.Cost_Bracket, labelW: Math.min(190, w * 0.36),
      parts: [{ value: (r) => r.top_share, color: C.red700 }, { value: (r) => 1 - r.top_share, color: C.red200 }],
      tipRows: (r) => [["Rated 4.0+", fmtPct(r.top_share)], ["Below 4.0", fmtPct(1 - r.top_share)], ["Restaurants", fmtInt(r.n)]],
      fkey: "cost", fval: (r) => r.Cost_Bracket,
    }),
    table: (d) => [["Price tier", "Rated 4.0+", "Below 4.0"], d.cost.map((r) => [r.Cost_Bracket, fmtPct(r.top_share), fmtPct(1 - r.top_share)])],
  },

  format_rings: {
    n: 7, title: "Format mix",
    sub: () => "Share of restaurants by dining format (top 10)",
    render: (d) => {
      const rows = [...d.formats].sort((a, b) => b.n - a.n);
      if (!rows.length) return emptyMsg();
      const total = d.kpis.restaurants || rows.reduce((a, r) => a + r.n, 0);
      const sel = state.filters.format;
      return `<div class="rings${sel ? " dim" : ""}">` + rows.map((r, i) => {
        const share = r.n / total, selected = sel === r.primary_rest_type;
        return `<div class="ring mark${selected ? " sel" : ""}" ${tipAttr({ t: r.primary_rest_type, rows: [["Share", fmtPct(share)], ["Restaurants", fmtInt(r.n)], ["Avg rating", fmtRate(r.avg)]] })} ${fAttr("format", r.primary_rest_type)}>
          <svg viewBox="0 0 84 84"><circle cx="42" cy="42" r="34" fill="none" stroke="${C.red100}" stroke-width="8"/>
          <circle class="sweep" style="--i:${i}" cx="42" cy="42" r="34" fill="none" stroke="${C.red}" stroke-width="8" stroke-linecap="round" pathLength="100" stroke-dasharray="${Math.max(0.5, share * 100)} 100" transform="rotate(-90 42 42)"/>
          <text class="rv" x="42" y="47" text-anchor="middle">${fmtPct(share, share < 0.1 ? 1 : 0)}</text></svg>
          <div class="rl">${esc(r.primary_rest_type)}</div><div class="rs">${fmtInt(r.n)}</div></div>`;
      }).join("") + `</div>`;
    },
    table: (d) => [["Format", "Restaurants", "Share"], [...d.formats].sort((a, b) => b.n - a.n).map((r) => [r.primary_rest_type, fmtInt(r.n), fmtPct(r.n / (d.kpis.restaurants || 1))])],
  },

  formats: {
    n: 8, title: "Rating by dining format",
    sub: (d) => {
      const r = byAvg(d.formats); if (r.length < 2) return "Top 10 formats by number of restaurants";
      return `<strong>${esc(r[0].primary_rest_type)}</strong> lead at ${fmtRate(r[0].avg)}; <strong>${esc(r[r.length - 1].primary_rest_type)}</strong> trail at ${fmtRate(r[r.length - 1].avg)}`;
    },
    render: (d, w) => hbars(byAvg(d.formats), {
      w, label: (r) => r.primary_rest_type, value: (r) => r.avg, fmt: fmtRate, max: 5,
      ref: d.kpis.avg_rating, refLabel: `avg ${fmtRate(d.kpis.avg_rating)}`, labelW: Math.min(140, w * 0.3),
      tipRows: (r) => [["Avg rating", fmtRate(r.avg)], ["Restaurants", fmtInt(r.n)], ["Rated ≥ 4.0", fmtPct(r.top_share)], ["Avg cost", fmtRs(r.cost)]],
      fkey: "format", fval: (r) => r.primary_rest_type,
    }),
    table: (d) => [["Format", "Avg rating", "Restaurants", "Rated ≥ 4.0", "Avg cost"], byAvg(d.formats).map((r) => [r.primary_rest_type, fmtRate(r.avg), fmtInt(r.n), fmtPct(r.top_share), fmtRs(r.cost)])],
  },

  cuisines: {
    n: 9, title: "Top cuisines",
    sub: (d) => d.cuisines.length ? `<strong>${esc(d.cuisines[0].primary_cuisine)}</strong> is the most common primary cuisine` : "",
    render: (d, w) => hbars(d.cuisines, {
      w, label: (r) => r.primary_cuisine, value: (r) => r.n, fmt: fmtInt, labelW: Math.min(130, w * 0.28),
      extra: (r) => `★ ${fmtRate(r.avg)}`,
      tipRows: (r) => [["Restaurants", fmtInt(r.n)], ["Avg rating", fmtRate(r.avg)]],
      fkey: "cuisine", fval: (r) => r.primary_cuisine,
    }),
    table: (d) => [["Cuisine", "Restaurants", "Avg rating"], d.cuisines.map((r) => [r.primary_cuisine, fmtInt(r.n), fmtRate(r.avg)])],
  },

  locations: {
    n: 10, title: "Top 15 neighbourhoods",
    sub: (d) => {
      const r = byAvg(d.locations); if (r.length < 2) return "Busiest neighbourhoods, ranked by average rating";
      return `Busiest 15 areas ranked by rating · <strong>${esc(r[0].location)}</strong> leads at ${fmtRate(r[0].avg)}`;
    },
    render: (d, w) => hbars(byAvg(d.locations), {
      w, label: (r) => r.location, value: (r) => r.avg, fmt: fmtRate, max: 5,
      ref: d.kpis.avg_rating, refLabel: `avg ${fmtRate(d.kpis.avg_rating)}`, labelW: Math.min(170, w * 0.3),
      extra: (r) => `${fmtInt(r.n)} outlets`,
      tipRows: (r) => [["Avg rating", fmtRate(r.avg)], ["Restaurants", fmtInt(r.n)], ["Avg cost", fmtRs(r.cost)], ["Avg votes", fmtInt(r.votes)]],
      fkey: "location", fval: (r) => r.location,
    }),
    table: (d) => [["Location", "Avg rating", "Restaurants", "Avg cost", "Avg votes"], byAvg(d.locations).map((r) => [r.location, fmtRate(r.avg), fmtInt(r.n), fmtRs(r.cost), fmtInt(r.votes)])],
  },

  listing: {
    n: 11, title: "Rating by listing type",
    sub: (d) => {
      const r = [...d.listing].sort((a, b) => b.avg - a.avg); if (!r.length) return "";
      return `<strong>${esc(r[0]["listed_in(type)"])}</strong> listings rate highest (${fmtRate(r[0].avg)})`;
    },
    render: (d, w) => columns([...d.listing].sort((a, b) => b.avg - a.avg), {
      w, h: 270, label: (r) => r["listed_in(type)"], value: (r) => r.avg, fmt: fmtRate,
      xLabel: (s) => s.replace("Drinks & nightlife", "Nightlife").replace("Pubs and bars", "Pubs & bars"),
      tipRows: (r) => [["Avg rating", fmtRate(r.avg)], ["Listings", fmtInt(r.n)]],
      fkey: "listing", fval: (r) => r["listed_in(type)"],
    }),
    table: (d) => [["Listing type", "Listings", "Avg rating"], d.listing.map((r) => [r["listed_in(type)"], fmtInt(r.n), fmtRate(r.avg)])],
  },

  scatter: {
    n: 12, title: "Neighbourhood map: price vs rating",
    sub: () => "Top 30 areas · bubble size = number of restaurants · click a bubble to focus on it",
    render: (d, w) => scatter(d.scatter, { w, h: Math.max(320, Math.min(420, w * 0.5)), ref: { avg: d.kpis.avg_rating } }),
    table: (d) => [["Location", "Avg rating", "Avg cost", "Restaurants"], d.scatter.map((r) => [r.location, fmtRate(r.avg), fmtRs(r.cost), fmtInt(r.n)])],
  },

  ml: {
    n: 13, title: "What predicts a rating",
    sub: () => "Random Forest feature importance (Review 1 notebook model)",
    staticData: true,
    render: (_d, w) => hbars(ML, {
      w, label: (r) => r.f, value: (r) => r.v, fmt: (v) => (v * 100).toFixed(1) + "%", labelW: Math.min(150, w * 0.42),
      tipRows: (r) => [["Importance", (r.v * 100).toFixed(2) + "%"], ["Feature", r.k]],
    }) + `<div class="ml-metrics"><div><strong>79.2%</strong><span>R² Random Forest</span></div><div><strong>0.130</strong><span>MAE (rating pts)</span></div><div><strong>37.6%</strong><span>R² linear baseline</span></div></div>`,
    table: () => [["Feature", "Importance"], ML.map((r) => [r.f, (r.v * 100).toFixed(2) + "%"])],
  },

  leaders: {
    n: 14, title: "Most-voted restaurants",
    sub: (d) => d.leaders.length ? `<strong>${esc(d.leaders[0].name)}</strong> tops engagement with ${fmtInt(d.leaders[0].max_votes)} votes` : "",
    render: (d) => {
      const rows = d.leaders; if (!rows.length) return emptyMsg();
      const mx = rows[0].max_votes || 1;
      const star = `<svg viewBox="0 0 24 24"><path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/></svg>`;
      return `<div class="lb-head"><span>#</span><span>Restaurant</span><span>Votes</span><span></span><span>Rating</span></div><div class="lb">` + rows.map((r, i) =>
        `<div class="lb-row" style="--i:${i}" ${tipAttr({ t: r.name, rows: [["Votes", fmtInt(r.max_votes)], ["Avg rating", fmtRate(r.avg)], ["Listings", fmtInt(r.n)], ["Avg cost", fmtRs(r.cost)]] })}>
          <span class="lb-rank">${i + 1}</span>
          <span class="lb-name">${esc(r.name)}<small>${fmtInt(r.n)} listings · ${fmtRs(r.cost)} for two</small></span>
          <span class="lb-bar"><i style="--i:${i};width:${(r.max_votes / mx) * 100}%"></i></span>
          <span class="lb-votes">${fmtCompactIntl(r.max_votes)}</span>
          <span class="lb-rate">${fmtRate(r.avg).slice(0, 3)} ${star}</span>
        </div>`).join("") + `</div>`;
    },
    table: (d) => [["Restaurant", "Votes", "Avg rating", "Listings", "Avg cost"], d.leaders.map((r) => [r.name, fmtInt(r.max_votes), fmtRate(r.avg), fmtInt(r.n), fmtRs(r.cost)])],
  },
};

const ML = [
  { f: "Customer votes", k: "votes", v: 0.6355 },
  { f: "Location", k: "location", v: 0.1101 },
  { f: "Price level", k: "approx_cost", v: 0.0859 },
  { f: "Cuisine", k: "cuisines", v: 0.0769 },
  { f: "Dining format", k: "rest_type", v: 0.0520 },
  { f: "Booking & online", k: "book_table, online_order", v: 0.0396 },
];

/* ================= CARD SHELL ================= */
function daxHighlight(q) {
  return esc(q)
    .replace(/(&quot;.*?&quot;)/g, '<span class="str">$1</span>')
    .replace(/(&#39;zomato_powerbi&#39;)/g, '<span class="tbl">$1</span>')
    .replace(/\b(EVALUATE|SUMMARIZECOLUMNS|TOPN|ORDER BY|DESC|ASC|CALCULATETABLE|CALCULATE|ROW|COUNTROWS|AVERAGE|SUM|MAX|DIVIDE|COALESCE|KEEPFILTERS|TREATAS|DISTINCTCOUNT|VAR|RETURN|IF|ISBLANK|BLANK)\b/g, '<span class="kw">$1</span>');
}

function renderCard(card, animate) {
  const key = card.dataset.chart, def = CHARTS[key], d = state.data;
  if (!def) return;
  const view = state.views[key] || "chart";
  const daxKey = key === "format_rings" ? "formats" : key === "top_share" ? "cost" : key;
  const hasDax = !def.staticData;
  if (!card._shell) {
    card.innerHTML = `<header class="card-head"><div><h2><span class="num">${def.n}</span>${esc(def.title)}</h2><p class="sub" data-sub></p></div>
      <div class="tools" role="group" aria-label="View">
        <button type="button" data-view="chart">Chart</button><button type="button" data-view="table">Table</button>${hasDax ? `<button type="button" data-view="dax">DAX</button>` : ""}
      </div></header>${def.legend ? `<div class="legend">${def.legend.map(([l, c]) => `<span><i style="background:${c}"></i>${esc(l)}</span>`).join("")}</div>` : ""}<div class="card-body"></div>`;
    card._shell = true;
    $$(".tools button", card).forEach((b) => b.addEventListener("click", () => {
      state.views[key] = b.dataset.view; renderCard(card, true);
    }));
  }
  $$(".tools button", card).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.view === view)));
  const body = $(".card-body", card);
  if (!d) { body.innerHTML = `<div class="skeleton"></div>`; return; }
  $("[data-sub]", card).innerHTML = def.sub ? def.sub(d) : "";
  const legend = $(".legend", card); if (legend) legend.style.display = view === "chart" ? "" : "none";
  const w = Math.max(240, body.clientWidth || card.clientWidth - 40);
  body.classList.toggle("no-anim", !animate);
  if (view === "table") {
    const [head, rows] = def.table(d);
    body.innerHTML = `<div class="tview"><table><thead><tr>${head.map((h, i) => `<th class="${i ? "r" : ""}">${esc(h)}</th>`).join("")}</tr></thead><tbody>${
      rows.map((r) => `<tr>${r.map((c, i) => `<td class="${i ? "r" : ""}">${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  } else if (view === "dax") {
    const q = d.dax?.[daxKey] || "";
    body.innerHTML = `<div class="dview"><button class="copy" type="button">Copy</button><pre>${daxHighlight(q)}</pre>
      <div class="src">${d.source === "powerbi" ? `Ran live against Power BI Desktop (localhost:${d.port}). Paste into DAX query view to reproduce.` : "Power BI is closed, so this ran on the CSV snapshot. Open Power BI to run it live."}</div></div>`;
    $(".copy", body).addEventListener("click", (e) => { navigator.clipboard?.writeText(q); e.target.textContent = "Copied"; setTimeout(() => (e.target.textContent = "Copy"), 1400); });
  } else {
    body.innerHTML = def.render(d, w);
  }
}

function renderAll(animate = true) {
  $$("[data-chart]").forEach((c) => renderCard(c, animate));
}

/* ================= KPIs ================= */
const ICONS = {
  store: '<path d="M3 9l1.5-5h15L21 9M3 9h18M3 9v11h18V9M9 20v-6h6v6"/>',
  rupee: '<path d="M6 4h12M6 9h12M6 4c7 0 7 9 0 9l8 7"/>',
  heart: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
  bag: '<path d="M5 8h14l-1 12H6zM9 8V6a3 3 0 0 1 6 0v2"/>',
  cal: '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
  star: '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z"/>',
};
const KPIS = [
  { k: "restaurants", label: "Restaurants", icon: "store", fmt: fmtInt, foot: (d) => `${fmtInt(d.kpis.locations)} areas · ${fmtInt(d.kpis.cuisines)} cuisines` },
  { k: "avg_cost", label: "Avg cost for two", icon: "rupee", fmt: fmtRs, foot: () => "per meal for two" },
  { k: "votes", label: "Total votes", icon: "heart", fmt: fmtCompactIntl, foot: (d) => `${fmtInt(d.kpis.avg_votes)} per restaurant` },
  { k: "online_share", label: "Online ordering", icon: "bag", fmt: (v) => fmtPct(v), meter: true, foot: (d) => d.kpis.online_lift == null ? "" : `${fmtSigned(d.kpis.online_lift)} rating vs offline` },
  { k: "booking_share", label: "Table booking", icon: "cal", fmt: (v) => fmtPct(v), meter: true, foot: (d) => d.kpis.booking_lift == null ? "" : `${fmtSigned(d.kpis.booking_lift)} rating vs no booking` },
  { k: "top_rated_share", label: "Rated 4.0+", icon: "star", fmt: (v) => fmtPct(v), meter: true, foot: () => "of restaurants in view" },
];
function renderKpis() {
  const host = $("#kpis"), d = state.data;
  if (!host.children.length) {
    host.innerHTML = KPIS.map((x, i) => `<div class="kpi" style="--i:${i}"><div class="kpi-label"><svg viewBox="0 0 24 24">${ICONS[x.icon]}</svg>${x.label}</div>
      <div class="kpi-value" data-k="${x.k}">—</div>${x.meter ? `<div class="meter"><i data-m="${x.k}"></i></div>` : ""}<div class="kpi-foot" data-f="${x.k}"></div></div>`).join("");
  }
  if (!d) return;
  for (const x of KPIS) {
    const v = d.kpis[x.k];
    countUp($(`[data-k="${x.k}"]`, host), v, x.fmt);
    if (x.meter) $(`[data-m="${x.k}"]`, host).style.width = v == null ? "0" : (v * 100).toFixed(1) + "%";
    $(`[data-f="${x.k}"]`, host).textContent = x.foot(d);
  }
  countUp($("#hero-rating"), d.kpis.avg_rating, fmtRate);
  $("#hero-lift").textContent = d.kpis.booking_lift == null ? "—" : fmtSigned(d.kpis.booking_lift);
  countUp($("#hero-rows"), d.kpis.restaurants, fmtInt);
}

/* ================= TAKEAWAYS + REPORT ================= */
function renderTakeaways() {
  const d = state.data, host = $("#takeaways");
  if (!d) return;
  const k = d.kpis, votes = d.votes, cost = d.cost, formats = byAvg(d.formats), locs = byAvg(d.locations);
  const items = [
    ["Drive reviews", votes.length > 1 ? `Restaurants with ${esc(stripParen(votes[votes.length - 1].Vote_Bracket))} votes average ${fmtRate(votes[votes.length - 1].avg)} vs ${fmtRate(votes[0].avg)} for ${esc(stripParen(votes[0].Vote_Bracket))}. Votes carry 63.6% of the model's predictive power.` : "Votes carry 63.6% of the model's predictive power."],
    ["Enable reservations", k.booking_lift != null ? `Table booking comes with a ${fmtSigned(k.booking_lift)} rating lift in the current view.` : "Table booking signals full-service dining and higher ratings."],
    ["Avoid price wars", cost.length > 1 ? `${esc(cost[cost.length - 1].Cost_Bracket.split(" (")[0])} averages ${fmtRate(cost[cost.length - 1].avg)} vs ${fmtRate(cost[0].avg)} for ${esc(cost[0].Cost_Bracket.split(" (")[0])}. Price for quality, not volume.` : "Higher price tiers rate higher."],
    ["Lifestyle formats win", formats.length > 1 ? `${esc(formats[0].primary_rest_type)} (${fmtRate(formats[0].avg)}) outperform ${esc(formats[formats.length - 1].primary_rest_type)} (${fmtRate(formats[formats.length - 1].avg)}).` : "Experiential formats outperform quick service."],
    ["Pick quality corridors", locs.length ? `${esc(locs[0].location)} leads the 15 busiest areas at ${fmtRate(locs[0].avg)}; location explains 11% of rating variance.` : "Location explains 11% of rating variance."],
  ];
  host.innerHTML = `<header class="card-head"><div><h2><span class="num">★</span>Strategic takeaways</h2><p class="sub">Finding → action, recomputed for the current filters</p></div></header>
    <ol class="take-list">${items.map(([b, s]) => `<li><div><b>${b}</b><span>${s}</span></div></li>`).join("")}</ol>`;
}

function renderReport() {
  const st = state.status, host = $("#report-card");
  if (!st) return;
  const embed = st.embed_url;
  const key = embed ? "embed:" + embed : "empty:" + st.live;
  if (host._key === key) return;
  host._key = key;
  host.innerHTML = `<header class="card-head"><div><h2><span class="num">PBI</span>Full Power BI report</h2>
    <p class="sub">${embed ? "Embedded from the Power BI Service. Fully interactive." : "The complete report lives in Power BI Desktop. This page is its live summary."}</p></div></header>
    <div class="report-body">${embed ? `<iframe title="Zomato Power BI report" src="${esc(embed)}" allowfullscreen loading="lazy"></iframe>` :
      `<div class="report-empty"><div><h3>${st.live ? "Connected to your open report" : "Open the report to go live"}</h3>
        <p>${st.live ? `This page is querying <code>${esc(st.pbix)}</code> right now. Edit or refresh the model in Power BI Desktop and press <b>Re-sync</b>.` : `Open <code>${esc(st.pbix)}</code> and every chart on this page switches from the CSV snapshot to live DAX against the model.`}</p>
        <button class="btn btn-primary" type="button" data-open-pbi style="flex:none">Open in Power BI Desktop</button></div>
        <div><p style="margin-bottom:8px"><b>Want the full report embedded here?</b></p><ol>
          <li>In Power BI Desktop: <b>Home → Publish</b> → pick a workspace.</li>
          <li>On app.powerbi.com open the report → <b>File → Embed report → Website or portal</b>.</li>
          <li>Paste the link into <code>dashboard/dashboard_config.json</code> → <code>"embed_url"</code>.</li>
          <li>Reload this page. The report appears right here.</li></ol></div></div>`}</div>`;
  $("[data-open-pbi]", host)?.addEventListener("click", openPowerBI);
}

/* ================= STATUS ================= */
function renderStatus() {
  const st = state.status; if (!st) return;
  const pill = $("#conn-pill");
  pill.classList.toggle("live", st.live);
  $("#conn-state").textContent = st.live ? "Live" : "Offline";
  $("#conn-file").textContent = st.pbix;
  $("#conn-engine").textContent = st.live ? `Power BI Desktop · localhost:${st.port}` : "CSV snapshot";
  $("#conn-mode").textContent = st.live ? "DAX via ADOMD.NET" : "pandas (same data)";
  $("#btn-open-label").textContent = st.live ? "Report is open" : "Open in Power BI";
  const reason = $("#conn-reason");
  reason.hidden = st.live || !st.reason; reason.textContent = st.reason || "";
  const host = $("#conn-tables"), sig = JSON.stringify(st.tables);
  if (host._sig !== sig) {
    host._sig = sig;
    host.innerHTML = (st.tables || []).map((t, i) => `<div class="tbl-row" style="--i:${i}"><span class="tsrc">${esc(t.source)}</span><span class="tname">${esc(t.name)}</span><span class="trows">${fmtInt(t.rows)} rows</span></div>`).join("");
  }
  renderReport();
}

async function fetchStatus() {
  try {
    const r = await fetch("/api/status"); const st = await r.json();
    const changed = !state.status || state.status.live !== st.live || state.status.port !== st.port;
    state.status = st; renderStatus();
    return changed;
  } catch { return false; }
}

/* ================= DATA LOAD ================= */
let loadSeq = 0;
async function load({ silent = false } = {}) {
  const seq = ++loadSeq;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(state.filters)) if (v) qs.set(k, v);
  writeHash(); renderChips();
  const prog = $("#progress");
  if (!silent) { prog.className = "progress on"; }
  try {
    const r = await fetch("/api/summary?" + qs.toString());
    const d = await r.json();
    if (seq !== loadSeq) return;
    const json = JSON.stringify(d, (k, v) => (k === "elapsed_ms" ? undefined : v));
    const changed = json !== state.lastJson;
    state.lastJson = json; state.data = d;
    const live = d.source === "powerbi";
    $("#query-meta").classList.toggle("live", live);
    $("#qm-text").textContent = live ? `Live DAX · ${d.elapsed_ms} ms` : `CSV snapshot · ${d.elapsed_ms} ms`;
    $("#conn-sync").textContent = new Date().toLocaleTimeString();
    $("#foot-source").textContent = live ? `Last query: Power BI Desktop (localhost:${d.port})` : "Last query: CSV snapshot (Power BI closed)";
    if (changed || !silent) {
      renderKpis(); renderAll(!silent || changed); renderTakeaways();
    }
  } catch (e) {
    toast("Could not reach the dashboard server");
  } finally {
    if (seq === loadSeq) { prog.className = "progress done"; setTimeout(() => (prog.className = "progress"), 400); }
  }
}

/* ================= FILTER CONTROLS ================= */
function renderChips() {
  const host = $("#chips"), entries = Object.entries(state.filters).filter(([, v]) => v);
  host.hidden = !entries.length;
  host.innerHTML = entries.map(([k, v]) => `<span class="chip"><b>${FILTER_LABEL[k]}</b>${esc(v)}<button type="button" data-rm="${k}" aria-label="Remove ${FILTER_LABEL[k]} filter">×</button></span>`).join("") +
    (entries.length > 1 ? `<button class="chip-clear" type="button" data-clear>Clear all</button>` : "");
}
$("#chips").addEventListener("click", (e) => {
  const rm = e.target.closest("[data-rm]");
  if (rm) { delete state.filters[rm.dataset.rm]; syncControls(); load(); }
  if (e.target.closest("[data-clear]")) { state.filters = {}; syncControls(); load(); }
});

function syncControls() {
  $$("select[data-filter]").forEach((s) => {
    const v = state.filters[s.dataset.filter] || "";
    if (v && ![...s.options].some((o) => o.value === v)) s.add(new Option(v, v));
    s.value = v; s.classList.toggle("active", !!v);
  });
  $$(".seg").forEach((g) => {
    const v = state.filters[g.dataset.filter] || "";
    $$("button", g).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === v)));
  });
}
$$("select[data-filter]").forEach((s) => s.addEventListener("change", () => {
  if (s.value) state.filters[s.dataset.filter] = s.value; else delete state.filters[s.dataset.filter];
  syncControls(); load();
}));
$$(".seg").forEach((g) => g.addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  if (b.dataset.v) state.filters[g.dataset.filter] = b.dataset.v; else delete state.filters[g.dataset.filter];
  syncControls(); load();
}));

async function loadOptions() {
  try {
    const o = await (await fetch("/api/options")).json();
    for (const key of ["location", "format", "cuisine", "listing"]) {
      const s = $(`#f-${key}`), first = s.options[0];
      s.innerHTML = ""; s.add(first);
      (o[key] || []).forEach((v) => s.add(new Option(v, v)));
    }
    syncControls();
  } catch { /* keep defaults */ }
}

/* ================= ACTIONS ================= */
async function openPowerBI() {
  try {
    const r = await (await fetch("/api/open-powerbi", { method: "POST" })).json();
    if (!r.ok) { toast(r.error || "Could not open Power BI"); return; }
    if (r.already_open) { toast("The report is already open in Power BI Desktop"); return; }
    toast("Opening Power BI Desktop… this page goes live automatically");
    let tries = 0;
    const poll = setInterval(async () => {
      tries++;
      const changed = await fetchStatus();
      if (state.status?.live) { clearInterval(poll); toast("Connected to Power BI Desktop · now live"); load(); loadOptions(); }
      else if (tries > 40) clearInterval(poll);
      else if (changed) load();
    }, 3000);
  } catch { toast("Could not reach the dashboard server"); }
}
$("#btn-open").addEventListener("click", openPowerBI);
$("#btn-sync").addEventListener("click", async () => {
  const b = $("#btn-sync"); b.classList.add("spin");
  await fetchStatus(); await load();
  b.classList.remove("spin"); toast(state.data?.source === "powerbi" ? "Re-synced from Power BI" : "Re-synced (snapshot)");
});

/* ================= REVEAL + RESIZE ================= */
const io = new IntersectionObserver((ents) => ents.forEach((e) => {
  if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
}), { threshold: 0.08 });
$$(".card").forEach((c) => io.observe(c));

let rz, lastW = innerWidth;
addEventListener("resize", () => {
  clearTimeout(rz);
  rz = setTimeout(() => { if (Math.abs(innerWidth - lastW) > 20) { lastW = innerWidth; renderAll(false); } }, 160);
});
addEventListener("hashchange", () => { state.filters = readHash(); syncControls(); load(); });

/* ================= BOOT ================= */
(async function boot() {
  renderKpis(); renderAll();
  syncControls();
  await fetchStatus();
  await Promise.all([load(), loadOptions()]);
  // keep in sync with Power BI: status every 8s, silent data refresh every 30s while live
  setInterval(async () => { if (await fetchStatus()) { load(); loadOptions(); } }, 8000);
  setInterval(() => { if (state.status?.live && !document.hidden) load({ silent: true }); }, 30000);
})();
})();
