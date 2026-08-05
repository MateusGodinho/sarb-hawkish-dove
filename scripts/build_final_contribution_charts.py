"""
ETAPA 5 (continuacao) - Gera os graficos 7 e 8 do ciclo atual: indice
combinado por reuniao (atas + discursos), decomposto na contribuicao de
cada tipo de comunicacao (ver build_combined_index.py para a metodologia).
Historico completo + zoom dos ultimos 3 anos.

Rode depois de build_combined_index.py. Saida em reports/.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta

import config

ZOOM_YEARS = 3

TEMPLATE = r"""
<style>
.viz-root {
  color-scheme: light;
  --surface-1:      #eaf2f8;
  --page:           #f9f9f7;
  --text-primary:   #0b0b0b;
  --text-secondary: #52514e;
  --muted:          #6b7580;
  --grid:           #ffffff;
  --baseline:       #0b0b0b;
  --stmt:           #2a78d6;
  --speech:         #eb6834;
  --combined:       #0b0b0b;
  --border:         rgba(11,11,11,0.10);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) .viz-root {
    color-scheme: dark;
    --surface-1:      #1c2732;
    --page:           #0d0d0d;
    --text-primary:   #ffffff;
    --text-secondary: #c3c2b7;
    --muted:          #9aa5af;
    --grid:           #2c3a47;
    --baseline:       #ffffff;
    --stmt:           #3987e5;
    --speech:         #d95926;
    --combined:       #ffffff;
    --border:         rgba(255,255,255,0.10);
  }
}
:root[data-theme="dark"] .viz-root {
  color-scheme: dark;
  --surface-1:      #1c2732;
  --page:           #0d0d0d;
  --text-primary:   #ffffff;
  --text-secondary: #c3c2b7;
  --muted:          #9aa5af;
  --grid:           #2c3a47;
  --baseline:       #ffffff;
  --stmt:           #3987e5;
  --speech:         #d95926;
  --combined:       #ffffff;
  --border:         rgba(255,255,255,0.10);
}

.viz-root { background: var(--page); padding: 24px; box-sizing: border-box; }
.card {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 22px 12px;
  max-width: 1100px;
  margin: 0 auto 14px;
}
.card h1 { font-size: 16px; margin: 0 0 2px; color: var(--text-primary); font-weight: 600; }
.card .sub { font-size: 12.5px; color: var(--text-secondary); margin-bottom: 12px; }
.legend { display:flex; gap:16px; font-size:11.5px; color:var(--text-secondary); margin: 6px 0 2px; flex-wrap: wrap; align-items: center; }
.legend .item { display:flex; align-items:center; gap:6px; }
.legend .swatch { width:11px; height:11px; border-radius:2px; display:inline-block; }
.legend .line { width:16px; height:2px; display:inline-block; background: var(--combined); }
svg { width: 100%; height: auto; overflow: visible; display:block; }
.axis-label { fill: var(--muted); font-size: 10.5px; }
.grid-line { stroke: var(--grid); stroke-width: 1; }
.baseline { stroke: var(--baseline); stroke-width: 1.2; }
.bar-stmt { fill: var(--stmt); cursor: pointer; }
.bar-speech { fill: var(--speech); cursor: pointer; }
.combined-dot { fill: var(--combined); }
#tooltip {
  position: fixed; pointer-events: none;
  background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px;
  padding: 9px 11px; font-size: 12px; color: var(--text-primary);
  box-shadow: 0 4px 16px rgba(0,0,0,0.18); max-width: 300px; display: none; z-index: 10; line-height: 1.5;
}
.note { font-size: 11.5px; color: var(--text-secondary); max-width: 1100px; margin: 8px auto 20px; padding: 0 4px; }
</style>

<div class="viz-root">
  <div class="card">
    <h1>__TITLE__</h1>
    <div class="sub">Henry (2008) index &middot; 1 bar per MPC meeting &middot; speeches between the previous meeting and this one are aggregated and attached to it</div>
    <div class="legend">
      <span class="item"><span class="swatch" style="background:var(--stmt)"></span> contribution from the statement itself</span>
      <span class="item"><span class="swatch" style="background:var(--speech)"></span> contribution from the window's speeches</span>
      <span class="item"><span class="line"></span> combined index</span>
    </div>
    <svg id="chart" viewBox="0 0 1060 360" preserveAspectRatio="xMidYMid meet"></svg>
  </div>
