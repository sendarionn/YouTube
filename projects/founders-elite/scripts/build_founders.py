"""判定結果から創業者の台帳を作る

screening.csv の founders 列の人物を、Iの部の役員一覧と照合し、生年と略歴を付ける
出力: data/founders_base.csv（1人1行）
"""
import json
import re

import pandas as pd

from extract_part1 import ZEN, officers, seireki
from paths import CACHE, DATA


def norm(name):
    return re.sub(r"[\s　・]", "", name or "")


def mirror_officers(key):
    """Iの部にない場合に、有価証券報告書の転載ページの役員一覧を使う"""
    f = CACHE / "mirror" / f"{key}_board.txt"
    if not f.exists():
        return [], ""
    t = seireki(f.read_text(encoding="utf-8").translate(ZEN))
    src = re.search(r"SOURCE: (.*)", t)
    if "【役員の状況】" not in t:
        return [], ""
    offs, _ = officers([t.split("【役員の状況】", 1)[1]])
    return offs, (src.group(1) if src else "")


def main():
    s = pd.read_csv(DATA / "screening.csv", dtype=str).fillna("")
    jpx = pd.read_csv(DATA / "jpx_listings.csv", dtype=str)
    jpx["key"] = jpx.listing_date + "_" + jpx.code
    names = dict(zip(jpx.key, jpx.company_name))
    ext = {json.loads(l)["key"]: json.loads(l) for l in open(CACHE / "part1_extract.jsonl", encoding="utf-8")}
    rows = []
    for r in s.itertuples():
        if r.type not in ("IND", "SPIN", "UNIV"):
            continue
        offs = ext.get(r.key, {}).get("officers", [])
        for i, f in enumerate([x for x in r.founders.split(";") if x]):
            o = next((o for o in offs if norm(o["name"]) == norm(f)), None)
            career_src = "P1" if o else ""
            if o is None and f != "?":
                moffs, msrc = mirror_officers(r.key)
                o = next((o for o in moffs if norm(o["name"]) == norm(f)), None)
                career_src = f"MIRROR {msrc}" if o else ""
            rows.append({
                "founder_id": f"{r.key}_{i + 1}",
                "key": r.key,
                "company": names.get(r.key, ""),
                "origin_ym": r.origin_ym,
                "name": "" if f == "?" else norm(f),
                "birth": o["birth"] if o else "",
                "title_at_ipo": o["title"] if o else "",
                "on_board_at_ipo": "Y" if career_src == "P1" else ("" if f == "?" or career_src else "N"),
                "career_p1": o["career"] if o else "",
                "career_source": career_src,
            })
    out = pd.DataFrame(rows)
    out.to_csv(DATA / "founders_base.csv", index=False)
    print(len(out), "人", (out.name == "").sum(), "名前不明", (out.birth != "").sum(), "略歴あり")


if __name__ == "__main__":
    main()
