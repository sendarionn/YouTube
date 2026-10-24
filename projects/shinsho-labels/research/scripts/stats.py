"""分野の比較の統計量：data/titles.csv と data/summary_labels.csv から計算する

分析の3層（methodology.md「分析の構造」）
- 全シリーズ（scope=all）：区分を問わず、横断比較の期間（2016〜2025年）に刊行のあるすべてのシリーズ。主分析
- 区分ごと（scope=category:<区分>）：一般・科学・ジュニアなど、同じ区分のシリーズどうし。追加分析
- 区分の間（scope=between_categories）：シリーズではなく区分を単位にした関連の強さ
シリーズごとの特徴（特化係数など）は analyze.py の ndc_specialization.csv

出力
- data/ndc_stats.csv：層・分類の細かさ（第1次区分 class／綱 division）ごとのクラメールの V、集中度・距離の中央値
- data/ndc_distance.csv：シリーズの組み合わせごとの距離（区分が同じか、点数）
- data/ndc_nearest.csv：シリーズごとに最も近いシリーズ
- data/ndc_v_by_decade.csv：10年ごとのクラメールの V（シリーズの違いが時代とともに大きく・小さくなったか）。
  その10年に DECADE_MIN 点以上のシリーズだけを使う
定義
- クラメールの V：シリーズ × 分野の分割表から。0 で無関係、1 でシリーズが分野を完全に決める
- 距離：分野の構成比のジェンセン・シャノン距離（底2、0〜1）。0 で構成が同じ
- 相互情報量（mutual_info_bits）：シリーズ（または区分）が分かると分野の不確かさがどれだけ減るか（ビット）。
  区分はシリーズから決まるため、I(シリーズ;分野) = I(区分;分野) + I(シリーズ;分野|区分) と分けられる。
  scope=all と between_categories の比が「シリーズの違いのうち区分の違いで説明できる割合」
- V は表の大きさ（シリーズ数・分野数）で上限の意味が変わるため、分類の細かさ（class／division）が違う V どうしは比べない
- stable：両方のシリーズが MIN_TITLES 点以上（点数が少ないシリーズの構成比はぶれやすい）
- 期間内の点数が MIN_DISTANCE 未満のシリーズ（終刊直前の数点だけ等）は、距離と最も近いシリーズの計算から除く。
  V・集中度の計算と、シリーズ自体の比較（summary_labels.csv）には含める
"""
import csv
import math
import statistics as st
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
CROSS = (2016, 2025)
MIN_TITLES = 100
MIN_DISTANCE = 20  # 距離・最も近いシリーズの計算に使う最低点数（これ未満は構成比が意味をなさないため、この項目だけ除く）
DECADE_MIN = 30
LEVELS = {"class": lambda r: r["ndc_class"], "division": lambda r: r["ndc"][:2] if len(r["ndc"]) >= 2 else ""}


def publishers():
    return {r["label"]: r["publisher"] for r in csv.DictReader((DATA / "label_candidates.csv").open(encoding="utf-8"))}


def load():
    cats = {r["label"]: r["category"] for r in csv.DictReader((DATA / "summary_labels.csv").open(encoding="utf-8"))}
    rows = [r for r in csv.DictReader((DATA / "titles.csv").open(encoding="utf-8"))
            if r["year"] and CROSS[0] <= int(r["year"]) <= CROSS[1] and r["label"] in cats]
    return cats, rows


def table(rows, unit, level):
    t = defaultdict(Counter)
    for r in rows:
        k = LEVELS[level](r)
        if k:
            t[unit(r)][k] += 1
    return dict(t)


def cramers_v(t):
    keys = sorted({k for c in t.values() for k in c})
    rows = [[c.get(k, 0) for k in keys] for c in t.values()]
    n = sum(map(sum, rows))
    cols = [sum(c) for c in zip(*rows)]
    chi2 = 0.0
    for r in rows:
        rs = sum(r)
        for i, c in enumerate(cols):
            e = rs * c / n
            chi2 += (r[i] - e) ** 2 / e
    k = min(len(rows), len(keys)) - 1
    return (math.sqrt(chi2 / (n * k)) if k > 0 else 0.0), n


def mutual_info(t):
    n = sum(sum(c.values()) for c in t.values())
    col = Counter()
    for c in t.values():
        col.update(c)
    mi = 0.0
    for c in t.values():
        rs = sum(c.values())
        for k, v in c.items():
            if v:
                mi += v / n * math.log2(v * n / (rs * col[k]))
    return mi


def shares(c, keys):
    n = sum(c.values())
    return [c.get(k, 0) / n for k in keys]


