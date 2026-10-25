"""統計ダッシュボード（総務省統計局）の API から、都道府県・市区町村別の指標を取得する

- API：https://dashboard.e-stat.go.jp/api/1.0/Json/getData（アプリケーション ID は不要）
- 応答は cache/japan-center/dash/<指標コード>_<地域区分>.json に保存し、再実行では保存済みを使う（--refresh で取り直す）
- 指標ごとに、全国の合計が揃う最新の年を使う。年は出力に記録する
- 出力：data/indicators.csv（指標, 地域区分, 年, 地域コード, 値）
"""
import json
import sys
import time

import pandas as pd
import requests

from geo import CACHE, DATA

API = "https://dashboard.e-stat.go.jp/api/1.0/Json/getData?Lang=JP&IndicatorCode={code}&RegionalRank={rank}"
DIR = CACHE / "dash"

# (キー, 指標コード, 地域区分 3=都道府県 4=市区町村)。市区町村別があるものは市区町村別を使う
INDICATORS = [
    ("gdp", "0705100401010010000", 3),            # 県内総生産（名目）2015年基準
    ("manufacturing", "0502010000000010010", 4),  # 製造品出荷額等
    ("retail", "0601010200000010010", 4),         # 小売業年間商品販売額
    ("deposits", "0702020101010010000", 3),       # 国内銀行預金残高
    ("establishments", "0701010001000010012", 4),  # 事業所数（民営）
    ("employees", "0701020001000010010", 4),      # 従業者数（民営）（従業地）
    ("emp_ict", "0701020301000210070", 4),        # 従業者数（民営）（情報通信業）
    ("emp_finance", "0701020301000210100", 4),    # 従業者数（民営）（金融業、保険業）
    ("emp_research", "0701020301000210120", 4),   # 従業者数（民営）（学術研究、専門・技術サービス業）
    ("agri_output", "0401010000000010010", 3),    # 農業産出額
    ("farmland", "0401040100000010000", 4),       # 耕地面積
    ("forest", "0101010200000010030", 4),         # 森林面積
    ("fish_catch", "0404010301000010010", 3),     # 海面漁業漁獲量
    ("power_gen", "0901020000000010000", 3),      # 発電電力量
    ("power_demand", "0901060000000010000", 3),   # 電力需要量
    ("guest_nights", "1003010201000010000", 3),   # 延べ宿泊者数（総数）
    ("guest_nights_foreign", "1003010201000110000", 3),  # 延べ宿泊者数（外国人）
    ("universities", "1201010800000010000", 3),   # 大学数
    ("univ_students", "1201051000000010000", 3),  # 大学学生数
    ("museums", "1202010500000010010", 3),        # 博物館数
    ("theaters", "1202010900000010010", 3),       # 劇場、音楽堂等数
    ("libraries", "1202010400000010010", 4),      # 図書館数
    ("important_cultural", "1203020101000010010", 3),  # 重要文化財指定件数
    ("religious_bodies", "1203040100000010000", 3),    # 宗教団体数
    ("hospitals", "1505020000000010000", 4),      # 病院数
    ("hospital_beds", "1505030000000010000", 4),  # 病院病床数
    ("doctors", "1505040000000010000", 4),        # 医師数
    ("air_cargo", "1001010202000010010", 3),      # 航空貨物輸送量
    ("sea_cargo", "1001010302000010010", 3),      # 海上出入貨物
    ("jr_freight", "1001010102010010010", 3),     # ＪＲ貨物発送量
    ("expressway_km", "1001020100000010070", 3),  # 道路実延長（高速道路）
]


def fetch(code, rank, refresh=False):
    path = DIR / f"{code}_{rank}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    DIR.mkdir(parents=True, exist_ok=True)
    url = API.format(code=code, rank=rank) + ("&TimeFrom=2015CY00" if rank == 4 else "")  # 市区町村別は件数の上限があるため2015年以降
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    body = r.content
    d = json.loads(body)
    if d["GET_STATS"]["RESULT"]["status"] != "0":
        raise RuntimeError(f"{code}: {d['GET_STATS']['RESULT']}")
    path.write_bytes(body)
    time.sleep(1)
    return d


def rows(key, code, rank, refresh=False):
    d = fetch(code, rank, refresh)
    objs = d["GET_STATS"]["STATISTICAL_DATA"]["DATA_INF"]["DATA_OBJ"]
    out = []
    for o in objs:
        v = o["VALUE"]
        if v.get("$") in (None, "", "-", "…", "***", "x", "X"):
            continue
        out.append({"key": key, "indicator": code, "rank": rank, "time": v["@time"], "region": v["@regionCode"],
                    "value": float(v["$"]), "unit": v.get("@unit")})
    return out


def latest(df, rank):
    """地域の数が十分に揃う最新の年（年・年度の値を優先し、地域の数が最大の9割以上の年）

    海のない県に港がないなど、値のない地域がある指標もあるため、47 を必須にしない
    """
    annual = df[df["time"].str.endswith(("CY00", "FY00"))]
    df = annual if len(annual) else df
    counts = df.groupby("time")["region"].nunique().sort_index()
    need = 0.9 * counts.max()
    ok = counts[counts >= need]
    return ok.index[-1]


def main():
    refresh = "--refresh" in sys.argv
    meta = json.loads((CACHE / "dash" / "indicators.json").read_text()) if (CACHE / "dash" / "indicators.json").exists() else None
    names = {}
    if meta:
        for o in meta["GET_META_INDICATOR_INF"]["METADATA_INF"]["CLASS_INF"]["CLASS_OBJ"]:
            cl = o["CLASS"] if isinstance(o["CLASS"], list) else [o["CLASS"]]
            names[o["@code"]] = (o["@name"], cl[0].get("@statName", ""), cl[0].get("@unit", ""))
    out = []
    for key, code, rank in INDICATORS:
        df = pd.DataFrame(rows(key, code, rank, refresh))
        df = df[df["region"].str.endswith("000") == (rank == 3)]
        t = latest(df, rank)
        sel = df[df["time"] == t].copy()
        name, stat, unit = names.get(code, ("", "", ""))
        sel["name"], sel["stat"], sel["unit_name"] = name, stat, unit
        out.append(sel)
        print(f"{key:22s} {name}：{t}、{sel['region'].nunique()} 地域、単位 {unit}（{stat}）")
    pd.concat(out).to_csv(DATA / "indicators.csv", index=False)


if __name__ == "__main__":
    main()
