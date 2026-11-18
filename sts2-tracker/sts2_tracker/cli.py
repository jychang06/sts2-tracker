import argparse

from .analysis import hp_curve, pick_rates
from .db import connect, scan_folder


def main():
    ap = argparse.ArgumentParser(prog="sts2")
    ap.add_argument("--db", default="sts2.db")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan"); s.add_argument("folder")
    r = sub.add_parser("report"); r.add_argument("--kind", default="card"); r.add_argument("--character")
    a = ap.parse_args()
    con = connect(a.db)
    if a.cmd == "scan":
        print("new=%d duplicate=%d failed=%d" % scan_folder(con, a.folder))
    else:
        print(pick_rates(con, a.kind, a.character).head(30).to_string(index=False))
        print(hp_curve(con).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
