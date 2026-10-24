"""候補の確認：Wikipedia「新書レーベル一覧」の全シリーズ名を、国立国会図書館サーチの書誌で確かめる

入力：data/wikipedia_labels.csv（版 101785742、2024-09-09。見出し・出版社・シリーズ名を手で整形せずに分けたもの）
出力：data/wikipedia_survey.csv
- hits：題名検索（title=シリーズ名）の件数（題名に一致する本も含む）
- sample_series_match：最初の50件のうち、書誌のシリーズ名がその名前で始まる件数
- year_min / year_max：一致した書誌の出版年の範囲（50件の中で）
- 件数は書誌レコード数で、刊行点数ではない。採否の目安にだけ使う
"""
import csv
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from tools.research import ndl  # noqa: E402

DATA = HERE.parent / "data"


def key(s):
    return re.sub(r"[\s・･]", "", unicodedata.normalize("NFKC", s)).lower()


def year(r):
    for v in r["issued"] + r["date"]:
        m = re.match(r"(\d{4})", v)
        if m:
            return int(m.group(1))
    return None


def main():
    offline = "--offline" in sys.argv
    rows = list(csv.DictReader((DATA / "wikipedia_labels.csv").open(encoding="utf-8")))
    out, done = [], {}
    for w in rows:
        name = w["series"]
        if name not in done:
            root = ndl.fetch({"dpid": "iss-ndl-opac", "title": name, "cnt": "50"}, offline=offline)
            items = [ndl.parse_item(it) for it in root.iter("item")]
            match = [r for r in items if any(key(s).startswith(key(name)) for s in r["series"])]
            years = sorted(y for y in map(year, match) if y)
            done[name] = {"hits": ndl.total(root), "sample": len(items), "sample_series_match": len(match),
                          "year_min": years[0] if years else "", "year_max": years[-1] if years else ""}
            print(name, done[name], flush=True)
        out.append({**w, **done[name]})
    with (DATA / "wikipedia_survey.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, list(out[0]))
        wr.writeheader()
        wr.writerows(out)


if __name__ == "__main__":
    main()
