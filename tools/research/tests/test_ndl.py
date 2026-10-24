"""国立国会図書館サーチの検索の分割のテスト（API には接続せず、応答を作って返す）"""
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.research import ndl  # noqa: E402


def fake_index(per_day):
    """per_day：{date: 件数}。from・until（年月日）の範囲の書誌を返す偽の fetch"""
    def fetch(params, offline=False):
        fr = date.fromisoformat(params["from"])
        un = date.fromisoformat(params["until"])
        items = [(d, i) for d, n in per_day.items() if fr <= d <= un for i in range(n)]
        cnt = int(params.get("cnt", 200))
        rss = ET.Element("rss")
        ch = ET.SubElement(rss, "channel")
        ET.SubElement(ch, "{http://a9.com/-/spec/opensearchrss/1.0/}totalResults").text = str(len(items))
        for d, i in items[:min(cnt, ndl.LIMIT)]:
            it = ET.SubElement(ch, "item")
            ET.SubElement(it, "link").text = f"{d}-{i}"
        return rss
    return fetch


def test_requires_full_dates(monkeypatch):
    calls = []
    f = fake_index({date(2005, 3, 1): 5})

    def spy(params, offline=False):
        calls.append(params)
        return f(params, offline)

    monkeypatch.setattr(ndl, "fetch", spy)
    items, _ = ndl.search_by_date({"title": "x"}, 2005, 2005)
    assert len(items) == 5
    assert all(len(c["from"]) == 10 and len(c["until"]) == 10 for c in calls)  # YYYY-MM-DD
    assert calls[0]["until"] == "2005-12-31"


def test_splits_when_over_limit(monkeypatch):
    # 10年で1,100件（各年110件）。10年の検索は500件を超えるため、年に分けて全件を取る
    per_day = {date(y, 6, 1): 110 for y in range(2010, 2020)}
    monkeypatch.setattr(ndl, "fetch", fake_index(per_day))
    items, log = ndl.search_by_date({"title": "x"}, 2010, 2019)
    assert len(items) == 1100
    assert len(log) == 10


def test_splits_year_into_months(monkeypatch):
    # 1年で600件（2か月に300件ずつ）。年の検索は上限を超えるため月に分け、取りこぼしは0
    per_day = {date(2020, 1, 15): 300, date(2020, 7, 15): 300}
    monkeypatch.setattr(ndl, "fetch", fake_index(per_day))
    items, log = ndl.search_by_date({"title": "x"}, 2020, 2020)
    assert len(items) == 600
    assert log[-1]["shortfall"] == 0
