"""著者属性の集計：横断比較（2016〜2025年）の点ごとに、最初の著者の区分（authors.py）を数える

出力：data/author_shares.csv
- matched_share：最初の著者を Wikidata で照合できた点の割合（照合できない点は区分が分からない）
- researcher_share_matched：照合できた点のうち「研究者・大学教員」の割合
- stable：100点以上（割合がぶれにくい）。少ないシリーズも除かずに出す
- researcher_lower / upper：照合できなかった点がすべて研究者でない場合 / すべて研究者の場合の、全点に対する割合
"""
import csv
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
CLASSES = ["研究者・大学教員", "ジャーナリスト", "実務家・経営者", "作家・評論家", "その他"]


def compute(au, titles):
    """au：(名前, 生年) → authors.csv の行、titles：titles.csv の行。シリーズごとの割合の行を返す"""
    stat = defaultdict(Counter)
    for t in titles:
        if not t["year"] or not 2016 <= int(t["year"]) <= 2025 or not t["first_creator"]:
            continue
        a = au.get((t["first_creator"], t["first_creator_birth"]))
        s = stat[(t["label"], t["category"])]
        s["titles"] += 1
        if a and a["status"] == "照合" and a["class"]:
            s["matched"] += 1
            s[a["class"]] += 1
    out = []
    for (label, cat), s in sorted(stat.items(), key=lambda x: -x[1]["titles"]):
        n, m = s["titles"], s["matched"]
        # 点数の少ないシリーズも除かず、stable（100点以上）で区別する
        row = {"label": label, "category": cat, "titles": n, "stable": int(n >= 100), "matched": m,
               "matched_share": round(m / n, 3)}
        for c in CLASSES:
            row[f"{c}_share_matched"] = round(s[c] / m, 3) if m else ""
        row["researcher_lower"] = round(s["研究者・大学教員"] / n, 3)
        row["researcher_upper"] = round((s["研究者・大学教員"] + n - m) / n, 3)
        out.append(row)
    return out


def main():
    au = {(a["name"], a["birth"]): a for a in csv.DictReader((DATA / "authors.csv").open(encoding="utf-8"))}
    out = compute(au, csv.DictReader((DATA / "titles.csv").open(encoding="utf-8")))
    with (DATA / "author_shares.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(out[0]))
        w.writeheader()
        w.writerows(out)

    def pct(x):
        return f"{x * 100:>4.0f}%" if x != "" else "    -"
    for r in sorted(out, key=lambda r: -(r["研究者・大学教員_share_matched"] or 0)):
        print(f'{r["label"]:<16}{r["titles"]:>5} 照合{pct(r["matched_share"])} 研究者{pct(r["研究者・大学教員_share_matched"])} '
              f'記者{pct(r["ジャーナリスト_share_matched"])} 実務{pct(r["実務家・経営者_share_matched"])} '
              f'全体での研究者 {r["researcher_lower"]*100:.0f}〜{r["researcher_upper"]*100:.0f}%')


if __name__ == "__main__":
    main()