def jsd(p, q):
    def kl(a, b):
        return sum(x * math.log2(x / y) for x, y in zip(a, b) if x)
    m = [(x + y) / 2 for x, y in zip(p, q)]
    return math.sqrt(max(0.0, (kl(p, m) + kl(q, m)) / 2))


def scope_stats(t, scope, level):
    keys = sorted({k for c in t.values() for k in c})
    sh = {l: shares(c, keys) for l, c in t.items()}
    v, n = cramers_v(t)
    hhi = [sum(x * x for x in s) for s in sh.values()]
    d = [jsd(sh[a], sh[b]) for a, b in combinations(sorted(sh), 2)]
    return {"scope": scope, "level": level, "units": len(t), "titles": n, "cramers_v": round(v, 3),
            "mutual_info_bits": round(mutual_info(t), 4),
            "hhi_median": round(st.median(hhi), 3), "jsd_median": round(st.median(d), 3) if d else ""}


def run(cats=None, rows=None, pubs=None):
    """cats：シリーズ → 区分、rows：横断比較の期間の点、pubs：シリーズ → 出版社（省略時は data/ から読む）"""
    if cats is None:
        cats, rows = load()
    pubs = pubs if pubs is not None else publishers()
    stats, dist, nearest = [], [], []
    for level in LEVELS:
        t = table(rows, lambda r: r["label"], level)
        stats.append(scope_stats(t, "all", level))
        by_cat = defaultdict(dict)
        for l, c in t.items():
            by_cat[cats[l]][l] = c
        for cat, tc in sorted(by_cat.items()):
            if len(tc) >= 2:
                stats.append(scope_stats(tc, f"category:{cat}", level))
        stats.append(scope_stats(table(rows, lambda r: cats[r["label"]], level), "between_categories", level))
        if level != "class":
            continue
        keys = sorted({k for c in t.values() for k in c})
        n = {l: sum(c.values()) for l, c in t.items()}
        sh = {l: shares(c, keys) for l, c in t.items() if n[l] >= MIN_DISTANCE}
        for a, b in combinations(sorted(sh), 2):
            dist.append({"label_a": a, "label_b": b, "category_a": cats[a], "category_b": cats[b],
                         "same_category": int(cats[a] == cats[b]),
                         "same_publisher": int(bool(pubs.get(a)) and pubs.get(a) == pubs.get(b)), "titles_a": n[a], "titles_b": n[b],
                         "stable": int(min(n[a], n[b]) >= MIN_TITLES), "jsd": round(jsd(sh[a], sh[b]), 3)})
        for l in sorted(sh):
            others = sorted((jsd(sh[l], sh[o]), o) for o in sh if o != l)
            same = [x for x in others if cats[x[1]] == cats[l]]
            nearest.append({"label": l, "category": cats[l], "titles": n[l],
                            "nearest": others[0][1], "nearest_category": cats[others[0][1]],
                            "nearest_jsd": round(others[0][0], 3),
                            "median_jsd_to_others": round(st.median(d for d, _ in others), 3),
                            "nearest_same_category": same[0][1] if same else "",
                            "nearest_same_category_jsd": round(same[0][0], 3) if same else ""})
    dist.sort(key=lambda r: r["jsd"])
    return stats, dist, nearest


def by_decade(rows, cats):
    """rows：全期間の点。10年ごとに、DECADE_MIN 点以上のシリーズで V を出す（全シリーズと一般向け）"""
    out = []
    dec = defaultdict(list)
    for r in rows:
        if r["year"] and r["label"] in cats:
            dec[int(r["year"]) // 10 * 10].append(r)
    for d, rs in sorted(dec.items()):
        t = table(rs, lambda r: r["label"], "class")
        for scope, keep in (("all", lambda l: True), ("category:general", lambda l: cats[l] == "general")):
            tt = {l: c for l, c in t.items() if keep(l) and sum(c.values()) >= DECADE_MIN}
            if len(tt) >= 2:
                v, n = cramers_v(tt)
                out.append({"decade": d, "scope": scope, "labels": len(tt), "titles": n, "cramers_v": round(v, 3)})
    return out


def write(name, rows):
    with (DATA / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    stats, dist, nearest = run()
    write("ndc_stats.csv", stats)
    write("ndc_distance.csv", dist)
    write("ndc_nearest.csv", nearest)
    # 時代の比較は2016年より前に終刊したシリーズも含めるため、区分は titles.csv から取る
    allrows = list(csv.DictReader((DATA / "titles.csv").open(encoding="utf-8")))
    write("ndc_v_by_decade.csv", by_decade(allrows, {r["label"]: r["category"] for r in allrows}))
    for s in stats:
        print(s)


if __name__ == "__main__":
    main()
