"""
parser.py — turns a plain-text OpenSTA / PrimeTime `report_checks` timing
report into structured Python objects.

The parser is intentionally forgiving: OpenSTA and PrimeTime formats drift
slightly between versions and between -path_delay max/min, so we match on
the stable anchors (Startpoint / Endpoint / Path Group / slack line) and
treat everything else as best-effort stage rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Stage:
    """One row of the timing path: an incremental delay at a pin/cell."""

    incr_delay: float
    time: float
    description: str

    @property
    def cell_type(self) -> str | None:
        m = re.search(r"\(([^()]+)\)\s*$", self.description)
        return m.group(1) if m else None

    @property
    def pin(self) -> str:
        m = re.match(r"^(\S+)", self.description)
        return m.group(1) if m else self.description


@dataclass
class TimingPath:
    """A single timing path (startpoint -> endpoint) from a report."""

    startpoint: str
    endpoint: str
    path_group: str
    path_type: str
    stages: list[Stage] = field(default_factory=list)
    data_arrival_time: float | None = None
    data_required_time: float | None = None
    slack: float | None = None
    met: bool | None = None

    @property
    def key(self) -> str:
        """Identity used to match the same path across two reports."""
        return f"{self.startpoint}|{self.endpoint}|{self.path_group}"

    @property
    def logic_depth(self) -> int:
        """Number of combinational stages between the two flops."""
        return max(len(self.stages) - 1, 0)


_START_RE = re.compile(r"^Startpoint:\s*(.+)$")
_END_RE = re.compile(r"^Endpoint:\s*(.+)$")
_GROUP_RE = re.compile(r"^Path Group:\s*(.+)$")
_TYPE_RE = re.compile(r"^Path Type:\s*(.+)$")
_SLACK_RE = re.compile(r"^\s*(-?\d+\.?\d*)\s+slack\s*\((MET|VIOLATED)\)\s*$")
_ARRIVAL_RE = re.compile(r"^\s*(-?\d+\.?\d*)\s+data arrival time\s*$")
_STAGE_RE = re.compile(
    r"^\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(.+?)\s*$"
)


def parse_report(text: str) -> list[TimingPath]:
    """Parse the full contents of a report_checks text file into paths."""
    paths: list[TimingPath] = []
    current: TimingPath | None = None
    in_stage_block = False
    arrival_seen = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        m = _START_RE.match(line)
        if m:
            if current is not None:
                paths.append(current)
            current = TimingPath(
                startpoint=m.group(1).strip(),
                endpoint="",
                path_group="",
                path_type="",
            )
            in_stage_block = False
            arrival_seen = False
            continue

        if current is None:
            continue

        m = _END_RE.match(line)
        if m:
            current.endpoint = m.group(1).strip()
            continue

        m = _GROUP_RE.match(line)
        if m:
            current.path_group = m.group(1).strip()
            continue

        m = _TYPE_RE.match(line)
        if m:
            current.path_type = m.group(1).strip()
            continue

        if line.strip().startswith("Delay") and "Description" in line:
            in_stage_block = True
            continue

        if line.strip().startswith("---"):
            continue

        m = _ARRIVAL_RE.match(line)
        if m and not arrival_seen:
            current.data_arrival_time = float(m.group(1))
            in_stage_block = False
            arrival_seen = True
            continue

        if line.strip().startswith("data required time") and current.data_required_time is None:
            # "            1.15   data required time"
            nums = re.findall(r"-?\d+\.\d+", line)
            if nums:
                current.data_required_time = float(nums[0])
            continue

        m = _SLACK_RE.match(line)
        if m:
            current.slack = float(m.group(1))
            current.met = m.group(2) == "MET"
            continue

        if in_stage_block:
            m = _STAGE_RE.match(line)
            if m:
                incr, time, desc = m.groups()
                current.stages.append(Stage(float(incr), float(time), desc.strip()))
                continue

    if current is not None:
        paths.append(current)

    return [p for p in paths if p.startpoint and p.endpoint]


def parse_report_file(path: str) -> list[TimingPath]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return parse_report(f.read())
