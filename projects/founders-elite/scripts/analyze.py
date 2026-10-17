"""データセットの作成、集計、検証用グラフの出力

入力: data/jpx_listings.csv, data/screening.csv, data/founders_base.csv,
      data/founders_career.csv, data/evidence_manual.tsv
出力: data/companies.csv, data/founders.csv, data/evidence.csv,
      data/summary.json, OUTPUT/charts/*.png
"""
import json
import re

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from paths import CACHE, DATA, OUTPUT  # noqa: E402

plt.rcParams["font.family"] = ["Hiragino Sans", "Hiragino Kaku Gothic ProN", "sans-serif"]
TARGET_TYPES = {"IND", "SPIN", "UNIV"}

# 大学の分類（定義は methodology.md）
KYUTEI = ["東京大学", "京都大学", "大阪大学", "東北大学", "名古屋大学", "九州大学", "北海道大学"]
NANKAN_KOKURITSU = KYUTEI + ["一橋大学", "東京工業大学", "東京科学大学", "神戸大学"]
SOKEI = ["早稲田大学", "慶應義塾大学"]


def load():
    jpx = pd.read_csv(DATA / "jpx_listings.csv", dtype=str)
    jpx["key"] = jpx.listing_date + "_" + jpx.code
    s = pd.read_csv(DATA / "screening.csv", dtype=str).fillna("")
    fb = pd.read_csv(DATA / "founders_base.csv", dtype=str).fillna("")
    fc = pd.read_csv(DATA / "founders_career.csv", dtype=str).fillna("")
    ev = pd.read_csv(DATA / "evidence_manual.tsv", sep="\t", dtype=str).fillna("")
    return jpx, s, fb, fc, ev


def companies(jpx, s):
    ext = {}
    for l in open(CACHE / "part1_extract.jsonl", encoding="utf-8"):
        e = json.loads(l)
        ext[e["key"]] = e
    c = jpx.merge(s, on="key", how="left")
    c["years_to_ipo"] = c.listing_year.astype(int) - pd.to_numeric(c.origin_ym.str[:4], errors="coerce")
    c["hq"] = c.key.map(lambda k: ext.get(k, {}).get("hq", ""))
    c["employees_consolidated"] = c.key.map(lambda k: (ext.get(k, {}).get("employees") or {}).get("consolidated", ""))
    c["employees_parent"] = c.key.map(lambda k: (ext.get(k, {}).get("employees") or {}).get("parent", ""))
    c["type"] = c.type.where(c.technical_listing == "0", "TECHNICAL")
    c["target_20y"] = (c.type.isin(TARGET_TYPES) & (c.years_to_ipo <= 20)).map({True: "Y", False: "N"})
    cols = ["key", "company_name", "code", "listing_date", "listing_year", "market", "technical_listing", "type",
            "origin_ym", "years_to_ipo", "target_20y", "founders", "founder_source", "note", "hq",
            "employees_consolidated", "employees_parent", "website", "part1_pdf", "source_url"]
    c[cols].to_csv(DATA / "companies.csv", index=False)
    return c


def edu_level(v):
    v = v or ""
    if not v:
        return "不明"
    head = v.split("|")[0]
    if "大学院修了" in head:
        return "大学院修了"
    if "中退" in head:
        return "大学中退"
    if "在学中" in head or "在籍" in head:
        return "大学在籍・在学中起業（卒業未確認）"
    if head.startswith("大学卒"):
        return "大学卒業"
    if "高専" in head or "専門学校" in head or "短大" in head:
        return "短大・高専・専門学校"
    if "高校" in head or "大学進学なし" in head:
        return "高校卒業・大学進学なし"
    if "大学" in head:
        return "大学卒業"
    return "その他"


def first_univ(v):
    parts = (v or "").split("|")
    return parts[1].split(";")[0].strip() if len(parts) > 1 else ""


def founders(fb, fc, ev, c):
    edu = ev[(ev.attribute == "education") & ev.status.isin(["verified", "partial"])]
    edu = edu.drop_duplicates("founder_id", keep="last")
    f = fb.merge(fc, on="founder_id", how="left").merge(
        edu[["founder_id", "value", "status", "source_url"]].rename(
            columns={"value": "education_raw", "status": "education_status", "source_url": "education_source"}),
        on="founder_id", how="left").fillna("")
    f = f.merge(c[["key", "listing_year", "years_to_ipo", "type", "target_20y"]], on="key", how="left")
    f["education_level"] = f.education_raw.map(edu_level)
    f["university"] = f.education_raw.map(first_univ)
    f["university"] = f.university.where(~f.university.isin(["不明", "不明（学部）"]), "")
    f.to_csv(DATA / "founders.csv", index=False)
    return f


