"""判型の確認：シリーズごとに書誌の標本をとり、大きさ（cm）を数える

OpenSearch の応答には大きさがないため、SRU（DC-NDL 形式）で取得する（tools/research/ndl.py の sru_extents）
- 標本：title=検索語 で最大20件（判型はシリーズの中でほとんど変わらないため少数で確かめる）（2016〜2025年に刊行のあるシリーズはその期間、ないシリーズは全期間）。
  書誌のシリーズ名が series_pattern に合うものだけを数える
- 新書判の目安：高さ 17〜18cm（JIS の B40 判 103×182mm 前後。書誌は cm 単位で切り上げて記録する）
- 標本であり全点ではない。判型の採否（新書判のシリーズか）の確認に使う
出力：data/sizes.csv
"""
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from tools.research import ndl  # noqa: E402

DATA = HERE.parent / "data"
SAMPLE = 20


def cm(extents):
    for e in extents:
        m = re.search(r"(\d+(?:\.\d+)?)\s*cm", unicodedata.normalize("NFKC", e))
        if m:
            return float(m.group(1))
    return None


def main():
    offline = "--offline" in sys.argv
    # 判型で除外したシリーズ（朝日文化手帖）も、除外の根拠として残す
    cands = list(csv.DictReader((DATA / "label_candidates.csv").open(encoding="utf-8")))
    recent = {r["label"] for r in csv.DictReader((DATA / "summary_labels.csv").open(encoding="utf-8"))}
    out = []
    for c in cands:
        cql = f'title="{c["query"].split("|")[0]}"' + (' AND from="2016" AND until="2025"' if c["label"] in recent else "")
        pat = re.compile(c["series_pattern"])
        hs = [cm(ext) for series, ext in ndl.sru_extents(cql, SAMPLE, offline=offline)
              if any(pat.search(unicodedata.normalize("NFKC", s)) or pat.search(s) for s in series)]
        hs = [h for h in hs if h]
        n = Counter(hs)
        out.append({"label": c["label"], "decision": c["decision"], "period": "2016-2025" if c["label"] in recent else "全期間",
                    "sample": len(hs), "height_mode_cm": n.most_common(1)[0][0] if n else "",
                    "share_17_18cm": round(sum(v for k, v in n.items() if 17 <= k <= 18) / len(hs), 3) if hs else "",
                    "heights": " ".join(f"{k:g}cm:{v}" for k, v in sorted(n.items()))})
        print(out[-1], flush=True)
    with (DATA / "sizes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(out[0]))
        w.writeheader()
        w.writerows(out)


if __name__ == "__main__":
    main()
