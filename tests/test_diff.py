from timingdiff.parser import TimingPath, Stage
from timingdiff.diff import diff_reports, summarize


def make_path(sp, ep, slack, stages=None, group="clk"):
    return TimingPath(
        startpoint=sp, endpoint=ep, path_group=group, path_type="max",
        stages=stages or [], slack=slack, met=slack >= 0,
    )


def test_matched_path_improved():
    before = [make_path("a", "b", 0.10)]
    after = [make_path("a", "b", 0.30)]
    diffs = diff_reports(before, after)
    assert len(diffs) == 1
    assert diffs[0].status == "improved"
    assert diffs[0].slack_delta == 0.20


def test_matched_path_worsened():
    before = [make_path("a", "b", 0.30)]
    after = [make_path("a", "b", -0.05)]
    diffs = diff_reports(before, after)
    assert diffs[0].status == "worsened"
    assert diffs[0].slack_delta == -0.35


def test_matched_path_unchanged_within_epsilon():
    before = [make_path("a", "b", 0.30)]
    after = [make_path("a", "b", 0.302)]
    diffs = diff_reports(before, after)
    assert diffs[0].status == "unchanged"


def test_new_and_removed_paths():
    before = [make_path("a", "b", 0.30), make_path("x", "y", 0.10)]
    after = [make_path("a", "b", 0.30), make_path("m", "n", 0.05)]
    diffs = diff_reports(before, after)
    statuses = {d.key: d.status for d in diffs}
    assert statuses["x|y|clk"] == "removed"
    assert statuses["m|n|clk"] == "new"


def test_sort_order_worst_regression_first():
    before = [make_path("a", "b", 0.50), make_path("c", "d", 0.10)]
    after = [make_path("a", "b", -0.40), make_path("c", "d", 0.05)]
    diffs = diff_reports(before, after)
    assert diffs[0].key == "a|b|clk"  # bigger regression sorts first


def test_summary_counts_and_violations():
    before = [make_path("a", "b", 0.20), make_path("c", "d", -0.10)]
    after = [make_path("a", "b", -0.05), make_path("c", "d", 0.15)]
    diffs = diff_reports(before, after)
    s = summarize(diffs)
    assert s.total == 2
    assert s.worsened == 1
    assert s.improved == 1
    assert s.now_violating == 1  # a->b newly violates
    assert s.now_fixed == 1      # c->d got fixed


def test_stage_alignment_flags_cell_change():
    before_stages = [Stage(0.30, 0.30, "u1/Z (AND2_X1)")]
    after_stages = [Stage(0.20, 0.20, "u1/Z (AND2_X2)")]
    before = [make_path("a", "b", 0.10, stages=before_stages)]
    after = [make_path("a", "b", 0.20, stages=after_stages)]
    diffs = diff_reports(before, after)
    sd = diffs[0].stage_deltas[0]
    assert sd.cell_changed is True
    assert sd.delta == -0.10
