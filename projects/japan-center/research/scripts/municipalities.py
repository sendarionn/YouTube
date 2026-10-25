"""市区町村ごとの人口重心と国勢調査の値をまとめた表を作る（data/municipalities.csv）

入力（cache/japan-center/src/。取得元は sources.md）
- topics135_10.xlsx：統計局「各都道府県及び市区町村の人口重心（10進数）」（2020年国勢調査）
- f_000032143614.bin：「都道府県・市区町村別の主な結果」2020年（major_results_2020.xlsx）
- f_000040507382.bin：同 2025年（major_results_2025.xlsx）

指定都市は区を単位にし、市の合計の行は使わない（市などの別 = 1 を除く）
"""
import pandas as pd

from geo import CACHE, DATA

SRC = CACHE / "src"

# 2020年の表の列番号（第１面・第２面）と、出力の列名
SHEET1 = {4: "pop", 14: "age0_14", 16: "age65p", 33: "japanese", 34: "foreign", 35: "households"}
SHEET2 = {13: "workers", 14: "w_agri_forest", 16: "w_fishery", 17: "w_mining", 18: "w_construction",
          19: "w_manufacturing", 20: "w_utilities", 21: "w_ict", 22: "w_transport", 23: "w_trade",
          24: "w_finance", 25: "w_realestate", 26: "w_research", 27: "w_hospitality", 28: "w_lifestyle",
          29: "w_education", 30: "w_medical", 33: "w_public", 53: "daytime_pop"}


def _read(path, sheet, cols):
    v = pd.read_excel(path, sheet_name=sheet, header=None, skiprows=9, dtype=str)
    v = v[v[3].isin(["0", "2", "3"])]
    out = pd.DataFrame({"code": v[1].str[:5], "name": v[1].str[6:], "pref": v[0].str[3:]})
    for c, name in cols.items():
        out[name] = pd.to_numeric(v[c].str.replace(",", ""), errors="coerce")
    return out.set_index("code")


def build():
    cen = pd.concat([d.iloc[2:, :4] for k, d in pd.read_excel(SRC / "topics135_10.xlsx", sheet_name=None,
                                                              header=None).items() if k != "全国"])
    cen.columns = ["code", "cname", "lon", "lat"]
    cen = cen.assign(code=cen["code"].astype(str).str.zfill(5)).drop_duplicates("code").set_index("code")
    t1 = _read(SRC / "f_000032143614.bin", "第１面事項_2020年", SHEET1)
    t2 = _read(SRC / "f_000032143614.bin", "第２面事項_2020年", SHEET2)
    t25 = _read(SRC / "f_000040507382.bin", "第１面事項_2025年", {4: "pop2025"})["pop2025"]
    m = t1.join(t2.drop(columns=["name", "pref"])).join(t25)
    # 2020〜2025年に区の再編があった指定都市（浜松市）は、2025年の人口を市の単位で、2020年の区の人口の比で割り振る
    changed = set(t25.index) ^ set(t1.index)
    old = m.index[m.index.isin(changed)]
    if len(old):
        if not all(c.startswith("221") and "22131" <= c <= "22140" for c in changed):
            raise SystemExit(f"浜松市以外の区域の変更：{sorted(changed)}")
        total = t25[t25.index.isin(changed)].sum()
        m.loc[old, "pop2025"] = total * m.loc[old, "pop"] / m.loc[old, "pop"].sum()
        print(f"区の再編（浜松市）：2025年の人口 {int(total)} を2020年の {len(old)} 区に人口の比で割り振った")
    m = m.join(cen[["lon", "lat"]], how="left")
    missing = m[m["lon"].isna()]
    if (missing["pop"] > 0).any():
        raise SystemExit(f"人口重心のない市区町村：{missing.index.tolist()}")
    m = m.drop(missing.index)  # 2020年の人口が0（福島県双葉町）。重心がなく、重みも0
    m["lon"], m["lat"] = m["lon"].astype(float), m["lat"].astype(float)
    m.to_csv(DATA / "municipalities.csv")
    return m


if __name__ == "__main__":
    m = build()
    print(len(m), "市区町村", int(m["pop"].sum()), "人（2020）", int(m["pop2025"].sum()), "人（2025）")
    print(m[m["pop2025"].isna()][["name", "pop"]])
