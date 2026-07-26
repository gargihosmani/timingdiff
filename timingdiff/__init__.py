"""timingdiff — a git-diff-style visual comparator for STA timing reports."""

from .parser import parse_report, parse_report_file, TimingPath, Stage
from .diff import diff_reports, summarize, PathDiff, StageDelta, DiffSummary
from .report import render_html

__all__ = [
    "parse_report",
    "parse_report_file",
    "TimingPath",
    "Stage",
    "diff_reports",
    "summarize",
    "PathDiff",
    "StageDelta",
    "DiffSummary",
    "render_html",
]

__version__ = "0.1.0"
