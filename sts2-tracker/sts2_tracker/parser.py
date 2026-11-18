"""Parse Slay the Spire 2 .run files (schema_version 8 observed) into flat records."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_SCHEMAS = {8}


@dataclass
class Choice:
    floor: int            # 1-based, cumulative across acts
    act: int              # 1-based
    node_type: str        # monster / elite / boss / shop / unknown / ancient / treasure / rest_site
    kind: str             # card / relic / potion / ancient / rest / shop_card / shop_relic
    offered: list[str]
    picked: list[str]     # empty list = skipped everything


@dataclass
class Run:
    run_id: str
    seed: str
    start_time: int
    build_id: str
    schema_version: int
    character: str
    ascension: int
    game_mode: str
    win: bool
    abandoned: bool
    run_time: int
    killed_by: str | None
    final_deck: list[str]
    final_relics: list[str]
    choices: list[Choice] = field(default_factory=list)
    floors: list[dict] = field(default_factory=list)   # per-floor hp/gold snapshots


def _none(v):
    return None if v in (None, "NONE.NONE") else v


def parse_run(path: Path) -> Run:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if d.get("schema_version") not in SUPPORTED_SCHEMAS:
        raise ValueError(f"unsupported schema_version {d.get('schema_version')}")
    p = d["players"][0]  # single-player; extend for co-op
    run = Run(
        run_id=f"{d['start_time']}-{d['seed']}",
        seed=d["seed"], start_time=d["start_time"], build_id=d["build_id"],
        schema_version=d["schema_version"], character=p["character"],
        ascension=d.get("ascension", 0), game_mode=d.get("game_mode", ""),
        win=bool(d["win"]), abandoned=bool(d.get("was_abandoned")),
        run_time=d.get("run_time", 0),
        killed_by=_none(d.get("killed_by_encounter")) or _none(d.get("killed_by_event")),
        final_deck=[c["id"] for c in p["deck"]],
        final_relics=[r["id"] for r in p["relics"]],
    )
    floor = 0
    for act_i, act in enumerate(d["map_point_history"], 1):
        for node in act:
            floor += 1
            t = node["map_point_type"]
            ps = node["player_stats"][0]
            room = node["rooms"][0] if node.get("rooms") else {}
            run.floors.append(dict(
                floor=floor, act=act_i, node_type=t, room_id=room.get("model_id"),
                hp=ps.get("current_hp"), max_hp=ps.get("max_hp"), gold=ps.get("current_gold"),
                damage_taken=ps.get("damage_taken", 0), turns=room.get("turns_taken", 0)))

            def add(kind, offered, picked):
                if offered:
                    run.choices.append(Choice(floor, act_i, t, kind, offered, picked))

            cc = ps.get("card_choices") or []
            if t == "shop":
                # In shops was_picked is always false; purchases show up elsewhere.
                offered = [c["card"]["id"] for c in cc]
                gained = {c["id"] for c in ps.get("cards_gained", [])}
                bought = list(dict.fromkeys([x for x in offered if x in gained] + list(ps.get("bought_colorless") or [])))
                add("shop_card", offered, bought)
                rc = ps.get("relic_choices") or []
                add("shop_relic", [r["choice"] for r in rc], list(ps.get("bought_relics") or []))
            else:
                add("card", [c["card"]["id"] for c in cc],
                    [c["card"]["id"] for c in cc if c["was_picked"]])
                rc = ps.get("relic_choices") or []
                add("relic", [r["choice"] for r in rc],
                    [r["choice"] for r in rc if r["was_picked"]])
            pc = ps.get("potion_choices") or []
            if t != "shop":
                add("potion", [x["choice"] for x in pc], [x["choice"] for x in pc if x["was_picked"]])
            ac = ps.get("ancient_choice") or []
            add("ancient", [a["TextKey"] for a in ac], [a["TextKey"] for a in ac if a["was_chosen"]])
            if t == "rest_site":
                opts = ps.get("rest_site_choices") or []
                up = ps.get("upgraded_cards") or []
                add("rest", ["HEAL", "SMITH"], opts)  # offered set is an assumption; see README
                if up:
                    add("upgrade", [], up)
    return run
