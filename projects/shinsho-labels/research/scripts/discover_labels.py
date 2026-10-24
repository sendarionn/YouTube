"""候補の発見：国立国会図書館サーチで「新書」を含む書誌を年ごとに集め、シリーズ名ごとの件数を数える

候補一覧（label_candidates.csv）の漏れを、書誌そのものから確かめるために使う
- 検索：title=新書（題名とシリーズ名に一致する）。年ごとに検索し、500件を超える年は月・日に分ける
- 年：2016〜2025年は毎年（横断比較の期間）、1950〜2010年は10年ごと（歴史的なシリーズの発見用の標本。終刊したシリーズは Wikipedia の一覧の全件確認で補う）
- シリーズ名は「 ; 」の前（番号を除く）と、岩波新書の版（赤版・新赤版など）を除いた名前で数える
- 名前に「新書」を含まないシリーズ（ブルーバックスなど）はここでは見つからない。Wikipedia の一覧などで補う
- 出力：data/series_discovery.csv（シリーズ名、件数、出版者、既存の候補に一致するか）
"""
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from tools.research import ndl  # noqa: E402

DATA = HERE.parent / "data"
YEARS_CROSS = list(range(2016, 2026))
YEARS_SAMPLE = list(range(1950, 2016, 10))


def base(series):
    s = series.split(";")[0].strip()
    s = re.sub(r"\s*(赤版|青版|黄版|新赤版)$", "", s)
    s = re.sub(r"\s*[0-9０-９]+$", "", s)
    return s


def main():
    offline = "--offline" in sys.argv
    cands = list(csv.DictReader((DATA / "label_candidates.csv").open(encoding="utf-8")))
    pats = [(c["label"], re.compile(c["series_pattern"])) for c in cands]
    count = defaultdict(Counter)   # 名前 → {"cross": n, "sample": n}
    years = defaultdict(set)
    pubs = defaultdict(Counter)
    errors = []
    for y in YEARS_CROSS + YEARS_SAMPLE:
        try:
            items, _ = ndl.search_by_date({"dpid": "iss-ndl-opac", "title": "新書"}, y, y, offline=offline)
        except ndl.TooMany as e:
            errors.append(str(e))
            continue
        seen = set()
        for r in items:
            bid = (r["ids"].get("NDLBibID") or [r["link"]])[0]
            if bid in seen:
                continue
            seen.add(bid)
            for s in r["series"]:
                if "新書" not in s:
                    continue
                name = base(s)
                count[name]["cross" if y in YEARS_CROSS else "sample"] += 1
                years[name].add(y)
                for p in r["publisher"][:1]:
                    pubs[name][p] += 1
        print(y, len(seen), flush=True)
    rows = []
    for name, c in count.items():
        hit = [l for l, p in pats if p.search(name)]
        rows.append({"series": name, "records_2016_2025": c["cross"], "records_sample_1950_2010": c["sample"],
                     "years_seen": f"{min(years[name])}-{max(years[name])}",
                     "publisher": pubs[name].most_common(1)[0][0] if pubs[name] else "",
                     "matched_candidate": " ".join(hit)})
    rows.sort(key=lambda r: -(r["records_2016_2025"] + r["records_sample_1950_2010"]))
    with (DATA / "series_discovery.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"シリーズ名 {len(rows)}、既存の候補に一致しないもの {sum(not r['matched_candidate'] for r in rows)}")
    for e in errors:
        print("取得できなかった：", e)


if __name__ == "__main__":
    main()