def evidence(ev, fb):
    rows = []
    for r in ev.itertuples():
        rows.append(r._asdict())
    for r in fb.itertuples():
        if r.career_p1:
            rows.append({"founder_id": r.founder_id, "attribute": "career", "value": r.career_p1[:300],
                         "source_url": r.career_source or "P1", "source_type": "P1" if r.career_source == "P1" else "edinet_mirror",
                         "status": "verified", "quote": "Iの部または有価証券報告書の役員略歴（全文は founders_base.csv）"})
    out = pd.DataFrame(rows).drop(columns=["Index"], errors="ignore")
    out["accessed"] = "2026-10-17"
    out.to_csv(DATA / "evidence.csv", index=False)


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def summarize(c, f):
    S = {}
    S["listings_total"] = int(len(c))
    S["technical"] = int((c.type == "TECHNICAL").sum())
    S["type_counts"] = c[c.type != "TECHNICAL"].type.value_counts().to_dict()
    for lim in (10, 20, None):
        name = f"target_{lim or 'all'}"
        m = c.type.isin(TARGET_TYPES) & ((c.years_to_ipo <= lim) if lim else True)
        S[name] = int(m.sum())
    S["years_to_ipo_median_target20"] = float(c[c.target_20y == "Y"].years_to_ipo.median())

    t = f[f.target_20y == "Y"].copy()
    S["founders_rows_target20"] = int(len(t))
    named = t[t.name != ""]
    S["founders_named_target20"] = int(len(named))
    S["companies_target20_with_named_founder"] = int(named.key.nunique())
    car = named[named.career_p1 != ""].copy()
    S["career_known"] = int(len(car))
    car["age"] = pd.to_numeric(car.age_at_founding, errors="coerce")
    S["age_at_founding_median"] = float(car.age.median())
    S["age_at_founding_mean"] = round(float(car.age.mean()), 1)
    bins = [0, 25, 29, 34, 39, 49, 200]
    labels = ["25歳以下", "26〜29歳", "30〜34歳", "35〜39歳", "40〜49歳", "50歳以上"]
    S["age_bins"] = pd.cut(car.age, bins=bins, labels=labels).value_counts().reindex(labels).fillna(0).astype(int).to_dict()
    S["student_founder_pct"] = pct((car.student_founder == "Y").sum(), len(car))
    S["no_prior_job_pct"] = pct((car.no_prior_job == "Y").sum(), len(car))
    S["serial_pct"] = pct((car.serial == "Y").sum(), len(car))
    yb = pd.to_numeric(car.years_before, errors="coerce")
    S["years_before_median"] = float(yb.median())
    S["years_before_bins"] = pd.cut(yb, bins=[-1, 0, 4, 9, 14, 19, 100],
                                   labels=["0年", "1〜4年", "5〜9年", "10〜14年", "15〜19年", "20年以上"]).value_counts().sort_index().astype(int).to_dict()
    cats = [k for k in car.columns if k.startswith("cat_")]
    S["career_categories_pct"] = {k[4:]: pct((car[k] == "Y").sum(), len(car)) for k in cats}
    S["large_org_pct_among_known"] = pct((car.large_org == "Y").sum(), len(car))

    # 学歴
    lv = named.education_level.value_counts().to_dict()
    S["education_levels_all_named"] = lv
    known = named[named.education_level != "不明"]
    S["education_known"] = int(len(known))
    S["education_known_pct"] = pct(len(known), len(named))
    univ_like = known.education_level.isin(["大学院修了", "大学卒業", "大学在籍・在学中起業（卒業未確認）", "大学中退"])
    S["univ_any_among_known_pct"] = pct(univ_like.sum(), len(known))
    grad = known.education_level.isin(["大学院修了", "大学卒業"])
    S["degree_lower_bound_pct_of_named"] = pct(grad.sum(), len(named))
    S["degree_upper_bound_pct_of_named"] = pct(grad.sum() + (named.education_level == "不明").sum(), len(named))
    # 高校・高専・専門学校の学校名は大学の集計に含めない
    uk = known[(known.university != "") & known.education_level.isin(["大学院修了", "大学卒業", "大学在籍・在学中起業（卒業未確認）", "大学中退"])]
    S["university_counts"] = uk.university.value_counts().to_dict()
    u = uk.university
    S["univ_groups_among_named_univ"] = {
        "東京大学": int((u == "東京大学").sum()),
        "旧帝大7校": int(u.isin(KYUTEI).sum()),
        "旧帝大+一橋・東工・神戸": int(u.isin(NANKAN_KOKURITSU).sum()),
        "早稲田・慶應": int(u.isin(SOKEI).sum()),
        "海外大学": int(u.str.contains("大学").eq(False).sum() + u.str.contains("ロンドン|テキサス|カリフォルニア|カーネギー|ジョージア|パデュー|サンダーバード").sum()),
        "大学名あり合計": int(len(u)),
    }
    # 学歴が分かる人と分からない人で、職歴に差があるか（判明の偏りの確認）
    m = named.merge(car[["founder_id", "large_org"]], on="founder_id", how="left", suffixes=("", "_c"))
    k1 = m[m.education_level != "不明"]
    k0 = m[m.education_level == "不明"]
    S["large_org_pct_edu_known"] = pct((k1.large_org == "Y").sum(), (k1.large_org != "").sum())
    S["large_org_pct_edu_unknown"] = pct((k0.large_org == "Y").sum(), (k0.large_org != "").sum())
    # 無作為標本（edu_sample.py）での学歴。判明者だけの集計より、有名人への偏りが小さい
    sp = DATA / "edu_sample.csv"
    if sp.exists():
        ids = pd.read_csv(sp, dtype=str).founder_id
        smp = named[named.founder_id.isin(ids)]
        sk = smp[smp.education_level != "不明"]
        S["sample_n"] = int(len(smp))
        S["sample_education_levels"] = smp.education_level.value_counts().to_dict()
        S["sample_known"] = int(len(sk))
        S["sample_degree_lower_bound_pct"] = pct(sk.education_level.isin(["大学院修了", "大学卒業"]).sum(), len(smp))
        S["sample_univ_among_known"] = sk[(sk.university != "") & sk.education_level.isin(["大学院修了", "大学卒業", "大学在籍・在学中起業（卒業未確認）", "大学中退"])].university.value_counts().to_dict()
    json.dump(S, open(DATA / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return S, car, named


def charts(S, car, named):
    out = OUTPUT / "charts"
    out.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 4))
    ages = S["age_bins"]
    ax.bar(list(ages), list(ages.values()), color="#4a6fa5")
    ax.set_title(f"創業時の年齢（n={sum(ages.values())}）")
    ax.set_ylabel("人数")
    fig.tight_layout()
    fig.savefig(out / "age_at_founding.png", dpi=150)
    plt.close(fig)

    names = {"consulting": "コンサル", "finance": "金融", "trading": "総合商社", "net_megaventure": "ネット大手",
             "foreign_tech": "外資系IT", "jp_large_maker_infra": "国内大手", "public_academia": "官公庁・大学・研究機関",
             "medical": "医療", "accounting_legal": "会計・法律"}
    cp = S["career_categories_pct"]
    items = sorted(((names[k], v) for k, v in cp.items()), key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.barh([i[0] for i in items], [i[1] for i in items], color="#4a6fa5")
    ax.set_xlabel("創業前に勤務経験がある割合（%）")
    ax.set_title(f"創業前の勤務先（略歴が判明した{S['career_known']}人、複数該当あり）")
    fig.tight_layout()
    fig.savefig(out / "career_categories.png", dpi=150)
    plt.close(fig)

    lv = S["education_levels_all_named"]
    order = ["大学院修了", "大学卒業", "大学在籍・在学中起業（卒業未確認）", "大学中退", "短大・高専・専門学校", "高校卒業・大学進学なし", "その他", "不明"]
    vals = [lv.get(k, 0) for k in order]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = ["#4a6fa5"] * 7 + ["#bbbbbb"]
    ax.barh(order[::-1], vals[::-1], color=colors[::-1])
    ax.set_title(f"最終学歴（創業者{sum(vals)}人。灰色は公開情報で確認できなかった人）")
    ax.set_xlabel("人数")
    fig.tight_layout()
    fig.savefig(out / "education_levels.png", dpi=150)
    plt.close(fig)

    uc = pd.Series(S["university_counts"]).head(15)[::-1]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(uc.index, uc.values, color="#4a6fa5")
    ax.set_title("出身大学（学部、判明分のみ）")
    ax.set_xlabel("人数")
    fig.tight_layout()
    fig.savefig(out / "universities.png", dpi=150)
    plt.close(fig)

    yb = S["years_before_bins"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(list(yb), list(yb.values()), color="#4a6fa5")
    ax.set_title("初職から創業までの年数")
    ax.set_ylabel("人数")
    fig.tight_layout()
    fig.savefig(out / "years_before_founding.png", dpi=150)
    plt.close(fig)


def main():
    jpx, s, fb, fc, ev = load()
    c = companies(jpx, s)
    f = founders(fb, fc, ev, c)
    evidence(ev, fb)
    S, car, named = summarize(c, f)
    charts(S, car, named)
    print(json.dumps(S, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
