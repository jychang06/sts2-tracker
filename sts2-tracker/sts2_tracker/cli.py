import argparse
import logging

from .analysis import hp_curve, pick_rates, win_rates
from .db import connect, scan_folder


def _floor_range(text):
    """'12' -> (12, 12); '10-20' -> (10, 20); '30-' -> (30, None); '-5' -> (None, 5)."""
    if text is None:
        return None, None
    if "-" not in text:
        return int(text), int(text)
    lo, hi = text.split("-", 1)
    return (int(lo) if lo else None), (int(hi) if hi else None)


def main():
    ap = argparse.ArgumentParser(prog="sts2")
    ap.add_argument("--db", default="sts2.db")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="import .run files from a folder")
    s.add_argument("folder")

    r = sub.add_parser("report", help="pick rates for offered cards/relics/potions/etc.")
    r.add_argument("--kind", default="card",
                   help="card, relic, potion, ancient, rest, shop_card, shop_relic, shop_potion")
    r.add_argument("--character", help="e.g. CHARACTER.SILENT")
    r.add_argument("--act", type=int, help="1, 2 or 3")
    r.add_argument("--floor", help="a floor (12), a range (10-20), or open-ended (30- / -5)")
    r.add_argument("--ascension", type=int)
    r.add_argument("--build", help="game build, e.g. v0.113.1")
    r.add_argument("--item", help="substring of an item id, e.g. backflip")
    r.add_argument("--min-offered", type=int, default=1)
    r.add_argument("--limit", type=int, default=30)

    w = sub.add_parser("winrate", help="run win rates")
    w.add_argument("--by", choices=["character", "ascension", "build"], default="character")

    sub.add_parser("hp", help="average HP fraction and damage by floor")

    a = ap.parse_args()
    if a.cmd == "report":
        try:
            _floor_range(a.floor)
        except ValueError:
            ap.error("--floor must look like 12, 10-20, 30- or -5")
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    con = connect(a.db)
    if a.cmd == "scan":
        print("new=%d duplicate=%d failed=%d" % scan_folder(con, a.folder))
    elif a.cmd == "report":
        lo, hi = _floor_range(a.floor)
        df = pick_rates(con, a.kind, a.character, a.act, lo, hi, a.ascension, a.build,
                        a.item, a.min_offered)
        print(df.head(a.limit).to_string(index=False, float_format=lambda x: f"{x:.3f}")
              if len(df) else "no matching data")
    elif a.cmd == "winrate":
        print(win_rates(con, a.by).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    else:
        print(hp_curve(con).to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
