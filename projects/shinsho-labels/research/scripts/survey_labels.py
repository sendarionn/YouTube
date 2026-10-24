"""予備調査：候補シリーズごとに、国立国会図書館サーチの件数と、検索結果がそのシリーズの本である割合を調べる

入力：data/label_candidates.csv（label, query, series_pattern）
出力：data/label_survey.csv
- hits：題名検索（title=シリーズ名）の件数。シリーズ名は書誌のシリーズ名でも一致する
- sample：最初の500件のうち、シリーズ名（dcndl:seriesTitle）が series_pattern に合う件数と、出版年の範囲
- 書誌レコード数であり、刊行点数ではない（重複の処理は collect.py で行う）
"""
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from tools.research import ndl  # noqa: E402

DATA = HERE.parent / "data"


def year(r):
    for v in r["issued"] + r["date"]:
        m = re.match(r"(\d{4})", v)
        if m:
            return int(m.group(1))
    return None


def main():
    rows = list(csv.DictReader((DATA / "label_candidates.csv").open(encoding="utf-8")))
    out = []
    for c in rows:
        params = {"dpid": "iss-ndl-opac", "title": c["query"]}
        hits = ndl.total(ndl.fetch({**params, "cnt": "1"}))
        sample = [ndl.parse_item(it) for it in ndl.fetch({**params, "cnt": "500"}).iter("item")]
        pat = re.compile(c["series_pattern"])
        match = [r for r in sample if any(pat.search(s) for s in r["series"])]
        years = sorted(y for y in map(year, match) if y)
        paper = sum("紙" in r["category"] for r in match)
        out.append({"label": c["label"], "category": c["category"], "hits": hits, "sample": len(sample),
                    "series_match": len(match), "paper": paper,
                    "year_min": years[0] if years else "", "year_max": years[-1] if years else "",
                    "series_examples": " | ".join(sorted({s for r in match[:200] for s in r["series"]})[:3])})
        print(out[-1]["label"], hits, len(sample), len(match), out[-1]["year_min"], out[-1]["year_max"], flush=True)
    with (DATA / "label_survey.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(out[0]))
        w.writeheader()
        w.writerows(out)


if __name__ == "__main__":
    main()
