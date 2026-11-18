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
                stats, card_choices=[{"card": {"id": "CARD.GOLD_AXE"}, "was_picked": False}],
                cards_gained=[{"id": "CARD.PANACHE"}],
                cards_removed=[{"id": "CARD.STRIKE_SILENT"}])]},
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
    # shop card_choices holds only unbought stock; purchases come from cards_gained
    assert shop.offered == ["CARD.GOLD_AXE", "CARD.PANACHE"] and shop.picked == ["CARD.PANACHE"]
    assert [(d["action"], d["card"]) for d in r.deck_changes] == [("remove", "CARD.STRIKE_SILENT")]


def test_scan_is_idempotent_and_skips_bad_files(tmp_path):
    (tmp_path / "a.run").write_text(json.dumps(_run()))
    (tmp_path / "bad.run").write_text("{not json")
    con = connect(":memory:")
    assert scan_folder(con, tmp_path, log=lambda m: None) == (1, 0, 1)
    assert scan_folder(con, tmp_path, log=lambda m: None) == (0, 1, 1)


def test_newer_schema_parses_with_warning(tmp_path, caplog):
    d = _run()
    d["schema_version"] = 99
    d["is_custom_game"] = True
    d["players"][0]["badges"] = [{"id": "ELITE", "rarity": "bronze"}]
    d["map_point_history"][0][0]["player_stats"][0]["brand_new_key"] = 1
    p = tmp_path / "n.run"
    p.write_text(json.dumps(d))
    r = parse_run(p)
    assert r.is_custom and r.badges == ["ELITE"]
    assert "newer than verified" in caplog.text and "brand_new_key" in caplog.text


def test_too_old_schema_rejected(tmp_path):
    d = _run()
    d["schema_version"] = 3
    p = tmp_path / "o.run"
    p.write_text(json.dumps(d))
    try:
        parse_run(p)
        assert False, "should have raised"
    except ValueError:
        pass
