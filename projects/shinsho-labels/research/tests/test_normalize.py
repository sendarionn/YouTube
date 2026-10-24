"""刊行点数へのまとめ方の回帰テスト（再調査で見つかった誤り）"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import normalize  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"


def rec(title, series, cat, year="1943"):
    return {"title": [title], "series": [series], "category": cat, "issued": [year], "date": [], "creator": ["山田, 太郎"],
            "author": "山田太郎 著", "edition": [], "price": [], "extent": [], "subjects": {}, "ids": {}}


def test_microfilm_only_title_is_kept():
    # 戦中の本でマイクロ資料しかない書誌は、複製ではなく唯一の記録として残す
    recs = [rec("伊能忠敬の測量日記", "ラジオ新書 ; 59", ["図書", "マイクロ"]),
            rec("健康の医学", "ラジオ新書 ; 60", ["図書", "紙"]),
            rec("健康の医学", "ラジオ新書 ; 60", ["図書", "マイクロ"])]
    rows = normalize.normalize("ラジオ新書", "general", recs, Counter())
    assert sorted(r["series_no"] for r in rows) == ["59", "60"]


def pattern(label):
    c = next(c for c in csv.DictReader((DATA / "label_candidates.csv").open(encoding="utf-8")) if c["label"] == label)
    return re.compile(c["series_pattern"])


def test_seishun_series_split_by_number_prefix():
    intel, play, old = (pattern(l) for l in ("青春新書インテリジェンス", "青春新書PLAY BOOKS", "青春新書（旧）"))
    assert intel.search("青春新書 ; PI- 222") and not old.search("青春新書 ; PI- 222")
    assert play.search("青春新書 ; P- 1211") and not old.search("青春新書 ; P- 1211")
    assert old.search("青春新書") and not intel.search("青春新書")
    assert intel.search("青春新書INTELLIGENCE ; PI-500") and not play.search("青春新書INTELLIGENCE ; PI-500")


def test_kyoikusha_excludes_yosensha():
    c = next(c for c in csv.DictReader((DATA / "label_candidates.csv").open(encoding="utf-8")) if c["label"] == "教育社歴史新書")
    assert c["publisher_pattern"] == "教育社"
    assert not re.search(c["series_pattern"], "歴史新書y ; 012")


def test_isbn10_matches_isbn13():
    import bestseller_labels
    assert bestseller_labels.digits("4-12-101655-6") == bestseller_labels.digits("978-4-12-101655-3")
