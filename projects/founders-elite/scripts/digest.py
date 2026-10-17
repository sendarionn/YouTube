"""判定作業用のダイジェストを出力する

使い方: python digest.py [年 ...]
各社の沿革冒頭と、代表者・創業者候補の略歴を1社数行にまとめて表示する
"""
import json
import re
import sys

import pandas as pd

from paths import CACHE, DATA

SETUP = re.compile(r"設立|創業|創立|開業|発足")


def short(s, n):
    s = re.sub(r"\s+", " ", s or "")
    return s if len(s) <= n else s[:n] + "…"


def compact_career(c):
    """日付だけが連続する列は読み取りに不要なので除く"""
    c = re.sub(r"(/\d{4}年\s*\d{1,2}月){3,}", "", c)
    return c.replace("/", " ")


def main():
    years = sys.argv[1:]
    jpx = pd.read_csv(DATA / "jpx_listings.csv", dtype=str)
    jpx["key"] = jpx.listing_date + "_" + jpx.code
    ext = {json.loads(l)["key"]: json.loads(l) for l in open(CACHE / "part1_extract.jsonl", encoding="utf-8")}
    rows = jpx[jpx.technical_listing == "0"]
    if years:
        rows = rows[rows.listing_year.isin(years)]
    for r in rows.itertuples():
        e = ext.get(r.key)
        print(f"## {r.key} {r.company_name} [{r.market}]")
        if not e:
            print("  (Iの部なし)")
            continue
        years = [int(d[:4]) for d, _ in e.get("history", [])]
        years += [int(y) for y in re.findall(r"(1[89]\d\d|20[0-2]\d)年", e.get("history_intro", ""))]
        earliest = min(years) if years else None
        if earliest and int(r.listing_year) - earliest >= 25:
            rep = e["officers"][0] if e.get("officers") else {}
            print(f"  [OLD] 最古{earliest} {short(e['history'][0][1] if e.get('history') else '', 70)} / 代表 {rep.get('name', '')}"
                  + ("" if not any(o["founder_flag"] for o in e.get("officers", [])) else " ★創業者候補あり"))
            continue
        if e.get("history_intro"):
            print("  沿革前文:", short(e["history_intro"], 160))
        hist = e.get("history", [])
        picked = hist[:3] + [h for h in hist[3:] if SETUP.search(h[1])][:3]
        for d, t in picked:
            print(f"  {d} {short(t, 110)}")
        offs = e.get("officers", [])
        shown = [o for i, o in enumerate(offs) if i == 0 or o["founder_flag"]]
        for o in shown:
            flag = "★" if o["founder_flag"] else ""
            print(f"  {flag}{short(o['title'], 24)} {o['name']} ({o['birth'][:4]}) {short(compact_career(o['career']), 220)}")


if __name__ == "__main__":
    main()
