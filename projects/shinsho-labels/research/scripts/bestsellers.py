"""トーハン「年間ベストセラー」（2016〜2025年）の新書ノンフィクション部門を表にする

入力：cache/shinsho-labels/bestsellers/*.pdf（https://www.tohan.jp/bestsellers/archives/ の年間ベストセラーの PDF）
出力：cache/shinsho-labels/bestsellers_tohan.csv（year, period, rank, isbn, title_line。ランキングの再配布にあたるため Git 管理外）
- 順位の行（「1 書名」）の後に出る ISBN をその順位に割り当てる。同じ順位に複数の巻がある場合は複数行になる
- 書名は PDF の行の折り返しのまま（照合は ISBN で行う）
- 利用条件：PDF に「『トーハン調べ』と明示」「営利を目的とした第三者への二次利用を固く禁じます」とある。
  ランキングそのものを配布しない（集計結果の引用にとどめ、出典を明記する）
"""
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from tools.infographic.config import CACHE  # noqa: E402

SRC = CACHE / "shinsho-labels" / "bestsellers"
DATA = HERE.parent / "data"
ISBN = re.compile(r"978-\d+-\d+-\d+-[\dX]")
# PDF のレイアウトで順位の数字が表の末尾に出るため、自動では順位を判定できない行（PDF を目視で確認）
# 2022年4位：アンデシュ・ハンセン『スマホ脳』『最強脳』『ストレス脳』（新潮社、3点まとめて1つの順位）
OVERRIDES = {(2022, "978-4-10-610882-2"): 4, (2022, "978-4-10-610930-0"): 4, (2022, "978-4-10-610959-1"): 4}


def parse(path):
    import pymupdf

    text = "".join(p.get_text() for p in pymupdf.open(path))
    m = re.search(r"集計期間[＝=:：]\s*([^）\n]+?(?:～|〜)[^）\n]+?日)", text.replace("\n", ""))
    period = m.group(1) if m else ""
    sec = re.search(r"【新書[・\s　]*ノンフィクション】(.*?)(?:【|トーハン調べ|\Z)", text, re.S)
    rows, rank, last = [], None, 0
    for line in sec.group(1).splitlines():
        line = line.strip()
        r = re.match(r"^(\d{1,2})(?:\s|$)", line)
        if r and not ISBN.search(line[:4]):
            n = int(r.group(1))
            if n < last:  # 10位の後に、レイアウトの都合で別の表の断片が続く場合は終わる
                break
            rank, last = n, n
            title = line[r.end():].strip()
            continue
        for isbn in ISBN.findall(line):
            rows.append({"year": None, "period": period, "rank": rank, "isbn": isbn, "title_line": title})
    return rows, period


def main():
    out = []
    for path in sorted(SRC.glob("*.pdf")):
        rows, period = parse(path)
        year = int(re.search(r"(\d{4})", period.split("～")[-1].split("〜")[-1]).group(1))
        for r in rows:
            r["year"] = year
            if (year, r["isbn"]) in OVERRIDES:
                r["rank"] = OVERRIDES[(year, r["isbn"])]
                r["title_line"] = "（順位はPDFを目視で確認）"
        out += rows
        print(year, period, len(rows), "件", sorted({r["rank"] for r in rows}))
    with (CACHE / "shinsho-labels" / "bestsellers_tohan.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["year", "period", "rank", "isbn", "title_line"])
        w.writeheader()
        w.writerows(out)


if __name__ == "__main__":
    main()
