/*
 * timingdiff-core.js
 *
 * A JavaScript port of the Python parser.py + diff.py logic, so the whole
 * tool can run client-side on GitHub Pages: files never leave the browser,
 * there's no server and no Python required to try it.
 *
 * Kept as a faithful line-for-line port of the Python version so the two
 * stay in sync — see timingdiff/parser.py and timingdiff/diff.py.
 */

const REGRESSION_EPSILON = 0.005;

const RE_START = /^Startpoint:\s*(.+)$/;
const RE_END = /^Endpoint:\s*(.+)$/;
const RE_GROUP = /^Path Group:\s*(.+)$/;
const RE_TYPE = /^Path Type:\s*(.+)$/;
const RE_SLACK = /^\s*(-?\d+\.?\d*)\s+slack\s*\((MET|VIOLATED)\)\s*$/;
const RE_ARRIVAL = /^\s*(-?\d+\.?\d*)\s+data arrival time\s*$/;
const RE_STAGE = /^\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(.+?)\s*$/;

function stageCellType(description) {
  const m = description.match(/\(([^()]+)\)\s*$/);
  return m ? m[1] : null;
}
function stagePin(description) {
  const m = description.match(/^(\S+)/);
  return m ? m[1] : description;
}

/** Parse report_checks text into an array of path objects. */
function parseReport(text) {
  const paths = [];
  let current = null;
  let inStageBlock = false;
  let arrivalSeen = false;

  const lines = text.split(/\r?\n/);
  for (const rawLine of lines) {
    const line = rawLine.replace(/\s+$/, "");

    let m = line.match(RE_START);
    if (m) {
      if (current) paths.push(current);
      current = {
        startpoint: m[1].trim(),
        endpoint: "",
        path_group: "",
        path_type: "",
        stages: [],
        data_arrival_time: null,
        data_required_time: null,
        slack: null,
        met: null,
      };
      inStageBlock = false;
      arrivalSeen = false;
      continue;
    }
    if (!current) continue;

    m = line.match(RE_END);
    if (m) { current.endpoint = m[1].trim(); continue; }

    m = line.match(RE_GROUP);
    if (m) { current.path_group = m[1].trim(); continue; }

    m = line.match(RE_TYPE);
    if (m) { current.path_type = m[1].trim(); continue; }

    if (line.trim().startsWith("Delay") && line.includes("Description")) {
      inStageBlock = true;
      continue;
    }
    if (line.trim().startsWith("---")) continue;

    m = line.match(RE_ARRIVAL);
    if (m && !arrivalSeen) {
      current.data_arrival_time = parseFloat(m[1]);
      inStageBlock = false;
      arrivalSeen = true;
      continue;
    }

    if (line.trim().startsWith("data required time") && current.data_required_time === null) {
      const nums = line.match(/-?\d+\.\d+/g);
      if (nums) current.data_required_time = parseFloat(nums[0]);
      continue;
    }

    m = line.match(RE_SLACK);
    if (m) {
      current.slack = parseFloat(m[1]);
      current.met = m[2] === "MET";
      continue;
    }

    if (inStageBlock) {
      m = line.match(RE_STAGE);
      if (m) {
        current.stages.push({
          incr_delay: parseFloat(m[1]),
          time: parseFloat(m[2]),
          description: m[3].trim(),
        });
        continue;
      }
    }
  }
  if (current) paths.push(current);

  return paths
    .filter((p) => p.startpoint && p.endpoint)
    .map((p) => ({ ...p, key: `${p.startpoint}|${p.endpoint}|${p.path_group}` }));
}

function alignStages(before, after) {
  const deltas = [];
  const n = Math.max(before.length, after.length);
  for (let i = 0; i < n; i++) {
    const b = i < before.length ? before[i] : null;
    const a = i < after.length ? after[i] : null;
    const desc = (a || b) ? (a || b).description : "";
    const cellChanged = !!(b && a && stageCellType(b.description) !== stageCellType(a.description));
    const beforeDelay = b ? b.incr_delay : null;
    const afterDelay = a ? a.incr_delay : null;
    const delta = beforeDelay !== null && afterDelay !== null
      ? Math.round((afterDelay - beforeDelay) * 1000) / 1000
      : null;
    deltas.push({
      description: desc,
      before_delay: beforeDelay,
      after_delay: afterDelay,
      cell_changed: cellChanged,
      delta,
    });
  }
  return deltas;
}

