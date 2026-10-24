"""分野の比較の統計量：data/ndc_by_label.csv と data/summary_labels.csv から計算する

出力：data/ndc_stats.csv（全体の指標）、data/ndc_distance.csv（一般向けのレーベルの組み合わせごとの距離）
定義
- 対象：横断比較（2016〜2025年）の一般向け（category=general）で compared=1 のレーベル
- クラメールの V：レーベル × NDC 第1次区分の分割表から。0 で無関係、1 でレーベルが分野を完全に決める
- 距離：NDC 構成比のジェンセン・シャノン距離（底2、0〜1）。0 で構成が同じ
"""
import csv
import math
import statistics as st
from collections import defaultdict
from itertools import combinations
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def targets():
    with open(DATA / "summary_labels.csv", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["category"] == "general" and r["compared"] == "1"]
    return {r["label"]: float(r["ndc_hhi"]) for r in rows}


def table(labels):
    t = defaultdict(lambda: [0] * 10)
    with open(DATA / "ndc_by_label.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["label"] in labels and r["ndc_class"].isdigit():
                t[r["label"]][int(r["ndc_class"])] = int(r["titles"])
    return dict(t)


def cramers_v(t):
    rows = list(t.values())
    n = sum(map(sum, rows))
    cols = [sum(c) for c in zip(*rows)]
    keep = [i for i, c in enumerate(cols) if c]
    chi2 = 0.0
    for r in rows:
        rs = sum(r)
        for i in keep:
            e = rs * cols[i] / n
            chi2 += (r[i] - e) ** 2 / e
    k = min(len(rows), len(keep)) - 1
    return math.sqrt(chi2 / (n * k)), n


def jsd(p, q):
    def kl(a, b):
        return sum(x * math.log2(x / y) for x, y in zip(a, b) if x)
    m = [(x + y) / 2 for x, y in zip(p, q)]
    return math.sqrt((kl(p, m) + kl(q, m)) / 2)


def main():
    hhi = targets()
    t = table(hhi)
    v, n = cramers_v(t)
    share = {k: [x / sum(r) for x in r] for k, r in t.items()}
    pairs = sorted((jsd(share[a], share[b]), a, b) for a, b in combinations(sorted(share), 2))
    with open(DATA / "ndc_stats.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["labels", len(t)])
        w.writerow(["titles_with_ndc", n])
        w.writerow(["cramers_v", round(v, 3)])
        w.writerow(["hhi_median", round(st.median(hhi.values()), 3)])
        w.writerow(["jsd_median", round(st.median(d for d, _, _ in pairs), 3)])
    with open(DATA / "ndc_distance.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label_a", "label_b", "jsd"])
        for d, a, b in pairs:
            w.writerow([a, b, round(d, 3)])
    print(f"一般向け {len(t)} レーベル、{n} 点、V = {v:.3f}")
    for d, a, b in pairs[:5] + pairs[-5:]:
        print(f"  {a} - {b}: {d:.3f}")


if __name__ == "__main__":
    main()
