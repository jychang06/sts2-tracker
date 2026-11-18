import json

from sts2_tracker.db import connect, scan_folder
from sts2_tracker.parser import parse_run


def _run():
    stats = {"current_hp": 70, "max_hp": 70, "current_gold": 99, "damage_taken": 0, "player_id": 1}
    return {
        "schema_version": 8, "build_id": "v0.98.3", "seed": "TESTSEED", "start_time": 1,
        "ascension": 0, "game_mode": "standard", "win": True, "was_abandoned": False,
        "run_time": 100, "killed_by_encounter": "NONE.NONE", "killed_by_event": "NONE.NONE",
        "acts": ["ACT.OVERGROWTH"],
        "players": [{"character": "CHARACTER.SILENT", "deck": [{"id": "CARD.BACKFLIP"}],
                     "relics": [{"id": "RELIC.RING_OF_THE_SNAKE"}], "potions": []}],
        "map_point_history": [[
            {"map_point_type": "monster", "rooms": [{"room_type": "monster"}], "player_stats": [dict(
                stats, card_choices=[
                    {"card": {"id": "CARD.BACKFLIP"}, "was_picked": True},
                    {"card": {"id": "CARD.DEFLECT"}, "was_picked": False}])]},
            {"map_point_type": "shop", "rooms": [{"room_type": "shop"}], "player_stats": [dict(
                stats, card_choices=[{"card": {"id": "CARD.PANACHE"}, "was_picked": False}],
                cards_gained=[{"id": "CARD.PANACHE"}], bought_colorless=["CARD.PANACHE"])]},
        ]],
    }


def test_parse_choices(tmp_path):
    p = tmp_path / "a.run"
    p.write_text(json.dumps(_run()))
    r = parse_run(p)
    assert r.win and r.character == "CHARACTER.SILENT"
    card = [c for c in r.choices if c.kind == "card"][0]
    assert card.offered == ["CARD.BACKFLIP", "CARD.DEFLECT"] and card.picked == ["CARD.BACKFLIP"]
    shop = [c for c in r.choices if c.kind == "shop_card"][0]
    assert shop.picked == ["CARD.PANACHE"]  # detected once, not double-counted


def test_scan_is_idempotent_and_skips_bad_files(tmp_path):
    (tmp_path / "a.run").write_text(json.dumps(_run()))
    (tmp_path / "bad.run").write_text("{not json")
    con = connect(":memory:")
    assert scan_folder(con, tmp_path, log=lambda m: None) == (1, 0, 1)
    assert scan_folder(con, tmp_path, log=lambda m: None) == (0, 1, 1)
