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


def pick_rates(con, kind="card", character=None, act=None, floor_min=None, floor_max=None,
               ascension=None, build=None, item=None, min_offered=1) -> pd.DataFrame:
    """Pick rate = picked / times offered, with Wilson CI.

    Every filter is optional and they combine with AND. `item` is a case-insensitive
    substring match on the item id (e.g. "backflip" matches CARD.BACKFLIP).
    """
    where, args = ["o.kind=?"], [kind]
    for clause, val in [("r.character=?", character), ("o.act=?", act),
                        ("o.floor>=?", floor_min), ("o.floor<=?", floor_max),
                        ("r.ascension=?", ascension), ("r.build_id=?", build)]:
        if val is not None:
            where.append(clause)
            args.append(val)
    if item:
        where.append("UPPER(o.item) LIKE ?")
        args.append(f"%{item.upper()}%")
    df = pd.read_sql_query(
        f"""SELECT o.item, COUNT(*) offered, SUM(o.was_picked) picked
            FROM options o JOIN runs r USING(run_id) WHERE {" AND ".join(where)}
            GROUP BY o.item""", con, params=args)
    df = df[df.offered >= min_offered].copy()
    if df.empty:
        return pd.DataFrame(columns=["item", "offered", "picked", "pick_rate", "ci_low", "ci_high"])
    df["pick_rate"] = df.picked / df.offered
    ci = df.apply(lambda r: wilson(int(r.picked), int(r.offered)), axis=1)
    df["ci_low"], df["ci_high"] = [x[0] for x in ci], [x[1] for x in ci]
    return df.sort_values(["offered", "item"], ascending=[False, True]).reset_index(drop=True)


def win_rates(con, by="character") -> pd.DataFrame:
    """Run win rate grouped by character, ascension or build, with Wilson CI.
    Abandoned runs are excluded."""
    col = {"character": "character", "ascension": "ascension", "build": "build_id"}[by]
    df = pd.read_sql_query(
        f"SELECT {col} AS {by}, COUNT(*) runs, SUM(win) wins FROM runs "
        f"WHERE abandoned=0 GROUP BY {col} ORDER BY runs DESC", con)
    if df.empty:
        return pd.DataFrame(columns=[by, "runs", "wins", "win_rate", "ci_low", "ci_high"])
    df["win_rate"] = df.wins / df.runs
    ci = df.apply(lambda r: wilson(int(r.wins), int(r.runs)), axis=1)
    df["ci_low"], df["ci_high"] = [x[0] for x in ci], [x[1] for x in ci]
    return df


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
