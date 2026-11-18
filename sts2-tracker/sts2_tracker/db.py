from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .parser import Run, parse_run

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(
  run_id TEXT PRIMARY KEY, seed TEXT, start_time INT, build_id TEXT, schema_version INT,
  character TEXT, ascension INT, game_mode TEXT, win INT, abandoned INT, run_time INT,
  killed_by TEXT, final_deck TEXT, final_relics TEXT);
CREATE TABLE IF NOT EXISTS choices(
  run_id TEXT REFERENCES runs, floor INT, act INT, node_type TEXT, kind TEXT,
  offered TEXT, picked TEXT, n_offered INT, n_picked INT);
CREATE TABLE IF NOT EXISTS options(          -- one row per offered item: the analysis workhorse
  run_id TEXT REFERENCES runs, floor INT, act INT, kind TEXT, item TEXT, was_picked INT);
CREATE TABLE IF NOT EXISTS floors(
  run_id TEXT REFERENCES runs, floor INT, act INT, node_type TEXT, room_id TEXT,
  hp INT, max_hp INT, gold INT, damage_taken INT, turns INT);
CREATE TABLE IF NOT EXISTS deck_changes(
  run_id TEXT REFERENCES runs, floor INT, act INT, node_type TEXT, action TEXT, card TEXT, detail TEXT);
CREATE INDEX IF NOT EXISTS ix_opt ON options(kind, item);
"""


def _ensure_column(con, table, col, decl):
    if col not in {r[1] for r in con.execute(f"PRAGMA table_info({table})")}:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def connect(path="sts2.db") -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    _ensure_column(con, "runs", "is_custom", "INT DEFAULT 0")   # added for schema 11
    _ensure_column(con, "runs", "badges", "TEXT")
    return con


def ingest_run(con, r: Run) -> bool:
    if con.execute("SELECT 1 FROM runs WHERE run_id=?", (r.run_id,)).fetchone():
        return False  # idempotent re-scan
    con.execute("INSERT INTO runs(run_id,seed,start_time,build_id,schema_version,character,ascension,"
                "game_mode,win,abandoned,run_time,killed_by,final_deck,final_relics) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        r.run_id, r.seed, r.start_time, r.build_id, r.schema_version, r.character, r.ascension,
        r.game_mode, int(r.win), int(r.abandoned), r.run_time, r.killed_by,
        json.dumps(r.final_deck), json.dumps(r.final_relics)))
    con.execute("UPDATE runs SET is_custom=?, badges=? WHERE run_id=?",
                (int(r.is_custom), json.dumps(r.badges), r.run_id))
    for d in r.deck_changes:
        con.execute("INSERT INTO deck_changes VALUES(?,?,?,?,?,?,?)", (
            r.run_id, d["floor"], d["act"], d["node_type"], d["action"], d["card"], d["detail"]))
    for c in r.choices:
        con.execute("INSERT INTO choices VALUES(?,?,?,?,?,?,?,?,?)", (
            r.run_id, c.floor, c.act, c.node_type, c.kind, json.dumps(c.offered),
            json.dumps(c.picked), len(c.offered), len(c.picked)))
        for item in c.offered:
            con.execute("INSERT INTO options VALUES(?,?,?,?,?,?)",
                        (r.run_id, c.floor, c.act, c.kind, item, int(item in c.picked)))
    for f in r.floors:
        con.execute("INSERT INTO floors VALUES(?,?,?,?,?,?,?,?,?,?)", (
            r.run_id, f["floor"], f["act"], f["node_type"], f["room_id"], f["hp"],
            f["max_hp"], f["gold"], f["damage_taken"], f["turns"]))
    return True


def scan_folder(con, folder, log=print) -> tuple[int, int, int]:
    new = dup = bad = 0
    for p in sorted(Path(folder).rglob("*.run")):
        try:
            if ingest_run(con, parse_run(p)):
                new += 1
            else:
                dup += 1
        except Exception as e:  # corrupt/partial/unsupported: log and continue
            bad += 1
            log(f"skip {p.name}: {e}")
    con.commit()
    return new, dup, bad
