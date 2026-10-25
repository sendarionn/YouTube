"""中心の一覧（data/centers.csv、data/centers.json）を作る

- 入力：独自計算（computed_*.csv）と、公表値・制度・歴史・自治体の主張（curated_centers.csv）
- 座標がなく住所だけの項目は、国土地理院の住所検索で代表点を求める
- place は資料が示す場所（なければ located と同じ）、located は座標から求めた所在地
- 所在地：国土地理院の逆ジオコーダーで市区町村と町字を求める。該当しない場合は海上として、最寄りの陸地までの距離を記録し、
  自治体には割り当てない
- 陸上・海上の判定は逆ジオコーダーの結果と、地球地図日本の陸地の面の両方で行い、食い違いを記録する
"""
import json

import numpy as np
import pandas as pd

import geo
import gsi_api
from geo import DATA

COLUMNS = ["id", "name", "field", "category", "definition", "place", "located", "land", "pref", "municipality", "lon", "lat",
           "lon_dms", "lat_dms", "year", "method", "unit_level", "source", "reliability", "top_unit", "top_share",
           "alt_km", "n_units", "note"]

# 分類（指示書4章）の表示順
CATEGORIES = ["幾何学的中心", "分布の重心", "最大集積地", "ネットワークの中心", "アクセスの中心", "制度的中心",
              "制度的・歴史的中心", "象徴的・通称的中心"]

# 定義が不確かな指標
UNCERTAIN = {
    "air_cargo": "定義を確認できない（統計ダッシュボードに説明がない）。成田空港のある千葉県が上位にないため、国内線の貨物とみられる（推測）",
    "important_cultural": "国立博物館などが所有する美術工芸品を含むため、所有者の所在地に左右される",
    "deposits": "預金の所在地は銀行の店舗の所在地で、預金者の住所ではない",
    "gdp": "都道府県単位。代表点は都道府県の人口重心",
}


def muni_names():
    m = pd.read_csv(DATA / "municipalities.csv", dtype={"code": str}).set_index("code")
    names = {c: (r["pref"], r["name"]) for c, r in m.iterrows()}
    from weighted_centers import centroid_table
    t = centroid_table()
    for c, r in t.iterrows():
        if c not in names and not c.endswith("000"):
            pref = t.loc[c[:2] + "000", "name"] if c[:2] + "000" in t.index else ""
            names[c] = (pref, r["name"])
    return names


def reliability(r):
    if isinstance(r.get("reliability"), str) and r["reliability"]:
        return r["reliability"]
    if r["id"] in UNCERTAIN and r["id"] in ("air_cargo",):
        return "低（定義未確認）"
    lvl = str(r.get("unit_level", ""))
    if "都道府県" in lvl:
        return "中（都道府県単位。代表点の選び方に左右される）"
    if "市区町村" in lvl:
        return "高（市区町村単位、再計算可能）"
    return "高（再計算可能）"


def main():
    comp = pd.concat([pd.read_csv(DATA / f) for f in
                      ["computed_geometry.csv", "computed_weighted.csv", "computed_network.csv", "computed_other.csv"]],
                     ignore_index=True)
    comp["category"] = comp["category"].fillna("分布の重心")
    cur = pd.read_csv(DATA / "curated_centers.csv", dtype=str)
    from other_centers import from_dms
    cur["lon"] = cur["lon_dms"].map(lambda s: from_dms(s) if isinstance(s, str) and s.strip() else np.nan)
    cur["lat"] = cur["lat_dms"].map(lambda s: from_dms(s) if isinstance(s, str) and s.strip() else np.nan)
    cur["unit_level"] = "地点"
    for i, r in cur.iterrows():
        if pd.isna(r["lat"]) and isinstance(r["address"], str):
            g = gsi_api.geocode(r["address"])
            if g is None:
                raise SystemExit(f"住所が見つからない：{r['address']}")
            if not pd.isna(r["lon"]):  # 経線だけ（標準時子午線）は緯度を求めない
                continue
            cur.loc[i, ["lon", "lat"]] = g[0], g[1]
            cur.loc[i, "unit_level"] = f"住所の代表点（{g[2]}）"
    cur = cur.rename(columns={"place_name": "place"})
    # 最大集積地：分布の重心の計算に使った指標のうち、主なものを別の項目として加える
    tops = []
    for key, label in [("gdp", "経済活動（県内総生産）"), ("employees", "働く場所（民営事業所の従業者）"),
                       ("emp_ict", "情報通信業の従業者"), ("agri_output", "農業産出額"), ("fish_catch", "海面漁業漁獲量"),
                       ("guest_nights", "延べ宿泊者数"), ("important_cultural", "重要文化財"), ("power_gen", "発電電力量"),
                       ("univ_students", "大学生"), ("forest", "森林面積")]:
        r = comp[comp["id"] == key].iloc[0]
        tops.append(dict(id=f"max_{key}", name=f"{label}の最大集積地", field=r["field"], category="最大集積地",
                         definition=f"{r['definition']}が最も多い{'都道府県' if '都道府県' in r['unit_level'] else '市区町村（区）'}",
                         place=r["top_unit"], unit_level=r["unit_level"], year=r["year"], method="独自集計",
                         source=r["source"], top_unit=r["top_unit"], top_share=r["top_share"],
                         note=f"全国の {r['top_share'] * 100:.1f}%。地図には置かない（地域であり点ではない）"))
    df = pd.concat([comp, cur, pd.DataFrame(tops)], ignore_index=True)

    names = muni_names()
    for i, r in df.iterrows():
        if pd.isna(r["lat"]) or pd.isna(r["lon"]):
            continue
        code, town = gsi_api.reverse(r["lon"], r["lat"])
        on_land = geo.land_code(r["lon"], r["lat"]) is not None
        df.loc[i, "lon_dms"], df.loc[i, "lat_dms"] = geo.dms(r["lon"]), geo.dms(r["lat"])
        if code:
            pref, muni = names.get(code, ("", f"（コード {code}）"))
            df.loc[i, "pref"], df.loc[i, "municipality"] = pref, muni
            df.loc[i, "land"] = "陸上" if on_land else "陸上（逆ジオコーダー）／海上（1:100万の陸地）"
            auto = f"{pref}{muni}{(town or '').strip('−')}"
        else:
            km = geo.nearest_land_km(r["lon"], r["lat"])
            df.loc[i, "land"] = "海上" if not on_land else "海上（逆ジオコーダー）／陸上（1:100万の陸地）"
            auto = f"海上（最寄りの陸地まで約{km:.0f}km）"
        df.loc[i, "located"] = auto
        if pd.isna(r.get("place")) or not str(r.get("place")).strip():
            df.loc[i, "place"] = auto
    df["reliability"] = df.apply(reliability, axis=1)
    for k, v in UNCERTAIN.items():
        m = df["id"].isin([k, f"max_{k}"])
        df.loc[m, "note"] = df.loc[m, "note"].fillna("").map(lambda s: (s + "。" if s else "") + v)
    df["category"] = pd.Categorical(df["category"], CATEGORIES, ordered=True)
    df = df.sort_values(["category", "field", "id"])[COLUMNS]
    df.to_csv(DATA / "centers.csv", index=False)
    recs = json.loads(df.to_json(orient="records", force_ascii=False))
    (DATA / "centers.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1))
    print(df.groupby(["category", "land"], observed=True).size())
    print(df[["id", "place", "land"]].to_string())


if __name__ == "__main__":
    main()
