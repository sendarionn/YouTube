"""題名に「マナー」を含む資料のうち、航空会社・客室乗務員を題名か著者に含むものを数える

count_titles.py と同じ検索結果（キャッシュ）を使う
判定は題名・著者・出版者の文字列に次の語を含むかどうかだけで行う
著者の経歴（元CAかどうか）は書誌から分からないため数えていない

出力：data/ndl_airline_manner_titles.csv（year, title, creator, publisher, link, matched）
      標準出力に5年ごとの件数
"""
import csv
import re

from count_titles import END, START, STEP, normalize
from ndl import fetch, items
from paths import DATA

KEYWORDS = ["スチュワーデス", "客室乗務員", "CA", "キャビンアテンダント", "JAL", "ANA", "日本航空", "全日空", "全日本空輸", "エアライン", "航空"]
TERM = "マナー"


def main():
    rows = []
    totals = {}
    for y0 in range(START, END + 1, STEP):
        y1 = min(y0 + STEP - 1, END)
        idx, seen = 1, {}
        while True:
            root = fetch({"title": TERM, "dpid": "iss-ndl-opac", "from": f"{y0}-01", "until": f"{y1}-12", "cnt": "500", "idx": str(idx)})
            batch = list(items(root))
            for r in batch:
                issued = (r.get("issued") or [""])[0]
                m = re.match(r"^(\d{4})(\D|$)", issued)
                title = (r.get("title") or [""])[0]
                if m and y0 <= int(m.group(1)) <= y1 and TERM in normalize(title):
                    seen[r["link"][0]] = (int(m.group(1)), r)
            if len(batch) < 500:
                break
            idx += 500
        hit = 0
        for link, (year, r) in seen.items():
            text = " ".join(r.get("title", []) + r.get("creator", []) + r.get("publisher", []))
            matched = [k for k in KEYWORDS if (re.search(r"(?<![A-Za-z])CA(?![A-Za-z])", text) if k == "CA" else k in text)]
            if matched:
                hit += 1
                rows.append({"year": year, "title": r["title"][0], "creator": "; ".join(r.get("creator", [])),
                             "publisher": "; ".join(r.get("publisher", [])), "link": link, "matched": "|".join(matched)})
        totals[(y0, y1)] = (len(seen), hit)
        print(y0, y1, "マナー", len(seen), "航空関連", hit)
    rows.sort(key=lambda x: (x["year"], x["title"]))
    with (DATA / "ndl_airline_manner_titles.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, ["year", "title", "creator", "publisher", "link", "matched"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
