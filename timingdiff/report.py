"""
report.py — renders a PathDiff list into a single self-contained,
interactive HTML file. No server, no build step: open it in a browser.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from .diff import PathDiff, DiffSummary


def _diff_to_dict(d: PathDiff) -> dict:
    out = asdict(d)
    out["slack_delta"] = d.slack_delta
    for sd, sd_out in zip(d.stage_deltas, out["stage_deltas"]):
        sd_out["delta"] = sd.delta
    return out


def render_html(
    diffs: list[PathDiff],
    summary: DiffSummary,
    before_label: str,
    after_label: str,
) -> str:
    data = {
        "before_label": before_label,
        "after_label": after_label,
        "summary": asdict(summary) | {
            "worst_regression": _diff_to_dict(summary.worst_regression) if summary.worst_regression else None,
            "best_improvement": _diff_to_dict(summary.best_improvement) if summary.best_improvement else None,
        },
        "diffs": [_diff_to_dict(d) for d in diffs],
    }
    payload = json.dumps(data)
    return _TEMPLATE.replace("__TIMINGDIFF_DATA__", payload)


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>timingdiff</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0b0e14;
  --surface:#111623;
  --surface-raised:#161d2c;
  --border:#232b3d;
  --text:#d7dce5;
  --text-muted:#7c8797;
  --text-dim:#525b6b;
  --worse:#ff6b6b;
  --worse-dim:#4a2b2f;
  --better:#4fd67a;
  --better-dim:#20402d;
  --new:#e0a339;
  --new-dim:#453118;
  --removed:#8b93a3;
  --removed-dim:#2a2f3a;
  --accent:#5b8cff;
  --radius:6px;
  --mono:'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
  --sans:'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}
*{box-sizing:border-box;}
html,body{margin:0;padding:0;}
body{
  background:var(--bg);
  color:var(--text);
  font-family:var(--sans);
  line-height:1.5;
  -webkit-font-smoothing:antialiased;
}
a{color:var(--accent);}
::selection{background:#2a3a5c;}
:focus-visible{outline:2px solid var(--accent); outline-offset:2px;}

.wrap{max-width:1080px; margin:0 auto; padding:32px 20px 80px;}

header.top{
  display:flex; align-items:baseline; justify-content:space-between;
  flex-wrap:wrap; gap:8px 24px;
  padding-bottom:20px; border-bottom:1px solid var(--border); margin-bottom:24px;
}
.brand{display:flex; align-items:baseline; gap:10px;}
.brand h1{
  font-family:var(--mono); font-size:20px; font-weight:700; margin:0;
  letter-spacing:-0.02em;
}
.brand h1 .dim{color:var(--text-dim); font-weight:500;}
.brand .tagline{color:var(--text-muted); font-size:13px; font-family:var(--mono);}
.compare-line{font-family:var(--mono); font-size:13px; color:var(--text-muted);}
.compare-line .before{color:var(--worse);}
.compare-line .after{color:var(--better);}
.compare-line .arrow{color:var(--text-dim); margin:0 6px;}

.stats{
  display:grid; grid-template-columns:repeat(6,1fr); gap:1px;
  background:var(--border); border:1px solid var(--border); border-radius:var(--radius);
  overflow:hidden; margin-bottom:24px;
}
.stat{background:var(--surface); padding:14px 12px; text-align:left;}
.stat .n{font-family:var(--mono); font-size:22px; font-weight:600; line-height:1.1;}
.stat .l{font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:.06em; margin-top:4px;}
.stat.worse .n{color:var(--worse);}
.stat.better .n{color:var(--better);}
.stat.new .n{color:var(--new);}
.stat.removed .n{color:var(--removed);}

.callouts{display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:24px;}
.callout{
  background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
  padding:12px 14px; font-family:var(--mono); font-size:12.5px;
}
.callout .h{color:var(--text-muted); font-size:10.5px; text-transform:uppercase; letter-spacing:.06em; margin-bottom:6px;}
.callout .path{color:var(--text); word-break:break-all;}
.callout.worse{border-left:3px solid var(--worse);}
.callout.better{border-left:3px solid var(--better);}
.callout .delta{float:right; font-weight:600;}
.callout.worse .delta{color:var(--worse);}
.callout.better .delta{color:var(--better);}

.controls{
  display:flex; gap:10px; margin-bottom:16px; flex-wrap:wrap; align-items:center;
}
.search{
  flex:1; min-width:200px; background:var(--surface); border:1px solid var(--border);
  border-radius:var(--radius); padding:8px 12px; color:var(--text); font-family:var(--mono);
  font-size:13px;
}
.search::placeholder{color:var(--text-dim);}
.chips{display:flex; gap:6px; flex-wrap:wrap;}
.chip{
  font-family:var(--mono); font-size:11.5px; padding:6px 10px; border-radius:20px;
  border:1px solid var(--border); background:var(--surface); color:var(--text-muted);
  cursor:pointer; user-select:none; transition:border-color .12s, color .12s;
}
.chip:hover{border-color:var(--text-dim);}
.chip.active{color:var(--bg); font-weight:600;}
.chip[data-status="worsened"].active{background:var(--worse); border-color:var(--worse);}
.chip[data-status="improved"].active{background:var(--better); border-color:var(--better);}
.chip[data-status="new"].active{background:var(--new); border-color:var(--new);}
.chip[data-status="removed"].active{background:var(--removed); border-color:var(--removed);}
.chip[data-status="unchanged"].active{background:var(--text-dim); border-color:var(--text-dim); color:var(--bg);}
.chip[data-status="all"].active{background:var(--accent); border-color:var(--accent); color:#fff;}

table.diff{width:100%; border-collapse:collapse; font-family:var(--mono); font-size:12.5px;}
.path-row{
  background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
  margin-bottom:6px; overflow:hidden;
}
.row-head{
  display:grid;
  grid-template-columns: 14px 1fr 140px 90px 90px 22px;
  gap:12px; align-items:center; padding:10px 12px; cursor:pointer;
}
.row-head:hover{background:var(--surface-raised);}
.status-dot{width:8px; height:8px; border-radius:50%; justify-self:center;}
.status-dot.worsened{background:var(--worse);}
.status-dot.improved{background:var(--better);}
.status-dot.new{background:var(--new);}
.status-dot.removed{background:var(--removed);}
.status-dot.unchanged{background:var(--text-dim);}

.endpoints{overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0;}
.endpoints .sp{color:var(--text-muted);}
.endpoints .arrow{color:var(--text-dim); margin:0 6px;}
.endpoints .ep{color:var(--text);}

.waterfall{display:flex; align-items:center; height:10px; gap:1px;}
.waterfall .seg{height:100%; min-width:1px;}
.waterfall .seg.pos{background:var(--worse);}
.waterfall .seg.neg{background:var(--better);}
.waterfall .seg.flat{background:var(--text-dim); opacity:.4;}

.slack-val{text-align:right; white-space:nowrap;}
.slack-val.neg{color:var(--worse);}
.slack-val.pos{color:var(--text-muted);}

.delta-val{text-align:right; font-weight:600; white-space:nowrap;}
.delta-val.worse{color:var(--worse);}
.delta-val.better{color:var(--better);}
.delta-val.flat{color:var(--text-dim); font-weight:400;}
.delta-val.na{color:var(--text-dim); font-weight:400;}

.chevron{color:var(--text-dim); justify-self:center; transition:transform .15s;}
.path-row.open .chevron{transform:rotate(90deg);}

.row-detail{display:none; border-top:1px solid var(--border); padding:12px 16px 16px;}
.path-row.open .row-detail{display:block;}
.detail-meta{color:var(--text-muted); font-size:11px; margin-bottom:10px;}
.stage-table{width:100%; border-collapse:collapse;}
.stage-table th{
  text-align:left; font-size:10px; text-transform:uppercase; letter-spacing:.05em;
  color:var(--text-dim); font-weight:500; padding:4px 8px; border-bottom:1px solid var(--border);
}
.stage-table td{padding:4px 8px; border-bottom:1px solid #1a2030; white-space:nowrap;}
.stage-table td.desc{white-space:normal; color:var(--text-muted); width:100%;}
.stage-table td.desc .cell-tag{color:var(--text-dim);}
.stage-table td.desc .cell-changed{color:var(--new);}
.stage-table tr.stage-added td{background:rgba(79,214,122,0.06);}
.stage-table tr.stage-removed td{background:rgba(255,107,107,0.06);}
.num{text-align:right; font-variant-numeric:tabular-nums;}

.empty{color:var(--text-dim); text-align:center; padding:40px 0; font-family:var(--mono); font-size:13px;}

footer{margin-top:32px; color:var(--text-dim); font-size:11px; font-family:var(--mono); text-align:center;}
footer a{color:var(--text-dim); text-decoration:underline;}

@media (max-width:640px){
  .stats{grid-template-columns:repeat(3,1fr);}
  .callouts{grid-template-columns:1fr;}
  .row-head{grid-template-columns: 12px 1fr 70px 22px;}
  .row-head .waterfall, .row-head .slack-val{display:none;}
}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div class="brand">
      <h1>timing<span class="dim">diff</span></h1>
      <span class="tagline">git diff, for timing closure</span>
    </div>
    <div class="compare-line" id="compareLine"></div>
  </header>

  <div class="stats" id="stats"></div>
  <div class="callouts" id="callouts"></div>

  <div class="controls">
    <input class="search" id="search" type="text" placeholder="filter by startpoint, endpoint, or cell…">
    <div class="chips" id="chips"></div>
  </div>

  <table class="diff"><tbody id="rows"></tbody></table>
  <div class="empty" id="emptyState" style="display:none;">no paths match this filter</div>

  <footer>generated by <a href="https://github.com/" target="_blank" rel="noopener">timingdiff</a> — a visual comparator for OpenSTA / PrimeTime timing reports</footer>
</div>

<script type="application/json" id="timingdiff-data">__TIMINGDIFF_DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('timingdiff-data').textContent);
const STATUS_LABEL = {worsened:'Worsened', improved:'Improved', new:'New', removed:'Removed', unchanged:'Unchanged'};

function fmt(n, digits=3){
  if(n === null || n === undefined) return '—';
  const s = n.toFixed(digits);
  return (n > 0 ? '+' : '') + s;
}
function fmtPlain(n, digits=3){
  if(n === null || n === undefined) return '—';
  return n.toFixed(digits);
}

document.getElementById('compareLine').innerHTML =
  `<span class="before">${DATA.before_label}</span><span class="arrow">→</span><span class="after">${DATA.after_label}</span>`;

const s = DATA.summary;
const statsEl = document.getElementById('stats');
const statCards = [
  {n: s.total, l: 'Total Paths', cls:''},
  {n: s.worsened, l: 'Worsened', cls:'worse'},
  {n: s.improved, l: 'Improved', cls:'better'},
  {n: s.new, l: 'New', cls:'new'},
  {n: s.removed, l: 'Removed', cls:'removed'},
  {n: s.now_violating, l: 'Now Violating', cls:'worse'},
];
statsEl.innerHTML = statCards.map(c =>
  `<div class="stat ${c.cls}"><div class="n">${c.n}</div><div class="l">${c.l}</div></div>`
).join('');

const calloutsEl = document.getElementById('callouts');
let calloutHtml = '';
if(s.worst_regression){
  const d = s.worst_regression;
  calloutHtml += `<div class="callout worse"><div class="h">Worst Regression <span class="delta">${fmt(d.slack_delta)} ns</span></div><div class="path">${d.startpoint} → ${d.endpoint}</div></div>`;
}
if(s.best_improvement){
  const d = s.best_improvement;
  calloutHtml += `<div class="callout better"><div class="h">Best Improvement <span class="delta">${fmt(d.slack_delta)} ns</span></div><div class="path">${d.startpoint} → ${d.endpoint}</div></div>`;
}
calloutsEl.innerHTML = calloutHtml;

const chipDefs = [
  {status:'all', label:'All'},
  {status:'worsened', label:`Worsened (${s.worsened})`},
  {status:'improved', label:`Improved (${s.improved})`},
  {status:'new', label:`New (${s.new})`},
  {status:'removed', label:`Removed (${s.removed})`},
  {status:'unchanged', label:`Unchanged (${s.unchanged})`},
];
const chipsEl = document.getElementById('chips');
chipsEl.innerHTML = chipDefs.map(c => `<div class="chip" data-status="${c.status}">${c.label}</div>`).join('');

let activeStatus = 'all';
let searchTerm = '';

function waterfallHtml(stageDeltas){
  if(!stageDeltas || !stageDeltas.length) return '';
  const maxAbs = Math.max(1, ...stageDeltas.map(d => Math.abs(d.delta || 0)));
  return '<div class="waterfall">' + stageDeltas.map(d => {
    if(d.delta === null || d.delta === undefined) return `<span class="seg flat" style="flex:1"></span>`;
    const w = Math.max(4, Math.round((Math.abs(d.delta)/maxAbs)*100));
    const cls = d.delta > 0.001 ? 'pos' : (d.delta < -0.001 ? 'neg' : 'flat');
    return `<span class="seg ${cls}" style="flex:${w}"></span>`;
  }).join('') + '</div>';
}

function stageRowsHtml(diff){
  return diff.stage_deltas.map(sd => {
    let cls = '';
    if(sd.before_delay === null) cls = 'stage-added';
    else if(sd.after_delay === null) cls = 'stage-removed';
    const deltaCls = sd.delta === null ? 'na' : (sd.delta > 0.001 ? 'worse' : (sd.delta < -0.001 ? 'better' : 'flat'));
    const descHtml = sd.cell_changed
      ? sd.description.replace(/\(([^()]+)\)\s*$/, '<span class="cell-changed">($1)</span>')
      : `<span class="cell-tag">${sd.description}</span>`;
    return `<tr class="${cls}">
      <td class="num">${fmtPlain(sd.before_delay)}</td>
      <td class="num">${fmtPlain(sd.after_delay)}</td>
      <td class="num delta-val ${deltaCls}">${fmt(sd.delta)}</td>
      <td class="desc">${descHtml}</td>
    </tr>`;
  }).join('');
}

function rowHtml(diff, idx){
  const slackCls = (diff.after_slack !== null && diff.after_slack < 0) ? 'neg' : 'pos';
  const deltaCls = diff.slack_delta === null ? 'na' : (diff.slack_delta > 0.001 ? 'worse' : (diff.slack_delta < -0.001 ? 'better' : 'flat'));
  return `
  <tr class="path-row" data-idx="${idx}">
    <td colspan="6">
      <div class="row-head" data-toggle="${idx}">
        <span class="status-dot ${diff.status}"></span>
        <span class="endpoints"><span class="sp">${diff.startpoint}</span><span class="arrow">→</span><span class="ep">${diff.endpoint}</span></span>
        ${waterfallHtml(diff.stage_deltas)}
        <span class="slack-val ${slackCls}">${fmtPlain(diff.after_slack)} ns</span>
        <span class="delta-val ${deltaCls}">${fmt(diff.slack_delta)}</span>
        <span class="chevron">›</span>
      </div>
      <div class="row-detail">
        <div class="detail-meta">path group: ${diff.path_group} · status: ${STATUS_LABEL[diff.status]||diff.status} · slack before ${fmtPlain(diff.before_slack)} ns → after ${fmtPlain(diff.after_slack)} ns</div>
        <table class="stage-table">
          <thead><tr><th class="num">Before (ns)</th><th class="num">After (ns)</th><th class="num">Δ (ns)</th><th>Stage</th></tr></thead>
          <tbody>${stageRowsHtml(diff)}</tbody>
        </table>
      </div>
    </td>
  </tr>`;
}

function matchesSearch(diff, term){
  if(!term) return true;
  const hay = (diff.startpoint + ' ' + diff.endpoint + ' ' +
    diff.stage_deltas.map(d => d.description).join(' ')).toLowerCase();
  return hay.includes(term);
}

function render(){
  const rowsEl = document.getElementById('rows');
  const filtered = DATA.diffs.filter(d =>
    (activeStatus === 'all' || d.status === activeStatus) && matchesSearch(d, searchTerm)
  );
  document.getElementById('emptyState').style.display = filtered.length ? 'none' : 'block';
  rowsEl.innerHTML = filtered.map((d, i) => rowHtml(d, i)).join('');

  document.querySelectorAll('[data-toggle]').forEach(el => {
    el.addEventListener('click', () => {
      el.closest('.path-row').classList.toggle('open');
    });
  });
}

chipsEl.addEventListener('click', (e) => {
  const chip = e.target.closest('.chip');
  if(!chip) return;
  activeStatus = chip.dataset.status;
  document.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c === chip));
  render();
});

document.getElementById('search').addEventListener('input', (e) => {
  searchTerm = e.target.value.trim().toLowerCase();
  render();
});

document.querySelector('.chip[data-status="all"]').classList.add('active');
render();
</script>
</body>
</html>
"""
