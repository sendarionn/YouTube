"""根拠を evidence.csv に追記する

使い方: python add_evidence.py founder_id 属性 値 出典URL 出典種別 確認状態 "根拠となる記述"
- 出典種別: P1（Iの部）, company（会社公式）, interview, news, profile_db, gov, other
- 確認状態: verified（原文で一致を確認）, partial（一部のみ一致）, unverified（原文未確認）, conflict（出典間で矛盾）
同じ founder_id・属性・出典URLの行は上書きする
"""
import csv
import sys
import time

from paths import DATA

FIELDS = ["founder_id", "attribute", "value", "source_url", "source_type", "status", "quote", "accessed"]


def main():
    fid, attr, value, url, stype, status, quote = sys.argv[1:8]
    path = DATA / "evidence.csv"
    rows = list(csv.DictReader(open(path, encoding="utf-8"))) if path.exists() else []
    rows = [r for r in rows if not (r["founder_id"] == fid and r["attribute"] == attr and r["source_url"] == url)]
    rows.append(dict(zip(FIELDS, [fid, attr, value, url, stype, status, quote, time.strftime("%Y-%m-%d")])))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
