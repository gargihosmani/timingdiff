"""
cli.py — command-line entry point.

    timingdiff before.rpt after.rpt -o diff.html
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser

from .parser import parse_report_file
from .diff import diff_reports, summarize
from .report import render_html


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="timingdiff",
        description="Compare two OpenSTA/PrimeTime timing reports and generate an interactive HTML diff.",
    )
    p.add_argument("before", help="path to the earlier (baseline) report_checks text file")
    p.add_argument("after", help="path to the later report_checks text file")
    p.add_argument(
        "-o", "--output", default="timingdiff.html",
        help="output HTML file path (default: timingdiff.html)",
    )
    p.add_argument(
        "--open", action="store_true",
        help="open the generated report in the default browser",
    )
    p.add_argument(
        "--json", metavar="PATH",
        help="also write the raw diff data as JSON to PATH (for CI / scripting)",
    )
    p.add_argument(
        "--fail-on-regression", action="store_true",
        help="exit with status 1 if any path worsened or newly violates timing (useful in CI)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    for f in (args.before, args.after):
        if not os.path.isfile(f):
            print(f"timingdiff: error: no such file: {f}", file=sys.stderr)
            return 2

    before_paths = parse_report_file(args.before)
    after_paths = parse_report_file(args.after)

    if not before_paths:
        print(f"timingdiff: warning: no timing paths parsed from {args.before}", file=sys.stderr)
    if not after_paths:
        print(f"timingdiff: warning: no timing paths parsed from {args.after}", file=sys.stderr)

    diffs = diff_reports(before_paths, after_paths)
    summary = summarize(diffs)

    html = render_html(
        diffs, summary,
        before_label=os.path.basename(args.before),
        after_label=os.path.basename(args.after),
    )
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"timingdiff: {summary.total} paths compared "
          f"({summary.worsened} worsened, {summary.improved} improved, "
          f"{summary.new} new, {summary.removed} removed)")
    if summary.now_violating:
        print(f"timingdiff: {summary.now_violating} path(s) newly VIOLATING", file=sys.stderr)
    print(f"timingdiff: wrote {args.output}")

    if args.json:
        import json
        from dataclasses import asdict
        payload = {
            "summary": {k: v for k, v in asdict(summary).items()
                        if k not in ("worst_regression", "best_improvement")},
            "diffs": [asdict(d) | {"slack_delta": d.slack_delta} for d in diffs],
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"timingdiff: wrote {args.json}")

    if args.open:
        webbrowser.open(f"file://{os.path.abspath(args.output)}")

    if args.fail_on_regression and (summary.worsened > 0 or summary.now_violating > 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
