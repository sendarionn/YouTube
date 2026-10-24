"""ネット上のイメージの分類：収集した記述（data/image_claims.tsv）を共通のカテゴリに分ける

- 1つの記述が複数のカテゴリに入ることがある（キーワードの規則による。規則は CATEGORIES）
- 数えるのは「そのカテゴリの記述がある情報源の数」。同じ情報源の同じレーベルについての複数の記述は1と数える
- basis が impression・citation の記述だけを数える（出典のない事実の記述は、事実の確認に回す）
出力：data/image_coded.tsv（記述ごとのカテゴリ）、data/image_summary.csv（レーベル×カテゴリの情報源数）
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# カテゴリ：(名前, 検証に使える代理指標, キーワードの正規表現)
CATEGORIES = [
    ("学術的・専門的", "研究者の著者比率、注・参考文献の掲載率", r"学術|専門的|格調|教養的|ガチガチ|本格|学術系|知の殿堂|原理的|抽象的|学問"),
    ("歴史に強い", "NDC 2類（歴史・地理）の比率", r"歴史"),
    ("分野が幅広い", "NDC の分野の分散（集中度）", r"幅広|幅が広|多様|色んな|バラエティ|網羅|節操がない"),
    ("読みやすい・入門的", "ページ数、紙面（標本）", r"読みやす|やさし|わかりやす|分かりやす|とっつきやす|手軽|初心者|最初の新書|サクサク|かみくだ|噛み砕"),
    ("大衆向け・時事的", "著者属性、タイトルの傾向", r"大衆|ポピュリズム|雑誌|時事|話題作|キャッチー|読み捨て|ベストセラー"),
    ("実用・ビジネス", "NDC 3類のうち経営・経済、タイトルの傾向", r"実用|実学|ビジネス|自己啓発|説教|仕事"),
    ("政治的にリベラル", "（単一の指標では測れない）", r"リベラル|左翼|左寄り|左派"),
    ("政治的に保守", "（単一の指標では測れない）", r"保守|憂国|右寄り"),
    ("政治・社会問題の本が多い", "NDC 3類（社会科学）の比率", r"政治|社会問題|政治家"),
    ("読みにくい・上級者向け", "ページ数、紙面（標本）", r"向いていない|おすすめしにく|とっつきにく|取っつきにく|上級|>>|硬派|ガチ"),
    ("薄い（ページ数が少ない）", "ページ数", r"薄い|ページ数が少ない"),
    ("中高年・特定の読者向け", "（書誌からは分からない）", r"中高年|おじさん|ビジネスマン|30代|サラリーマン|10代|中学"),
    ("デザイン・装丁", "表紙・背表紙（実物・書影）", r"デザイン|装丁|装幀|表紙|カバー|色|背表紙"),
]


def main():
    rows = list(csv.DictReader((DATA / "image_claims.tsv").open(encoding="utf-8"), delimiter="\t"))
    coded = []
    for r in rows:
        cats = [name for name, _, pat in CATEGORIES if re.search(pat, r["quote"])]
        # 否定の記述（「初心者には向いていない」など）は「読みやすい」に数えない
        if "読みにくい・上級者向け" in cats and "読みやすい・入門的" in cats:
            cats.remove("読みやすい・入門的")
        coded.append({**r, "categories": "|".join(cats)})
    with (DATA / "image_coded.tsv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(coded[0]), delimiter="\t")
        w.writeheader()
        w.writerows(coded)
    counts = defaultdict(set)
    for r in coded:
        if not r["basis"].startswith(("impression", "citation")):
            continue
        for c in filter(None, r["categories"].split("|")):
            counts[(r["label"], c)].add(r["source_id"])
    with (DATA / "image_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "category", "sources", "source_ids", "proxy_indicator"])
        proxy = {name: p for name, p, _ in CATEGORIES}
        for (label, c), s in sorted(counts.items(), key=lambda x: (x[0][0], -len(x[1]))):
            w.writerow([label, c, len(s), " ".join(sorted(s)), proxy[c]])
    n_src = len({r["source_id"] for r in coded})
    print(f"記述 {len(coded)} 件、情報源 {n_src}")
    uncoded = [r for r in coded if not r["categories"] and r["basis"].startswith("impression")]
    print(f"どのカテゴリにも入らない印象の記述 {len(uncoded)} 件")
    for r in uncoded[:15]:
        print("  ", r["label"], r["quote"][:50])


if __name__ == "__main__":
    sys.exit(main())
