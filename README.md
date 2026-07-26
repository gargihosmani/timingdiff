# timingdiff

**`git diff`, but for timing closure.**

`timingdiff` compares two STA (Static Timing Analysis) reports — from
[OpenSTA](https://github.com/The-OpenROAD-Project/OpenSTA) or
PrimeTime — and renders an interactive, visual diff: which paths got
better, which got worse, which are new or gone, and exactly which stage
of each path absorbed the delay change.

Today, engineers usually diff timing closure by eyeballing two text
reports side by side. `timingdiff` turns that into something you can
scan in seconds.

![timingdiff screenshot](docs/screenshot.png)

<details>
<summary>Expanded path view (stage-by-stage diff)</summary>

![timingdiff expanded row](docs/screenshot-expanded.png)
</details>

## Why

- **Zero setup to view.** Output is a single self-contained HTML file — no server, no build step, works offline once generated.
- **Sorts regressions to the top.** The worst timing regression across your whole design is always the first thing you see.
- **Stage-level attribution.** Click into any path to see a git-diff-style, colored breakdown of every cell/net delay, so you know exactly where the delta came from — not just that the path got worse.
- **CI-friendly.** `--fail-on-regression` exits non-zero if any path worsened or newly violates timing, and `--json` dumps the raw diff for scripting.

## Install

```bash
git clone https://github.com/<you>/timingdiff.git
cd timingdiff
pip install -e .
```

Requires Python 3.10+. No other dependencies — the whole tool is
stdlib Python plus a self-contained HTML/CSS/JS template.

## Usage

```bash
timingdiff before.rpt after.rpt -o diff.html --open
```

Generate `before.rpt` / `after.rpt` from OpenSTA with something like:

```tcl
report_checks -path_delay max -group_count 50 > before.rpt
# ... make your RTL/constraint/placement change ...
report_checks -path_delay max -group_count 50 > after.rpt
```

Then try it on the bundled sample data:

```bash
timingdiff samples/before.rpt samples/after.rpt -o demo.html --open
```

### CLI options

| Flag | Description |
|---|---|
| `-o, --output PATH` | output HTML file (default `timingdiff.html`) |
| `--open` | open the report in your default browser after generating it |
| `--json PATH` | also write the raw diff as JSON, for scripting/CI dashboards |
| `--fail-on-regression` | exit with status `1` if any path worsened or newly violates timing |

## How it works

1. **`parser.py`** reads a `report_checks`-style text report and extracts each timing path: startpoint, endpoint, path group, the incremental-delay stage table, and the final slack.
2. **`diff.py`** matches paths across the two reports by `(startpoint, endpoint, path group)`, computes the slack delta, and positionally aligns each path's stage rows to flag which cell delays changed (and whether the cell type itself changed, e.g. a resize during ECO).
3. **`report.py`** renders everything into one HTML file: sortable/filterable path list, per-path "waterfall" of stage deltas, and an expandable git-diff-colored stage table.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Roadmap / ideas

- [ ] Min (hold) path support alongside max (setup)
- [ ] Multi-corner diffing (compare across PVT corners, not just before/after)
- [ ] Direct OpenROAD `.def`/SPEF hooks to auto-generate before/after reports from two GDS iterations
- [ ] `--group-by` to roll up regressions by clock domain or module hierarchy

Contributions and issues welcome.

## License

MIT — see [LICENSE](LICENSE).
