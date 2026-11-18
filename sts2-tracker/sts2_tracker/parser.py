"""Parse Slay the Spire 2 .run files (schema_version 8 observed) into flat records."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import logging

log = logging.getLogger("sts2")

MIN_SCHEMA = 8          # oldest layout verified
MAX_VERIFIED_SCHEMA = 11  # newest layout verified; newer files parse with a warning

# Keys inside per-floor player_stats that this parser understands (or knowingly ignores).
KNOWN_STATS_KEYS = {
    "ancient_choice", "bought_colorless", "bought_potions", "bought_relics", "card_choices",
    "cards_enchanted", "cards_gained", "cards_removed", "cards_transformed", "current_gold",
    "current_hp", "damage_taken", "downgraded_cards", "event_choices", "gold_gained",
    "gold_lost", "gold_spent", "gold_stolen", "hp_healed", "is_affected_by_fur_coat",
    "max_hp", "max_hp_gained", "max_hp_lost", "max_potion_slot_count", "player_id",
    "potion_choices", "potion_discarded", "potion_used", "relic_choices",
    "rest_site_choices", "stolen_loot", "upgraded_cards",
}
_warned_keys: set[str] = set()


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
    is_custom: bool = False
    badges: list[str] = field(default_factory=list)
    deck_changes: list[dict] = field(default_factory=list)  # removals/transforms/upgrades/downgrades
    choices: list[Choice] = field(default_factory=list)
    floors: list[dict] = field(default_factory=list)   # per-floor hp/gold snapshots


def _none(v):
    return None if v in (None, "NONE.NONE") else v


def parse_run(path: Path) -> Run:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    sv = d.get("schema_version")
    if not isinstance(sv, int) or sv < MIN_SCHEMA:
        raise ValueError(f"unsupported schema_version {sv}")
    if sv > MAX_VERIFIED_SCHEMA:
        log.warning("schema_version %s is newer than verified (%s); parsing best-effort", sv, MAX_VERIFIED_SCHEMA)
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
        is_custom=bool(d.get("is_custom_game", False)),
        badges=[b["id"] for b in p.get("badges", [])],
    )
    floor = 0
    for act_i, act in enumerate(d["map_point_history"], 1):
        for node in act:
            floor += 1
            t = node["map_point_type"]
            ps = node["player_stats"][0]
            for k in set(ps) - KNOWN_STATS_KEYS - _warned_keys:  # drift detector
                _warned_keys.add(k)
                log.warning("unrecognized player_stats key %r (schema %s) - parser may be missing data", k, sv)
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
                # Verified on 2 files / 10 purchases: shop card_choices lists only the UNBOUGHT
                # stock (was_picked is always false) and purchased cards appear in cards_gained.
                remaining = [c["card"]["id"] for c in cc]
                bought = [c["id"] for c in ps.get("cards_gained", [])]
                add("shop_card", remaining + bought, bought)
                rc = ps.get("relic_choices") or []
                add("shop_relic", [r["choice"] for r in rc], list(ps.get("bought_relics") or []))
                pc = ps.get("potion_choices") or []
                add("shop_potion", [x["choice"] for x in pc], list(ps.get("bought_potions") or []))
            else:
                add("card", [c["card"]["id"] for c in cc],
                    [c["card"]["id"] for c in cc if c["was_picked"]])
                rc = ps.get("relic_choices") or []
                add("relic", [r["choice"] for r in rc],
                    [r["choice"] for r in rc if r["was_picked"]])
            def change(action, card, detail=None):
                run.deck_changes.append(dict(floor=floor, act=act_i, node_type=t, action=action,
                                             card=card, detail=detail))
            for c in ps.get("cards_removed") or []:
                change("remove", c["id"])
            for c in ps.get("cards_transformed") or []:
                change("transform", c["original_card"]["id"], c["final_card"]["id"])
            for cid in ps.get("upgraded_cards") or []:
                change("upgrade", cid)
            for cid in ps.get("downgraded_cards") or []:
                change("downgrade", cid)
            pc = ps.get("potion_choices") or []
            if t != "shop":
                add("potion", [x["choice"] for x in pc], [x["choice"] for x in pc if x["was_picked"]])
            ac = ps.get("ancient_choice") or []
            add("ancient", [a["TextKey"] for a in ac], [a["TextKey"] for a in ac if a["was_chosen"]])
            if t == "rest_site":
                opts = ps.get("rest_site_choices") or []
                up = ps.get("upgraded_cards") or []
                add("rest", ["HEAL", "SMITH"], opts)  # offered set is an assumption; see README

    return run