</div>

<div class="note">__NOTE__</div>

<div id="tooltip"></div>

<script>
const DATA = __DATA_JSON__;
const X_MIN = __X_MIN__, X_MAX = __X_MAX__;
const YEAR_STEP = __YEAR_STEP__;

const svg = document.getElementById('chart');
const W = 1060, H = 360;
const M = {top: 14, right: 18, bottom: 32, left: 40};
const plotW = W - M.left - M.right;
const plotH = H - M.top - M.bottom;

const allVals = DATA.flatMap(d => [d.contrib_stmt, d.contrib_speech, d.combined, 0]);
const vMax = Math.max(...allVals, 0.2);
const vMin = Math.min(...allVals, -0.2);
const yMax = Math.ceil(vMax * 5) / 5 + 0.1;
const yMin = Math.floor(vMin * 5) / 5 - 0.1;

const barW = __BARW__;

function y(v) { return M.top + (1 - (v - yMin) / (yMax - yMin)) * plotH; }
function xCenter(i) { return M.left + ((DATA[i].x - X_MIN) / (X_MAX - X_MIN)) * plotW; }

function svgEl(tag, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) el.setAttribute(k, attrs[k]);
  return el;
}

for (let v = Math.ceil(yMin * 5) / 5; v <= yMax; v += 0.2) {
  const gy = y(v);
  const isZero = Math.abs(v) < 1e-9;
  svg.appendChild(svgEl('line', {x1: M.left, x2: W - M.right, y1: gy, y2: gy, class: isZero ? 'baseline' : 'grid-line'}));
  const lbl = svgEl('text', {x: M.left - 8, y: gy + 4, class: 'axis-label', 'text-anchor': 'end'});
  lbl.textContent = v.toFixed(1);
  svg.appendChild(lbl);
}

let lastYear = null;
DATA.forEach((d, i) => {
  const year = d.date.slice(0, 4);
  if (year !== lastYear && (parseInt(year) % YEAR_STEP === 0)) {
    const gx = xCenter(i);
    const lbl = svgEl('text', {x: gx, y: H - M.bottom + 16, class: 'axis-label', 'text-anchor': 'middle'});
    lbl.textContent = year;
    svg.appendChild(lbl);
    lastYear = year;
  } else if (year !== lastYear) {
    lastYear = year;
  }
});

const tooltip = document.getElementById('tooltip');

function addSegment(i, d, value, cls) {
  if (value === 0) return;
  const cx = xCenter(i);
  const x0 = cx - barW / 2;
  const yTop = y(Math.max(value, 0));
  const yBot = y(Math.min(value, 0));
  const h = Math.max(yBot - yTop, 0.5);
  const rect = svgEl('rect', {x: x0, y: yTop, width: barW, height: h, class: cls, rx: 2});
  rect.addEventListener('mouseenter', (ev) => showTooltip(ev, d));
  rect.addEventListener('mousemove', positionTooltip);
  rect.addEventListener('mouseleave', () => tooltip.style.display = 'none');
  svg.appendChild(rect);
}

DATA.forEach((d, i) => {
  if (d.contrib_stmt >= 0 && d.contrib_speech >= 0) {
    addSegment(i, d, d.contrib_stmt, 'bar-stmt');
    const cx = xCenter(i);
    const x0 = cx - barW / 2;
    const yTop = y(d.contrib_stmt + d.contrib_speech);
    const yBot = y(d.contrib_stmt);
    const rect = svgEl('rect', {x: x0, y: yTop, width: barW, height: Math.max(yBot - yTop, 0.5), class: 'bar-speech', rx: 2});
    rect.addEventListener('mouseenter', (ev) => showTooltip(ev, d));
    rect.addEventListener('mousemove', positionTooltip);
    rect.addEventListener('mouseleave', () => tooltip.style.display = 'none');
    svg.appendChild(rect);
  } else if (d.contrib_stmt <= 0 && d.contrib_speech <= 0) {
    addSegment(i, d, d.contrib_stmt, 'bar-stmt');
    const cx = xCenter(i);
    const x0 = cx - barW / 2;
    const yTop = y(d.contrib_stmt);
    const yBot = y(d.contrib_stmt + d.contrib_speech);
    const rect = svgEl('rect', {x: x0, y: yTop, width: barW, height: Math.max(yBot - yTop, 0.5), class: 'bar-speech', rx: 2});
    rect.addEventListener('mouseenter', (ev) => showTooltip(ev, d));
    rect.addEventListener('mousemove', positionTooltip);
    rect.addEventListener('mouseleave', () => tooltip.style.display = 'none');
    svg.appendChild(rect);
  } else {
    addSegment(i, d, d.contrib_stmt, 'bar-stmt');
    addSegment(i, d, d.contrib_speech, 'bar-speech');
  }
  const cx = xCenter(i);
  svg.appendChild(svgEl('circle', {cx: cx, cy: y(d.combined), r: 3, class: 'combined-dot'}));
});

