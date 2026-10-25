"""中心の計算の検証（python -m pytest projects/japan-center/research/tests）"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import geo  # noqa: E402
from weighted_centers import leaf_units  # noqa: E402

SRC = geo.CACHE / "src" / "topics135_10.xlsx"


def test_stat_bureau_formula_on_symmetric_points():
    x, y = geo.stat_bureau_mean([136, 138], [35, 35], [1, 1])
    assert x == pytest.approx(137) and y == pytest.approx(35)


def test_spherical_mean_differs_from_simple_average_in_latitude():
    # 経度が大きく離れた2点の球面上の中点は、緯度の単純平均より極側にずれる
    _, lat = geo.spherical_mean([120, 150], [40, 40])
    assert lat > 40


def test_geometric_median_of_three_points_is_inside():
    lon, lat = geo.geometric_median([136, 138, 137], [35, 35, 36], [1, 1, 1])
    assert 136 < lon < 138 and 35 < lat < 36


def test_leaf_units_drop_designated_city_totals():
    assert leaf_units(["01100", "01101", "01202", "14130", "14131", "13000"]) == ["01101", "01202", "14131"]


@pytest.mark.skipif(not SRC.exists(), reason="統計局の人口重心の表が cache にない")
def test_national_population_centroid_reproduces_published_value():
    """都道府県の人口重心と人口から、統計局の式で全国の人口重心（公表値）を再現できる"""
    from weighted_centers import centroid_table
    cen = centroid_table()
    muni = pd.read_csv(geo.DATA / "municipalities.csv", dtype={"code": str}).set_index("code")
    pref = muni.groupby(muni.index.str[:2])["pop"].sum()
    pc = cen.loc[[p + "000" for p in pref.index]]
    x, y = geo.stat_bureau_mean(pc["lon"], pc["lat"], pref.values)
    pub = cen.loc["00000"]
    assert geo.distance_km(x, y, pub["lon"], pub["lat"]) < 0.01


def test_population_history_moves_match_published_distances():
    """公表の移動距離（統計トピックス No.135・No.61）と、公表座標から計算した距離が一致する"""
    h = pd.read_csv(geo.DATA / "pop_centroid_history.csv")
    published = {1970: 8.3, 1975: 3.3, 1980: 1.5, 1985: 1.8, 1990: 3.1, 1995: 1.3, 2000: 1.4,
                 2005: 2.1, 2010: 2.4, 2015: 1.6, 2020: 2.2}
    for _, r in h.dropna(subset=["move_km"]).iterrows():
        assert r["move_km"] == pytest.approx(published[int(r["year"])], abs=0.06)


def test_offshore_points_are_not_assigned_to_municipalities():
    c = pd.read_csv(geo.DATA / "centers.csv")
    sea = c[c["land"] == "海上"]
    assert len(sea) > 0
    assert sea["municipality"].isna().all() and sea["pref"].isna().all()


def test_every_center_has_definition_and_source():
    c = pd.read_csv(geo.DATA / "centers.csv")
    assert c["definition"].notna().all() and c["source"].notna().all() and c["year"].notna().all()
    assert c["id"].is_unique
