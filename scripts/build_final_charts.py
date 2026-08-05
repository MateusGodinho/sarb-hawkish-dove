"""
ETAPA 5 - Gera os graficos finais deste primeiro ciclo do indicador
hawkish/dove, no formato visual do paper original (pontos + linha
suavizada LOWESS + banda aproximada), mais o grafico de contribuicao
(atas vs discursos). Cada grafico sai em duas versoes: historico completo
e zoom dos ultimos 3 anos -- 8 arquivos HTML standalone em reports/.

Usa o score Henry (2008) (scores_henry.csv / speeches_scores_henry.csv /
combined_index_by_meeting.csv), ja calculados pelas etapas anteriores.

1. statements  - so as atas do MPC
2. speeches    - so os discursos
3. combined    - atas + discursos tratados como 1 corpus so (pooled),
                 igual a abordagem do paper (que junta os tipos de
                 comunicacao antes de suavizar)
4. contribution- indice combinado por reuniao, decomposto na contribuicao
                 de cada tipo (grafico de barras, nao de pontos+LOWESS)

Rode com: python build_final_charts.py
"""

from __future__ import annotations

import csv
import json
from bisect import bisect_right
from datetime import datetime, timedelta

import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess

import config

ZOOM_YEARS = 3


def load_points(path, date_field, score_field="henry_index"):
    pts = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            d = r.get(date_field)
            if not d:
                continue
            pts.append({"date": d, "score": float(r[score_field]), "title": r.get("title", "")})
    pts.sort(key=lambda p: p["date"])
    return pts


