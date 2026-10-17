"""題名に語を含む国立国会図書館所蔵資料の年別件数

条件
- dpid=iss-ndl-opac（国立国会図書館の所蔵資料のみ。他館の重複を除く）
- 題名に語を含む（NDLサーチの題名検索の結果から、中黒と空白を除いた題名に語を含むものだけを残す。「ビジネス・マナー」も数える）
- 出版年が4桁の西暦で始まる資料だけを数える（「[199-]」など年が確定しないものは除く）
- 版や刷の違いで別書誌になったものは別に数える。雑誌・映像資料・新聞記事索引も含まれうる

APIの負荷を抑えるため5年単位で検索し、各資料の出版年で年別に振り分ける
出力：data/ndl_title_counts.csv（term, year, count）
"""
import csv
import re
import sys
from collections import Counter

from ndl import fetch, items
from paths import DATA

TERMS = ["ビジネスマナー", "マナー", "接遇", "作法", "敬語"]
START, END, STEP = 1950, 2025, 5


def normalize(title):
    return re.sub(r"[・･\s　]", "", title)


def count_range(term, y0, y1):
    links = {}
    idx = 1
    while True:
        root = fetch({"title": term, "dpid": "iss-ndl-opac", "from": f"{y0}-01", "until": f"{y1}-12", "cnt": "500", "idx": str(idx)})
        batch = list(items(root))
        for r in batch:
            issued = (r.get("issued") or [""])[0]
            m = re.match(r"^(\d{4})(\D|$)", issued)
            if m and y0 <= int(m.group(1)) <= y1 and term in normalize((r.get("title") or [""])[0]):
                links[r["link"][0]] = int(m.group(1))
        if len(batch) < 500:
            return Counter(links.values())
        idx += 500


if __name__ == "__main__":
    terms = sys.argv[1:] or TERMS
    out = DATA / "ndl_title_counts.csv"
    rows = []
    if out.exists():
        rows = [r for r in csv.DictReader(out.open()) if r["term"] not in terms]
    for t in terms:
        for y0 in range(START, END + 1, STEP):
            y1 = min(y0 + STEP - 1, END)
            c = count_range(t, y0, y1)
            for y in range(y0, y1 + 1):
                rows.append({"term": t, "year": y, "count": c.get(y, 0)})
            print(t, y0, y1, dict(sorted(c.items())), flush=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, ["term", "year", "count"])
        w.writeheader()
        w.writerows(rows)
