from timingdiff.parser import parse_report

SAMPLE = """\
Startpoint: reg_a/CK (rising edge-triggered flip-flop clocked by clk)
Endpoint: reg_b/D (rising edge-triggered flip-flop clocked by clk)
Path Group: clk
Path Type: max

  Delay    Time   Description
---------------------------------------------------------
   0.00    0.00   clock clk (rise edge)
   0.00    0.00   clock network delay (ideal)
   0.00    0.00   reg_a/CK (DFF_X1)
   0.15    0.15   reg_a/Q (DFF_X1)
   0.32    0.47   u_and1/Z (AND2_X1)
   0.18    0.65   reg_b/D (DFF_X1)
   0.65           data arrival time

   1.20    1.20   clock clk (rise edge)
   0.00    1.20   clock network delay (ideal)
   0.00    1.20   reg_b/CK (DFF_X1)
  -0.05    1.15   library setup time
            1.15   data required time
---------------------------------------------------------
            1.15   data required time
           -0.65   data arrival time
---------------------------------------------------------
            0.50   slack (MET)
"""


def test_parses_single_path():
    paths = parse_report(SAMPLE)
    assert len(paths) == 1
    p = paths[0]
    assert p.startpoint == "reg_a/CK (rising edge-triggered flip-flop clocked by clk)"
    assert p.endpoint == "reg_b/D (rising edge-triggered flip-flop clocked by clk)"
    assert p.path_group == "clk"
    assert p.path_type == "max"
    assert p.slack == 0.50
    assert p.met is True
    assert p.data_arrival_time == 0.65


def test_stage_rows_extracted():
    p = parse_report(SAMPLE)[0]
    # stage rows captured up to (not including) "data arrival time" line
    descriptions = [s.description for s in p.stages]
    assert "reg_a/Q (DFF_X1)" in descriptions
    assert "u_and1/Z (AND2_X1)" in descriptions
    assert "reg_b/D (DFF_X1)" in descriptions


def test_stage_cell_type_and_pin():
    p = parse_report(SAMPLE)[0]
    and_stage = next(s for s in p.stages if "u_and1" in s.description)
    assert and_stage.cell_type == "AND2_X1"
    assert and_stage.pin == "u_and1/Z"


def test_violated_path_parses_negative_slack():
    text = SAMPLE.replace("0.50   slack (MET)", "-0.17   slack (VIOLATED)")
    p = parse_report(text)[0]
    assert p.slack == -0.17
    assert p.met is False


def test_multiple_paths_in_one_file():
    text = SAMPLE + "\n\n" + SAMPLE.replace("reg_a", "reg_c").replace("reg_b", "reg_d")
    paths = parse_report(text)
    assert len(paths) == 2
    assert paths[0].key != paths[1].key


def test_empty_input_returns_no_paths():
    assert parse_report("") == []
