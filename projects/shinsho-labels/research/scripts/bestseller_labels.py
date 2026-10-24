"""トーハン年間ベストセラー（新書ノンフィクション、2016〜2025年）の各点が、どのシリーズの本かを ISBN で照合して集計する

入力：cache/shinsho-labels/bestsellers_tohan.csv（bestsellers.py）、data/titles.csv
出力：data/bestseller_counts.csv（シリーズごとの上位10点への登場数。集計結果だけを Git 管理し、ランキングの表は配布しない）
- 同じ順位に複数の巻がある場合は1つの登場として数える
- 照合できない点（調査対象外のシリーズ、ISBN の不一致）は「対象外・照合できず」として数える
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from tools.infographic.config import CACHE  # noqa: E402

DATA = HERE.parent / "data"


def digits(isbn):
    """ISBN を13桁にそろえる（古い本の書誌は10桁の ISBN のことがある。例：物語ウクライナの歴史 2002年）"""
    d = re.sub(r"[^0-9X]", "", (isbn or "").upper())
    if len(d) == 10:
        core = "978" + d[:9]
        check = (10 - sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(core)) % 10) % 10
        d = core + str(check)
    return d


def main():
    by_isbn = {digits(t["isbn"]): t["label"] for t in csv.DictReader((DATA / "titles.csv").open(encoding="utf-8"))
               if t["isbn"]}
    seen, counts = set(), Counter()
    for r in csv.DictReader((CACHE / "shinsho-labels" / "bestsellers_tohan.csv").open(encoding="utf-8")):
        label = by_isbn.get(digits(r["isbn"]), "対象外・照合できず")
        key = (r["year"], r["rank"], label)
        if key in seen:
            continue
        seen.add(key)
        counts[label] += 1
    with (DATA / "bestseller_counts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "appearances_top10_2016_2025", "source"])
        for label, n in counts.most_common():
            w.writerow([label, n, "トーハン調べ 年間ベストセラー 新書ノンフィクション 2016〜2025年"])
    print(counts.most_common())


if __name__ == "__main__":
    main()