/** Compare two parsed path lists, mirroring diff.py exactly. */
function diffReports(before, after) {
  const beforeMap = new Map(before.map((p) => [p.key, p]));
  const afterMap = new Map(after.map((p) => [p.key, p]));

  const allKeys = [];
  const seen = new Set();
  for (const p of [...before, ...after]) {
    if (!seen.has(p.key)) { seen.add(p.key); allKeys.push(p.key); }
  }

  const results = [];
  for (const key of allKeys) {
    const b = beforeMap.get(key);
    const a = afterMap.get(key);

    if (b && a) {
      const slackDelta = (a.slack || 0) - (b.slack || 0);
      let status;
      if (slackDelta < -REGRESSION_EPSILON) status = "worsened";
      else if (slackDelta > REGRESSION_EPSILON) status = "improved";
      else status = "unchanged";
      results.push({
        key, startpoint: a.startpoint, endpoint: a.endpoint, path_group: a.path_group,
        status, before_slack: b.slack, after_slack: a.slack,
        stage_deltas: alignStages(b.stages, a.stages),
        slack_delta: Math.round(slackDelta * 1000) / 1000,
      });
    } else if (a && !b) {
      results.push({
        key, startpoint: a.startpoint, endpoint: a.endpoint, path_group: a.path_group,
        status: "new", before_slack: null, after_slack: a.slack,
        stage_deltas: alignStages([], a.stages), slack_delta: null,
      });
    } else if (b && !a) {
      results.push({
        key, startpoint: b.startpoint, endpoint: b.endpoint, path_group: b.path_group,
        status: "removed", before_slack: b.slack, after_slack: null,
        stage_deltas: alignStages(b.stages, []), slack_delta: null,
      });
    }
  }

  const statusOrder = { worsened: 0, new: 1, removed: 2, improved: 3, unchanged: 4 };
  results.sort((x, y) => {
    const so = statusOrder[x.status] - statusOrder[y.status];
    if (so !== 0) return so;
    const mx = x.slack_delta !== null ? Math.abs(x.slack_delta) : 0;
    const my = y.slack_delta !== null ? Math.abs(y.slack_delta) : 0;
    return my - mx;
  });
  return results;
}

/** Summarize a diff array, mirroring diff.py's summarize(). */
function summarize(diffs) {
  const worsened = diffs.filter((d) => d.status === "worsened");
  const improved = diffs.filter((d) => d.status === "improved");
  const unchanged = diffs.filter((d) => d.status === "unchanged");
  const news = diffs.filter((d) => d.status === "new");
  const removed = diffs.filter((d) => d.status === "removed");

  const nowViolating = diffs.filter(
    (d) => d.after_slack !== null && d.after_slack < 0 &&
      !(d.before_slack !== null && d.before_slack < 0)
  ).length;
  const nowFixed = diffs.filter(
    (d) => d.before_slack !== null && d.before_slack < 0 &&
      d.after_slack !== null && d.after_slack >= 0
  ).length;

  const withDelta = diffs.filter((d) => d.slack_delta !== null);
  const worst = withDelta.length
    ? withDelta.reduce((a, b) => (a.slack_delta <= b.slack_delta ? a : b))
    : null;
  const best = withDelta.length
    ? withDelta.reduce((a, b) => (a.slack_delta >= b.slack_delta ? a : b))
    : null;

  return {
    total: diffs.length,
    worsened: worsened.length,
    improved: improved.length,
    unchanged: unchanged.length,
    new: news.length,
    removed: removed.length,
    now_violating: nowViolating,
    now_fixed: nowFixed,
    worst_regression: worst && worst.status === "worsened" ? worst : null,
    best_improvement: best && best.status === "improved" ? best : null,
  };
}
