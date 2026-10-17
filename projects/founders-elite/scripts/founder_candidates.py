"""創業者が未特定の企業について、役員略歴から創業者候補を探す

Iの部と転載ページ（最新の有価証券報告書）の役員略歴を対象に、
「当社設立」「（現当社）設立」「当社創業」等の記載がある役員を候補として出力する
候補は判定用であり、採否は screening.csv に人手で反映する
"""
import json
import re

import pandas as pd

from build_founders import mirror_officers
from paths import CACHE, DATA

PAT = re.compile(r"(当社|現当社|現 当社|現・当社|（現当社）|\(現当社\))[^/]{0,12}(設立|創業|創立)|(設立|創業)[^/]{0,6}(当社|現当社)|創業者|共同創業")


def main():
    s = pd.read_csv(DATA / "screening.csv", dtype=str).fillna("")
    ext = {json.loads(l)["key"]: json.loads(l) for l in open(CACHE / "part1_extract.jsonl", encoding="utf-8")}
    s["age"] = s.key.str[:4].astype(int) - pd.to_numeric(s.origin_ym.str[:4], errors="coerce")
    t = s[s.founders.str.contains(r"\?") & s.type.isin(["IND", "SPIN", "UNIV", "HOLD", "UNK"]) & ((s.age <= 25) | s.age.isna())]
    for r in t.itertuples():
        offs = ext.get(r.key, {}).get("officers", [])
        src = "P1"
        hits = [o for o in offs if PAT.search(o["career"].replace("/", ""))]
        if not hits:
            moffs, msrc = mirror_officers(r.key)
            hits = [o for o in moffs if PAT.search(o["career"].replace("/", ""))]
            src = f"MIRROR {msrc}"
        for o in hits:
            m = PAT.search(o["career"].replace("/", ""))
            ctx = o["career"].replace("/", "")[max(0, m.start() - 40):m.end() + 20]
            print(f"{r.key}\t{r.origin_ym}\t{o['name']}\t{o['birth'][:4]}\t{src}\t…{ctx}…")


if __name__ == "__main__":
    main()
