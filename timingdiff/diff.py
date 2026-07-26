"""
diff.py — compares two lists of TimingPath objects (before/after) and
produces a structured diff: matched paths with slack/stage deltas, plus
paths that only exist on one side.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .parser import TimingPath, Stage

REGRESSION_EPSILON = 0.005  # ps/ns-agnostic noise floor for "unchanged"


@dataclass
class StageDelta:
    description: str
    before_delay: float | None
    after_delay: float | None
    cell_changed: bool

    @property
    def delta(self) -> float | None:
        if self.before_delay is None or self.after_delay is None:
            return None
        return round(self.after_delay - self.before_delay, 3)


@dataclass
class PathDiff:
    key: str
    startpoint: str
    endpoint: str
    path_group: str
    status: str  # "worsened" | "improved" | "unchanged" | "new" | "removed"
    before_slack: float | None
    after_slack: float | None
    stage_deltas: list[StageDelta] = field(default_factory=list)

    @property
    def slack_delta(self) -> float | None:
        if self.before_slack is None or self.after_slack is None:
            return None
        return round(self.after_slack - self.before_slack, 3)


def _align_stages(before: list[Stage], after: list[Stage]) -> list[StageDelta]:
    """Best-effort positional alignment of stage rows between two paths.

    Real STA reports keep pin ordering stable stage-to-stage unless cells
    were inserted/removed by re-synthesis or buffering, so we align by
    position and flag cell-type changes; this is enough to spot which
    stage of the path absorbed the delta.
    """
    deltas: list[StageDelta] = []
    n = max(len(before), len(after))
    for i in range(n):
        b = before[i] if i < len(before) else None
        a = after[i] if i < len(after) else None
        desc = (a or b).description if (a or b) else ""
        cell_changed = bool(b and a and b.cell_type != a.cell_type)
        deltas.append(
            StageDelta(
                description=desc,
                before_delay=b.incr_delay if b else None,
                after_delay=a.incr_delay if a else None,
                cell_changed=cell_changed,
            )
        )
    return deltas


def diff_reports(before: list[TimingPath], after: list[TimingPath]) -> list[PathDiff]:
    before_map = {p.key: p for p in before}
    after_map = {p.key: p for p in after}

    all_keys = list(dict.fromkeys([*before_map.keys(), *after_map.keys()]))
    results: list[PathDiff] = []

    for key in all_keys:
        b = before_map.get(key)
        a = after_map.get(key)

        if b and a:
            slack_delta = (a.slack or 0) - (b.slack or 0)
            if slack_delta < -REGRESSION_EPSILON:
                status = "worsened"
            elif slack_delta > REGRESSION_EPSILON:
                status = "improved"
            else:
                status = "unchanged"
            results.append(
                PathDiff(
                    key=key,
                    startpoint=a.startpoint,
                    endpoint=a.endpoint,
                    path_group=a.path_group,
                    status=status,
                    before_slack=b.slack,
                    after_slack=a.slack,
                    stage_deltas=_align_stages(b.stages, a.stages),
                )
            )
        elif a and not b:
            results.append(
                PathDiff(
                    key=key,
                    startpoint=a.startpoint,
                    endpoint=a.endpoint,
                    path_group=a.path_group,
                    status="new",
                    before_slack=None,
                    after_slack=a.slack,
                    stage_deltas=_align_stages([], a.stages),
                )
            )
        elif b and not a:
            results.append(
                PathDiff(
                    key=key,
                    startpoint=b.startpoint,
                    endpoint=b.endpoint,
                    path_group=b.path_group,
                    status="removed",
                    before_slack=b.slack,
                    after_slack=None,
                    stage_deltas=_align_stages(b.stages, []),
                )
            )

    # Worst regressions first, then improvements, then new/removed, then unchanged.
    status_order = {"worsened": 0, "new": 1, "removed": 2, "improved": 3, "unchanged": 4}

    def sort_key(d: PathDiff):
        delta = d.slack_delta
        magnitude = abs(delta) if delta is not None else 0
        return (status_order[d.status], -magnitude)

    return sorted(results, key=sort_key)


@dataclass
class DiffSummary:
    total: int
    worsened: int
    improved: int
    unchanged: int
    new: int
    removed: int
    worst_regression: PathDiff | None
    best_improvement: PathDiff | None
    now_violating: int
    now_fixed: int


def summarize(diffs: list[PathDiff]) -> DiffSummary:
    worsened = [d for d in diffs if d.status == "worsened"]
    improved = [d for d in diffs if d.status == "improved"]
    unchanged = [d for d in diffs if d.status == "unchanged"]
    new = [d for d in diffs if d.status == "new"]
    removed = [d for d in diffs if d.status == "removed"]

    now_violating = sum(
        1 for d in diffs
        if d.after_slack is not None and d.after_slack < 0
        and not (d.before_slack is not None and d.before_slack < 0)
    )
    now_fixed = sum(
        1 for d in diffs
        if d.before_slack is not None and d.before_slack < 0
        and d.after_slack is not None and d.after_slack >= 0
    )

    worst = min(
        (d for d in diffs if d.slack_delta is not None),
        key=lambda d: d.slack_delta,
        default=None,
    )
    best = max(
        (d for d in diffs if d.slack_delta is not None),
        key=lambda d: d.slack_delta,
        default=None,
    )

    return DiffSummary(
        total=len(diffs),
        worsened=len(worsened),
        improved=len(improved),
        unchanged=len(unchanged),
        new=len(new),
        removed=len(removed),
        worst_regression=worst if worst and worst.status == "worsened" else None,
        best_improvement=best if best and best.status == "improved" else None,
        now_violating=now_violating,
        now_fixed=now_fixed,
    )
