"""分析対象の範囲の回帰テスト：区分（一般向けなど）や点数で、全シリーズの比較から機械的に除かないこと"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import author_shares  # noqa: E402
import discover_labels  # noqa: E402
import stats  # noqa: E402


def title(label, ndc, year="2020", creator="", birth=""):
    return {"label": label, "ndc_class": ndc[0], "ndc": ndc, "year": year, "category": "",
            "first_creator": creator, "first_creator_birth": birth}


def sample():
    cats = {"一般A": "general", "一般B": "general", "科学C": "science", "小D": "specialized"}  # 小D だけ20点未満
    rows = ([title("一般A", "361")] * 12 + [title("一般A", "210")] * 8 + [title("一般B", "361")] * 10 +
            [title("一般B", "210")] * 10 + [title("科学C", "420")] * 18 + [title("科学C", "361")] * 2 +
            [title("小D", "686")] * 3)
    return cats, rows


def test_all_scope_includes_every_category_and_small_labels(monkeypatch):
    monkeypatch.setattr(stats, "MIN_DISTANCE", 1)
    cats, rows = sample()
    st, dist, nearest = stats.run(cats, rows, {})
    all_class = next(s for s in st if s["scope"] == "all" and s["level"] == "class")
    assert all_class["units"] == 4          # 科学・小規模のシリーズも含む
    assert {n["label"] for n in nearest} == set(cats)


def test_category_scope_is_separate_and_wider_differences_in_all():
    cats, rows = sample()
    st, _, _ = stats.run(cats, rows, {})
    v = {s["scope"]: s["cramers_v"] for s in st if s["level"] == "class"}
    assert "category:general" in v and "between_categories" in v
    assert v["all"] > v["category:general"]  # 専門のシリーズを含めると差が大きくなる


def test_distance_marks_unstable_pairs(monkeypatch):
    monkeypatch.setattr(stats, "MIN_DISTANCE", 1)
    cats, rows = sample()
    _, dist, _ = stats.run(cats, rows, {})
    assert all(d["stable"] == 0 for d in dist)   # どれも100点未満
    assert any(d["same_category"] == 0 for d in dist)


def test_author_shares_keeps_small_labels():
    titles = [{"label": "小D", "category": "specialized", "year": "2020", "first_creator": "山田太郎",
               "first_creator_birth": ""}] * 3
    out = author_shares.compute({}, titles)
    assert out[0]["label"] == "小D" and out[0]["stable"] == 0 and out[0]["matched"] == 0


def test_discover_base_name():
    assert discover_labels.base("岩波新書 新赤版 ; 1706") == "岩波新書"
    assert discover_labels.base("ヤマケイ新書 ; YS026") == "ヤマケイ新書"
    assert discover_labels.base("交通新聞社新書 ; 107") == "交通新聞社新書"


def test_tiny_labels_kept_in_v_but_not_in_distance():
    cats, rows = sample()   # 小D は3点（MIN_DISTANCE 未満）
    st, dist, nearest = stats.run(cats, rows, {})
    assert next(s for s in st if s["scope"] == "all" and s["level"] == "class")["units"] == 4
    assert "小D" not in {n["label"] for n in nearest}
    assert all("小D" not in (d["label_a"], d["label_b"]) for d in dist)