function showTooltip(ev, d) {
  const fmt = (v) => (v === null ? 'n/a' : v.toFixed(3));
  let html = `<div style="font-weight:600">${d.date}</div>`;
  html += `<div style="color:var(--text-secondary); margin-bottom:4px;">${d.title}</div>`;
  html += `<div>Statement: index ${fmt(d.avg_stmt)}, contribution ${d.contrib_stmt.toFixed(3)}</div>`;
  html += `<div>Speeches in window: ${d.n_speech}, average index ${fmt(d.avg_speech)}, contribution ${d.contrib_speech.toFixed(3)}</div>`;
  html += `<div style="margin-top:4px; font-weight:600;">Combined: ${d.combined.toFixed(3)}</div>`;
  tooltip.innerHTML = html;
  tooltip.style.display = 'block';
  positionTooltip(ev);
}
function positionTooltip(ev) {
  const pad = 16;
  let left = ev.clientX + pad;
  let top = ev.clientY + pad;
  if (left + 300 > window.innerWidth) left = ev.clientX - 300 - pad;
  tooltip.style.left = left + 'px';
  tooltip.style.top = top + 'px';
}
</script>
"""


def build(out_name, title, note, rows, year_step, bar_w):
    t0 = datetime.strptime(rows[0]["date"], "%Y-%m-%d")
    for r in rows:
        r["x"] = (datetime.strptime(r["date"], "%Y-%m-%d") - t0).days
    x_min, x_max = 0, rows[-1]["x"]
    data_json = json.dumps(rows, ensure_ascii=False)

    html = (TEMPLATE.replace("__DATA_JSON__", data_json)
            .replace("__X_MIN__", str(x_min))
            .replace("__X_MAX__", str(x_max))
            .replace("__YEAR_STEP__", str(year_step))
            .replace("__BARW__", str(bar_w))
            .replace("__TITLE__", title)
            .replace("__NOTE__", note))

    out_path = config.REPORTS_DIR / f"{out_name}.html"
    out_path.write_text(f"<title>{title}</title>\n" + html, encoding="utf-8")
    print("wrote", out_path, "n:", len(rows))


def main():
    all_rows = []
    with open(config.PROCESSED_DIR / "combined_index_by_meeting.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            all_rows.append({
                "date": r["meeting_date"],
                "title": r["title"],
                "n_speech": int(r["n_speeches_in_window"]),
                "avg_stmt": float(r["statement_index"]),
                "avg_speech": float(r["avg_speech_index"]) if r["avg_speech_index"] else None,
                "contrib_stmt": float(r["contrib_statement"]),
                "contrib_speech": float(r["contrib_speech"]),
                "combined": float(r["combined_index"]),
            })
    all_rows.sort(key=lambda r: r["date"])

    zoom_cutoff = (datetime.strptime(all_rows[-1]["date"], "%Y-%m-%d") - timedelta(days=365 * ZOOM_YEARS)).strftime("%Y-%m-%d")

    build(
        "final_07_contribution_full",
        "SARB — Contribution to the combined index, by meeting (1999–2026)",
        "173 meetings. Blue = contribution from the statement itself; orange = contribution from speeches given since the previous meeting; black dot = combined index (exact sum).",
        [dict(r) for r in all_rows], year_step=2, bar_w=3.2,
    )

    zoom_rows = [dict(r) for r in all_rows if r["date"] >= zoom_cutoff]
    build(
        "final_08_contribution_zoom",
        "SARB — Contribution to the combined index, last 3 years",
        "Last 3 years (same decomposition as the full chart).",
        zoom_rows, year_step=1, bar_w=8,
    )

    print("zoom cutoff:", zoom_cutoff, "zoom rows:", len(zoom_rows))


if __name__ == "__main__":
    main()
