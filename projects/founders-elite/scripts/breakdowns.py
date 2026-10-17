"""analysis.md 用の追加集計

analyze.py の出力（data/companies.csv, data/founders.csv）を読み、次を data/breakdowns.json に出す
- 経過年数の基準（10年・20年・制限なし）による違い
- 大手組織の勤務経験・学生起業とIPOまでの年数
- 上場年（前半・後半）による違い
- 学歴の判明状況と企業の知名度の関係を見るため、判明率を上場年別に
"""
import json

import pandas as pd

from paths import DATA


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def career_stats(d):
    d = d[d.career_p1 != ""]
    age = pd.to_numeric(d.age_at_founding, errors="coerce")
    yb = pd.to_numeric(d.years_before, errors="coerce")
    return {
        "n_career": int(len(d)),
        "age_median": float(age.median()) if len(d) else None,
        "age_le25_pct": pct((age <= 25).sum(), age.notna().sum()),
        "age_40plus_pct": pct((age >= 40).sum(), age.notna().sum()),
        "years_before_median": float(yb.median()) if len(d) else None,
        "large_org_pct": pct((d.large_org == "Y").sum(), len(d)),
        "consulting_pct": pct((d.cat_consulting == "Y").sum(), len(d)),
        "finance_pct": pct((d.cat_finance == "Y").sum(), len(d)),
        "net_megaventure_pct": pct((d.cat_net_megaventure == "Y").sum(), len(d)),
        "student_founder_pct": pct((d.student_founder == "Y").sum(), len(d)),
        "no_prior_job_pct": pct((d.no_prior_job == "Y").sum(), len(d)),
        "serial_pct": pct((d.serial == "Y").sum(), len(d)),
    }


def main():
    f = pd.read_csv(DATA / "founders.csv", dtype=str).fillna("")
    f = f[f.type.isin(["IND", "SPIN", "UNIV"]) & (f.name != "")]
    f["yti"] = pd.to_numeric(f.years_to_ipo, errors="coerce")
    B = {}

    B["by_horizon"] = {}
    for lim in (10, 20, None):
        d = f[f.yti <= lim] if lim else f
        B["by_horizon"][f"le{lim}" if lim else "all"] = {"n_named": int(len(d)), **career_stats(d)}

    t = f[f.yti <= 20]
    car = t[t.career_p1 != ""]
    g = {}
    for label, m in [("large_org", car.large_org == "Y"), ("no_large_org", car.large_org != "Y"),
                     ("student", car.student_founder == "Y"), ("no_prior_job", car.no_prior_job == "Y"),
                     ("serial", car.serial == "Y"), ("not_serial", car.serial != "Y")]:
        d = car[m]
        age = pd.to_numeric(d.age_at_founding, errors="coerce")
        g[label] = {"n": int(len(d)), "years_to_ipo_median": float(d.yti.median()),
                    "age_median": float(age.median()) if age.notna().any() else None}
    B["years_to_ipo_by_group_target20"] = g

    t2 = t.copy()
    t2["half"] = t2.listing_year.astype(int).map(lambda y: "2016-2020" if y <= 2020 else "2021-2025")
    B["by_listing_half_target20"] = {h: {"n_named": int(len(d)), **career_stats(d)} for h, d in t2.groupby("half")}

    t2["edu_known"] = t2.education_level != "不明"
    B["edu_known_pct_by_year_target20"] = {y: pct(d.edu_known.sum(), len(d)) for y, d in t2.groupby("listing_year")}

    # 職種の分布（SPIN・UNIV を含む型別の人数）
    B["named_by_type_target20"] = t.type.value_counts().to_dict()

    json.dump(B, open(DATA / "breakdowns.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(B, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
