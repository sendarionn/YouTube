"""集計：data/titles.csv（normalize.py の出力）からレーベルごとの指標を作る

出力：data/summary_labels.csv（横断比較 2016〜2025年）、data/yearly_counts.csv、data/ndc_by_label.csv、
      data/ndc_by_decade.csv、data/coverage.csv、data/price_trend.csv、data/title_features.csv
定義
- 刊行点数：normalize.py でまとめた点数（書誌レコード数ではない）
- 横断比較：刊行年が 2016〜2025年の点。この期間の点数が MIN_TITLES 未満のレーベルは比較から外す（別に記載）
- 分野：NDC の第1次区分（0〜9）。区分のない点は分母から除き、欠損率を記録する
- 集中度：分野の構成比の二乗和（ハーフィンダール指数。1 に近いほど特定の分野に集中）
- 価格：表示価格（税の記載なし）は本体価格とみなす。「税込」の価格は刊行年の消費税率で割って本体価格に直し、
  直した点数を記録する（税率：1989年4月〜3%、1997年4月〜5%、2014年4月〜8%、2019年10月〜10%）
- 実質価格：消費者物価指数（総合、2020年=100、e-Stat）で 2020年の円に直す
- ページ当たり価格：本体価格 ÷ 本文のページ数
- 翻訳：責任表示に「訳」を含む
"""
import csv
import math
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
CROSS = (2016, 2025)
MIN_TITLES = 100

NDC_NAMES = {"0": "総記", "1": "哲学・宗教", "2": "歴史・地理", "3": "社会科学", "4": "自然科学", "5": "技術・工学",
             "6": "産業", "7": "芸術・スポーツ", "8": "言語", "9": "文学"}


def tax_rate(y, m):
    ym = y * 100 + (m or 6)
    if ym >= 201910:
        return 0.10
    if ym >= 201404:
        return 0.08
    if ym >= 199704:
        return 0.05
    if ym >= 198904:
        return 0.03
    return 0.0


def base_price(r):
    """(本体価格, 直したか)"""
    if not r["price_yen"]:
        return None, False
    p, y, m = int(r["price_yen"]), int(r["year"]), int(r["month"]) if r["month"] else None
    if r["price_basis"] == "税込":
        return p / (1 + tax_rate(y, m)), True
    return float(p), False


def cpi():
    return {int(r["year"]): float(r["総合"]) for r in csv.DictReader((DATA / "cpi_annual.csv").open(encoding="utf-8"))
            if r["総合"]}