def load_rate_regimes() -> list[tuple[str, str | None, float | None]]:
    """
    Le statements_dataset.csv e devolve a lista (data, rate_action_final,
    policy_rate_final) de cada reuniao, ordenada -- usada pra colorir os
    pontos por "movimento de juros vigente" em qualquer um dos 3 corpora
    (statement: a propria reuniao; speech: a reuniao mais recente antes
    dela, ja que um discurso nao tem decisao propria).
    """
    rows = []
    with open(config.DATASET_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            action = r.get("rate_action_final") or None
            rate = r.get("policy_rate_final")
            rate = float(rate) if rate not in (None, "", "None") else None
            rows.append((r["meeting_date"], action, rate))
    rows.sort(key=lambda t: t[0])
    return rows


def attach_regime(points: list[dict], regimes: list[tuple[str, str | None, float | None]]):
    """
    Anexa 'action'/'rate' a cada ponto: a acao/taxa da reuniao mais recente
    NA OU ANTES da data do ponto. Para um statement isso e a decisao da
    propria reuniao; para um speech (que nao tem decisao propria), e o
    ultimo movimento de juros conhecido no momento daquela comunicacao.
    """
    dates = [r[0] for r in regimes]
    for p in points:
        idx = bisect_right(dates, p["date"]) - 1
        if idx < 0:
            p["action"] = None
            p["rate"] = None
        else:
            p["action"] = regimes[idx][1]
            p["rate"] = regimes[idx][2]


PAPER_STYLE = r"""
<style>
.viz-root {
  color-scheme: light;
  --surface-1:      #eaf2f8;
  --page:           #f9f9f7;
  --text-primary:   #0b0b0b;
  --text-secondary: #52514e;
  --muted:          #6b7580;
  --grid:           #ffffff;
  --baseline:       #b9c6d1;
  --raw:            #52514e;
  --smooth:         #e34948;
  --band:           #e34948;
  --event:          #6b7580;
  --hike:           #eb6834;
  --cut:            #1baf7a;
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
    --baseline:       #46586a;
    --raw:            #c3c2b7;
    --smooth:         #e66767;
    --band:           #e66767;
    --event:          #9aa5af;
    --hike:           #d95926;
    --cut:            #199e70;
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
  --baseline:       #46586a;
  --raw:            #c3c2b7;
  --smooth:         #e66767;
  --band:           #e66767;
  --event:          #9aa5af;
  --hike:           #d95926;
  --cut:            #199e70;
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
.legend { display:flex; gap:16px; font-size:11.5px; color:var(--text-secondary); margin: 6px 0 2px; flex-wrap: wrap; }
.legend .item { display:flex; align-items:center; gap:6px; }
.legend .swatch { width:16px; height:2px; display:inline-block; }
.legend .dotswatch { width:6px; height:6px; border-radius:50%; display:inline-block; }
svg { width: 100%; height: auto; overflow: visible; display:block; }
.axis-label { fill: var(--muted); font-size: 10.5px; }
.axis-title { fill: var(--text-secondary); font-size: 11px; }
.grid-line { stroke: var(--grid); stroke-width: 1; }
.baseline { stroke: var(--baseline); stroke-width: 1; stroke-dasharray: 2 2; }
.event-line { stroke: var(--event); stroke-width: 1; stroke-dasharray: 1 3; }
.raw-line { fill:none; stroke: var(--raw); stroke-width: 1; opacity: 0.45; }
.raw-dot { fill: var(--raw); opacity: 0.55; cursor: pointer; }
.raw-dot.hike { fill: var(--hike); opacity: 0.85; }
.raw-dot.cut { fill: var(--cut); opacity: 0.85; }
.smooth-band { fill: var(--band); opacity: 0.14; }
.smooth-line { fill:none; stroke: var(--smooth); stroke-width: 2.5; stroke-linecap: round; }
#tooltip {
  position: fixed; pointer-events: none;
  background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px;
  padding: 9px 11px; font-size: 12px; color: var(--text-primary);
  box-shadow: 0 4px 16px rgba(0,0,0,0.18); max-width: 300px; display: none; z-index: 10; line-height: 1.45;
}
.note { font-size: 11.5px; color: var(--text-secondary); max-width: 1100px; margin: 8px auto 20px; padding: 0 4px; }
</style>
"""


def days_since(date_str, t0):
    return (datetime.strptime(date_str, "%Y-%m-%d") - t0).days


def build_paper_chart(out_name, title, subtitle, points, frac, note, zoom_cutoff=None):
    if zoom_cutoff:
        points = [p for p in points if p["date"] >= zoom_cutoff]

    t0 = datetime.strptime(points[0]["date"], "%Y-%m-%d")
    xs = np.array([days_since(p["date"], t0) for p in points], dtype=float)
    ys = np.array([p["score"] for p in points])

    smoothed = lowess(ys, xs, frac=frac, return_sorted=True)
    sx, sy = smoothed[:, 0], smoothed[:, 1]

    sy_at_x = np.interp(xs, sx, sy)
    resid2 = (ys - sy_at_x) ** 2
    band_smoothed = lowess(resid2, xs, frac=min(frac * 1.5, 0.9), return_sorted=True)
    bx, bvar = band_smoothed[:, 0], np.clip(band_smoothed[:, 1], 0, None)
    bstd = np.sqrt(bvar)
    band_hi = np.interp(sx, bx, bstd)

    for p, xv in zip(points, xs):
        p["x"] = float(xv)

    data_json = json.dumps(points, ensure_ascii=False)
    smooth_json = json.dumps([{"x": float(a), "y": float(b)} for a, b in zip(sx, sy)])
    band_json = json.dumps([{"x": float(a), "y": float(b), "s": float(s)} for a, b, s in zip(sx, sy, band_hi)])

    x_min, x_max = xs.min(), xs.max()

    it_date = "2000-02-01"
    it_x = days_since(it_date, t0) if points[0]["date"] <= it_date <= points[-1]["date"] else None
    year_step = 1 if zoom_cutoff else 2

    script = r"""
<script>
const DATA = __DATA_JSON__;
const SMOOTH = __SMOOTH_JSON__;
const BAND = __BAND_JSON__;
const X_MIN = __X_MIN__, X_MAX = __X_MAX__;
const IT_X = __IT_X__;
const YEAR_STEP = __YEAR_STEP__;

const svg = document.getElementById('chart');
const W = 1060, H = 360;
const M = {top: 14, right: 18, bottom: 32, left: 40};
const plotW = W - M.left - M.right;
const plotH = H - M.top - M.bottom;

const allY = DATA.map(d => d.score);
const yPad = 0.3;
const yMin = Math.floor((Math.min(...allY) - yPad) * 4) / 4;
const yMax = Math.ceil((Math.max(...allY) + yPad) * 4) / 4;

function x(v) { return M.left + ((v - X_MIN) / (X_MAX - X_MIN)) * plotW; }
function y(v) { return M.top + (1 - (v - yMin) / (yMax - yMin)) * plotH; }

function svgEl(tag, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) el.setAttribute(k, attrs[k]);
  return el;
}

const step = (yMax - yMin) > 3 ? 1 : 0.5;
for (let v = Math.ceil(yMin / step) * step; v <= yMax; v += step) {
  const gy = y(v);
  svg.appendChild(svgEl('line', {x1: M.left, x2: W - M.right, y1: gy, y2: gy, class: Math.abs(v) < 1e-9 ? 'baseline' : 'grid-line'}));
  const lbl = svgEl('text', {x: M.left - 8, y: gy + 4, class: 'axis-label', 'text-anchor': 'end'});
  lbl.textContent = (v > 0 ? '+' : '') + v.toFixed(step < 1 ? 1 : 0);
  svg.appendChild(lbl);
}

let lastYear = null;
DATA.forEach((d) => {
  const year = d.date.slice(0, 4);
  if (year !== lastYear && (parseInt(year) % YEAR_STEP === 0)) {
    const gx = x(d.x);
    const lbl = svgEl('text', {x: gx, y: H - M.bottom + 16, class: 'axis-label', 'text-anchor': 'middle'});
    lbl.textContent = year;
    svg.appendChild(lbl);
    lastYear = year;
  } else if (year !== lastYear) {
    lastYear = year;
  }
});

const axisTitle = svgEl('text', {x: (M.left + W - M.right) / 2, y: H - 2, class: 'axis-title', 'text-anchor': 'middle'});
axisTitle.textContent = 'Date';
svg.appendChild(axisTitle);
const yAxisTitle = svgEl('text', {x: -H/2 + M.bottom, y: 12, class: 'axis-title', 'text-anchor': 'middle', transform: 'rotate(-90)'});
yAxisTitle.textContent = 'Index Value';
svg.appendChild(yAxisTitle);

if (IT_X !== null) {
  const gx = x(IT_X);
  svg.appendChild(svgEl('line', {x1: gx, x2: gx, y1: M.top, y2: H - M.bottom, class: 'event-line'}));
}

let bandPath = '';
BAND.forEach((p, i) => {
  const px = x(p.x), pyTop = y(p.y + p.s);
  bandPath += (i === 0 ? 'M ' : 'L ') + px + ' ' + pyTop + ' ';
});
for (let i = BAND.length - 1; i >= 0; i--) {
  const p = BAND[i];
  bandPath += 'L ' + x(p.x) + ' ' + y(p.y - p.s) + ' ';
}
bandPath += 'Z';
svg.appendChild(svgEl('path', {d: bandPath, class: 'smooth-band'}));

let rawPath = '';
DATA.forEach((d, i) => { rawPath += (i === 0 ? 'M ' : 'L ') + x(d.x) + ' ' + y(d.score) + ' '; });
svg.appendChild(svgEl('path', {d: rawPath, class: 'raw-line'}));

const tooltip = document.getElementById('tooltip');
DATA.forEach((d) => {
  const isRate = d.action === 'hike' || d.action === 'cut';
  const cls = 'raw-dot' + (d.action ? ' ' + d.action : '');
  const dot = svgEl('circle', {cx: x(d.x), cy: y(d.score), r: isRate ? 3.6 : 2.3, class: cls});
  dot.addEventListener('mouseenter', (ev) => showTooltip(ev, d));
  dot.addEventListener('mousemove', positionTooltip);
  dot.addEventListener('mouseleave', () => tooltip.style.display = 'none');
  svg.appendChild(dot);
});

let smoothPath = '';
SMOOTH.forEach((p, i) => { smoothPath += (i === 0 ? 'M ' : 'L ') + x(p.x) + ' ' + y(p.y) + ' '; });
svg.appendChild(svgEl('path', {d: smoothPath, class: 'smooth-line'}));

const ACTION_LABEL = {hike: 'rate hike', cut: 'rate cut', hold: 'rate held'};
function showTooltip(ev, d) {
  let html = `<div style="font-weight:600">${d.date}${d.kind ? ' · ' + d.kind : ''}</div>`;
  html += `<div style="color:var(--text-secondary); margin-top:2px;">${(d.title || '').slice(0, 140)}</div>`;
  html += `<div style="margin-top:4px;">score ${d.score.toFixed(3)}</div>`;
  if (d.action) {
    html += `<div>${ACTION_LABEL[d.action] || d.action}${d.rate !== null && d.rate !== undefined ? ' · prevailing rate ' + d.rate + '%' : ''}</div>`;
  }
  tooltip.innerHTML = html;
  tooltip.style.display = 'block';
  positionTooltip(ev);
}
function positionTooltip(ev) {
  const pad = 16;
  let left = ev.clientX + pad, top = ev.clientY + pad;
  if (left + 300 > window.innerWidth) left = ev.clientX - 300 - pad;
  tooltip.style.left = left + 'px';
  tooltip.style.top = top + 'px';
}
</script>
"""
    script = (script.replace("__DATA_JSON__", data_json)
              .replace("__SMOOTH_JSON__", smooth_json)
              .replace("__BAND_JSON__", band_json)
              .replace("__X_MIN__", str(x_min))
              .replace("__X_MAX__", str(x_max))
              .replace("__IT_X__", "null" if it_x is None else str(it_x))
              .replace("__YEAR_STEP__", str(year_step)))

    body = f"""
<div class="viz-root">
  <div class="card">
    <h1>{title}</h1>
    <div class="sub">{subtitle}</div>
    <div class="legend">
      <span class="item"><span class="dotswatch" style="background:var(--raw)"></span> SI (Henry) — rate held / no associated decision</span>
      <span class="item"><span class="dotswatch" style="background:var(--hike)"></span> rate hike (at the meeting, or the most recent one before the document)</span>
      <span class="item"><span class="dotswatch" style="background:var(--cut)"></span> rate cut (same)</span>
      <span class="item"><span class="swatch" style="background:var(--smooth)"></span> SI (Henry), LOWESS-smoothed</span>
    </div>
    <svg id="chart" viewBox="0 0 1060 360" preserveAspectRatio="xMidYMid meet"></svg>
  </div>
</div>
<div class="note">{note}</div>
<div id="tooltip"></div>
"""

    html = f"<title>{title}</title>\n" + PAPER_STYLE + body + script
    out_path = config.REPORTS_DIR / f"{out_name}.html"
    out_path.write_text(html, encoding="utf-8")
    print("wrote", out_path, "n_points:", len(points))


def main():
    stmt_pts = load_points(config.PROCESSED_DIR / "scores_henry.csv", "meeting_date")
    speech_pts = load_points(config.PROCESSED_DIR / "speeches_scores_henry.csv", "publish_date")

    regimes = load_rate_regimes()
    attach_regime(stmt_pts, regimes)
    attach_regime(speech_pts, regimes)

    combined_pts = sorted(
        [{**p, "kind": "statement"} for p in stmt_pts] + [{**p, "kind": "speech"} for p in speech_pts],
        key=lambda p: p["date"],
    )

    global_max_date = combined_pts[-1]["date"]
    zoom_cutoff = (datetime.strptime(global_max_date, "%Y-%m-%d") - timedelta(days=365 * ZOOM_YEARS)).strftime("%Y-%m-%d")
    print("zoom cutoff (last", ZOOM_YEARS, "years):", zoom_cutoff)

    build_paper_chart(
        "final_01_statements_full", "SARB — Statements (MPC minutes), 1999–2026",
        "Henry (2008) index, 1 point per statement · smoothed red line (LOWESS)",
        [dict(p) for p in stmt_pts], frac=0.15,
        note="173 MPC statements. Vertical dotted line: adoption of the inflation-targeting regime (Feb 2000).",
    )
    build_paper_chart(
        "final_02_statements_zoom", "SARB — Statements, last 3 years",
        "Henry (2008) index, 1 point per statement · smoothed red line (LOWESS)",
        [dict(p) for p in stmt_pts], frac=0.4, zoom_cutoff=zoom_cutoff,
        note="Last 3 years (same series as the full statements chart).",
    )
    build_paper_chart(
        "final_03_speeches_full", "SARB — Speeches, 1994–2026",
        "Henry (2008) index, 1 point per speech · smoothed red line (LOWESS)",
        [dict(p) for p in speech_pts], frac=0.08,
        note="511 speeches with recovered text (of 604 indexed). Vertical dotted line: adoption of the inflation-targeting regime (Feb 2000).",
    )
    build_paper_chart(
        "final_04_speeches_zoom", "SARB — Speeches, last 3 years",
        "Henry (2008) index, 1 point per speech · smoothed red line (LOWESS)",
        [dict(p) for p in speech_pts], frac=0.25, zoom_cutoff=zoom_cutoff,
        note="Last 3 years (same series as the full speeches chart).",
    )
    build_paper_chart(
        "final_05_combined_full", "SARB — Statements + Speeches combined (pooled), 1994–2026",
        "Henry (2008) index, every document (statement OR speech) treated as 1 point on the same timeline",
        [dict(p) for p in combined_pts], frac=0.08,
        note="684 documents (173 statements + 511 speeches) pooled into a single chronological series, a direct replica of the paper's approach.",
    )
    build_paper_chart(
        "final_06_combined_zoom", "SARB — Statements + Speeches combined, last 3 years",
        "Henry (2008) index, every document (statement OR speech) treated as 1 point on the same timeline",
        [dict(p) for p in combined_pts], frac=0.2, zoom_cutoff=zoom_cutoff,
        note="Last 3 years (same series as the full combined chart).",
    )


if __name__ == "__main__":
    main()
