from __future__ import annotations

import math

import pandas as pd


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def pick_rates(con, kind="card", character=None, min_offered=1) -> pd.DataFrame:
    """Pick rate = picked / times offered, with Wilson CI."""
    q = """SELECT o.item, COUNT(*) offered, SUM(o.was_picked) picked
           FROM options o JOIN runs r USING(run_id) WHERE o.kind=? {c} GROUP BY o.item"""
    args = [kind]
    c = ""
    if character:
        c, args = "AND r.character=?", args + [character]
    df = pd.read_sql_query(q.format(c=c), con, params=args)
    df = df[df.offered >= min_offered].copy()
    df["pick_rate"] = df.picked / df.offered
    ci = df.apply(lambda r: wilson(int(r.picked), int(r.offered)), axis=1)
    df["ci_low"], df["ci_high"] = [x[0] for x in ci], [x[1] for x in ci]
    return df.sort_values("offered", ascending=False).reset_index(drop=True)


def win_rate_by_pick(con, kind="card", min_runs=5) -> pd.DataFrame:
    """Naive win rate for runs that picked each item (confounded! see README)."""
    df = pd.read_sql_query(
        """SELECT o.item, COUNT(DISTINCT o.run_id) runs, SUM(r.win) * 1.0 / COUNT(*) win_rate
           FROM options o JOIN runs r USING(run_id)
           WHERE o.kind=? AND o.was_picked=1 GROUP BY o.item HAVING runs>=?""",
        con, params=(kind, min_runs))
    return df.sort_values("win_rate", ascending=False)


def hp_curve(con) -> pd.DataFrame:
    return pd.read_sql_query(
        """SELECT f.floor, AVG(f.hp*1.0/f.max_hp) hp_frac, AVG(f.damage_taken) dmg, COUNT(*) n
           FROM floors f GROUP BY f.floor ORDER BY f.floor""", con)