def write(name, rows):
    if not rows:
        return
    with (DATA / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def title_features(t):
    return {
        "length": len(t),
        "question": bool(re.search(r"[?？]|なぜ|どうして|のか$|とは何か|とは$", t)),
        "number": bool(re.search(r"[0-9０-９]|[一二三四五六七八九十百千万]つの|[0-9]+の", t)),
        "emphasis": bool(re.search(r"[!！]|絶対|最強|すごい|ヤバ|9割|本当は|知らない|間違い", t)),
    }


def main():
    rows = [r for r in csv.DictReader((DATA / "titles.csv").open(encoding="utf-8")) if r["year"]]
    for r in rows:
        r["year"] = int(r["year"])
    idx = cpi()
    labels = sorted({r["label"] for r in rows})

    # 刊行実績
    yearly = Counter((r["label"], r["year"]) for r in rows)
    write("yearly_counts.csv", [{"label": l, "year": y, "titles": n} for (l, y), n in sorted(yearly.items())])

    # 網羅率：番号が通しで振られるシリーズは、最大の番号を期待される点数とみなす（目安）
    cov = []
    for l in labels:
        for era in sorted({r["era"] for r in rows if r["label"] == l}):
            rs = [r for r in rows if r["label"] == l and r["era"] == era]
            nums = [int(r["series_no"]) for r in rs if r["series_no"].isdigit()]
            cov.append({"label": l, "era": era, "titles": len(rs), "numbered": len(nums),
                        "max_number": max(nums) if nums else "",
                        "titles_per_max_number": round(len(rs) / max(nums), 3) if nums else "",
                        "first_year": min(r["year"] for r in rs), "last_year": max(r["year"] for r in rs)})
    write("coverage.csv", cov)

    # 横断比較
    cross = [r for r in rows if CROSS[0] <= r["year"] <= CROSS[1]]
    summary, ndc_rows = [], []
    for l in labels:
        rs = [r for r in cross if r["label"] == l]
        if not rs:
            continue
        cat = rs[0]["category"]
        nd = Counter(r["ndc_class"] for r in rs if r["ndc_class"])
        n_nd = sum(nd.values())
        shares = {c: nd.get(c, 0) / n_nd for c in NDC_NAMES} if n_nd else {}
        hhi = sum(s * s for s in shares.values()) if shares else None
        prices, converted = [], 0
        ppp, real = [], []
        for r in rs:
            p, conv = base_price(r)
            if p is None:
                continue
            prices.append(p)
            converted += conv
            if r["pages"]:
                ppp.append(p / int(r["pages"]))
            if r["year"] in idx:
                real.append(p * 100 / idx[r["year"]])
        pages = [int(r["pages"]) for r in rs if r["pages"]]
        feats = [title_features(r["title"]) for r in rs]
        summary.append({
            "label": l, "category": cat, "titles": len(rs), "compared": int(len(rs) >= MIN_TITLES),
            "ndc_known_share": round(n_nd / len(rs), 3), "ndc_hhi": round(hhi, 3) if hhi is not None else "",
            "top_ndc": max(shares, key=shares.get) if shares else "",
            "top_ndc_share": round(max(shares.values()), 3) if shares else "",
            "history_share": round(shares.get("2", 0), 3) if shares else "",
            "social_share": round(shares.get("3", 0), 3) if shares else "",
            "science_share": round(shares.get("4", 0), 3) if shares else "",
            "price_known_share": round(len(prices) / len(rs), 3),
            "price_median": round(st.median(prices)) if prices else "",
            "price_converted_from_taxincl": converted,
            "pages_known_share": round(len(pages) / len(rs), 3),
            "pages_median": st.median(pages) if pages else "",
            "price_per_page_median": round(st.median(ppp), 2) if ppp else "",
            "translated_share": round(sum(int(r["translated"]) for r in rs) / len(rs), 3),
            "title_length_median": st.median(f["length"] for f in feats),
            "title_question_share": round(sum(f["question"] for f in feats) / len(feats), 3),
            "title_number_share": round(sum(f["number"] for f in feats) / len(feats), 3),
            "title_emphasis_share": round(sum(f["emphasis"] for f in feats) / len(feats), 3),
        })
        for c in NDC_NAMES:
            ndc_rows.append({"label": l, "ndc_class": c, "ndc_name": NDC_NAMES[c], "titles": nd.get(c, 0),
                             "share": round(shares.get(c, 0), 4) if shares else ""})
    write("summary_labels.csv", summary)
    write("ndc_by_label.csv", ndc_rows)

    # 分野の時代変化（10年ごと）
    dec = defaultdict(Counter)
    for r in rows:
        if r["ndc_class"]:
            dec[(r["label"], r["year"] // 10 * 10)][r["ndc_class"]] += 1
    write("ndc_by_decade.csv", [{"label": l, "decade": d, "titles": sum(c.values()),
                                 **{f"share_{k}": round(c.get(k, 0) / sum(c.values()), 3) for k in NDC_NAMES}}
                                for (l, d), c in sorted(dec.items())])

    # 価格とページ数の推移（5年ごと、名目と実質）
    pt = []
    for l in labels:
        groups = defaultdict(list)
        for r in rows:
            if r["label"] != l:
                continue
            p, _ = base_price(r)
            if p is None:
                continue
            groups[r["year"] // 5 * 5].append((p, r))
        for y0, ps in sorted(groups.items()):
            real = [p * 100 / idx[r["year"]] for p, r in ps if r["year"] in idx]
            pg = [int(r["pages"]) for _, r in ps if r["pages"]]
            pt.append({"label": l, "period": f"{y0}-{y0 + 4}", "titles_with_price": len(ps),
                       "price_median_nominal": round(st.median(p for p, _ in ps)),
                       "price_median_real_2020yen": round(st.median(real)) if real else "",
                       "pages_median": st.median(pg) if pg else ""})
    write("price_trend.csv", pt)
    print(f"点数 {len(rows)}、横断比較 {len(cross)} 点、レーベル {len(labels)}")


if __name__ == "__main__":
    main()
