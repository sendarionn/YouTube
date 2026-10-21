"""航空関連のマナー本の判定と、文書の件数・割合が集計ファイルと一致することの確認（progress.md「訂正の記録」）"""
import csv
import re
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

import airline_titles  # noqa: E402
from count_titles import normalize  # noqa: E402
from paths import CACHE  # noqa: E402


def rows(name):
    with open(PROJECT / "data" / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_ca_is_matched_as_a_word():
    assert airline_titles.matched_keywords("CAのマナー") == ["CA"]
    assert airline_titles.matched_keywords("元CA 山田") == ["CA"]
    # 2026-10-21 に見つかった誤検出
    assert airline_titles.matched_keywords("LIFE CAREER : 人生100年時代の私らしい働き方 渡部, 昌平 金子書房") == []
    assert airline_titles.matched_keywords("青春グラフィティ PONY CANYON") == []
    assert "JAL" in airline_titles.matched_keywords("JALスチュワーデスのいきいきマナー講座")


def test_csv_rows_satisfy_the_conditions():
    for r in rows("ndl_airline_manner_titles.csv"):
        assert "マナー" in normalize(r["title"])
        assert airline_titles.matched_keywords(" ".join([r["title"], r["creator"], r["publisher"]]))
        assert 1950 <= int(r["year"]) <= 2025


def test_documents_match_the_counts():
    n = len(rows("ndl_airline_manner_titles.csv"))
    total = sum(int(r["count"]) for r in rows("ndl_title_counts.csv") if r["term"] == "マナー")
    expected = f"{total:,}点（1950〜2025年）のうち、航空会社・CAを題名・著者・出版者に掲げたものは{n}点（{100 * n / total:.1f}%）"
    for doc in ("hypotheses.md", "history.md"):
        text = (PROJECT / doc).read_text(encoding="utf-8")
        assert expected in text, doc
    first = min(int(r["year"]) for r in rows("ndl_airline_manner_titles.csv"))
    assert f"最初は{first}年" in (PROJECT / "hypotheses.md").read_text(encoding="utf-8")


@pytest.mark.skipif(not (CACHE / "ndl").exists(), reason="取得済みの NDL 応答（Git 管理外）がない")
def test_rerun_from_cache_matches_csv(tmp_path, monkeypatch):
    """取得済みの応答から再集計すると CSV と同じ行になる（API には問い合わせない）"""
    import ndl

    def no_network(*a, **k):
        raise AssertionError("キャッシュにない問い合わせ（API には接続しない）")

    monkeypatch.setattr(ndl.urllib.request, "urlopen", no_network)
    monkeypatch.setattr(airline_titles, "DATA", tmp_path)
    airline_titles.main()
    new = (tmp_path / "ndl_airline_manner_titles.csv").read_text(encoding="utf-8").splitlines()
    old = (PROJECT / "data" / "ndl_airline_manner_titles.csv").read_text(encoding="utf-8").splitlines()
    assert [re.sub(r"\s+$", "", x) for x in new] == [re.sub(r"\s+$", "", x) for x in old]
