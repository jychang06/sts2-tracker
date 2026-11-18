import json

from sts2_tracker.analysis import pick_rates, win_rates
from sts2_tracker.db import connect, scan_folder

from test_parser import _run


def _con(tmp_path):
    (tmp_path / "a.run").write_text(json.dumps(_run()))
    con = connect(":memory:")
    scan_folder(con, tmp_path, log=lambda m: None)
    return con


def test_filters(tmp_path):
    con = _con(tmp_path)
    df = pick_rates(con, "card")
    row = df[df.item == "CARD.BACKFLIP"].iloc[0]
    assert (row.offered, row.picked) == (1, 1)
    assert len(pick_rates(con, "card", item="deflect")) == 1          # substring, case-insensitive
    assert len(pick_rates(con, "card", floor_min=2)) == 0             # card reward was on floor 1
    assert len(pick_rates(con, "card", floor_min=1, floor_max=1)) == 2
    assert len(pick_rates(con, "card", character="CHARACTER.NOPE")) == 0
    assert len(pick_rates(con, "card", act=1, ascension=0, build="v0.98.3")) == 2


def test_empty_results_are_clean(tmp_path):
    con = _con(tmp_path)
    assert pick_rates(con, "card", item="zzzz").empty
    assert list(pick_rates(con, "card", item="zzzz").columns)[:3] == ["item", "offered", "picked"]


def test_win_rates(tmp_path):
    con = _con(tmp_path)
    df = win_rates(con, "character")
    assert (df.runs[0], df.wins[0]) == (1, 1)
