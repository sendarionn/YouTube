"""書誌レコードを刊行点数の単位（1タイトル・1版）にまとめる

入力：cache/shinsho-labels/raw/<シリーズ名>.jsonl（collect.py）
出力：data/titles.csv（1行1点）、data/normalize_report.csv（規則ごとの件数）

規則（methodology.md「刊行点数の数え方」）
1. 紙の図書だけを残す：カテゴリが「マイクロ」だけ・「デジタル」だけの書誌は、同じ本の複製として除く
2. 同じシリーズ・同じ番号の書誌は1点にまとめる（重版・刷の書誌）
3. 番号のない書誌は、正規化した題名・最初の著者・版の表示が同じものを1点にまとめる（新版・改訂版は別の点）。番号のある書誌と同じ題名・著者で
   同じ時期（era）なら、その番号の点に含める（時期が違えば別の版として数える）
4. 刊行年は、まとめた書誌のうち最も早い年。価格・ページ数は、その年の書誌の値を使う
5. シリーズの時期（era）：同じ名前の別シリーズや時代区分を、刊行年とシリーズ名で分ける（ERAS）
"""
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from tools.infographic.config import CACHE  # noqa: E402

RAW = CACHE / "shinsho-labels" / "raw"
DATA = HERE.parent / "data"


def iwanami_era(year, series):
    if "新赤版" in series:
        return "新赤版"
    if year and year >= 1988:
        return "新赤版"
    if year and year >= 1977:
        return "黄版"
    if year and year >= 1949:
        return "青版"
    return "赤版"


# シリーズごとの時期区分。戻り値が None の書誌は対象外（同じ名前の別シリーズなど）
ERAS = {
    "岩波新書": lambda y, s: iwanami_era(y, s),
    "角川新書": lambda y, s: "角川新書（2014年〜）" if y and y >= 2014 else "角川新書（旧・1950年代〜）",
    "河出新書": lambda y, s: "河出新書（2018年〜）" if y and y >= 2018 else "河出新書（旧・1950年代〜）",
}


def nfkc(s):
    return unicodedata.normalize("NFKC", s or "")


def norm_title(t):
    t = nfkc(t).split(" : ")[0]
    return re.sub(r"[\s・･:：\-ー―〜~「」『』（）()\[\]【】!！?？、。,.]", "", t).lower()


def edition_key(r):
    """版の表示を比べられる形にする（「2版」「第2版」は同じ、記載なしと「初版」は同じ）。刷の違いは書誌に出ないことが多い"""
    e = nfkc(" ".join(r["edition"]))
    e = re.sub(r"\s|第", "", e)
    if not e or e in ("初版", "1版"):
        return ""
    m = re.match(r"(\d+)版", e)
    return f"{m.group(1)}版" if m else e


def year_month(r):
    for v in r["issued"] + r["date"]:
        m = re.match(r"(\d{4})(?:[.\-](\d{1,2}))?", v)
        if m:
            return int(m.group(1)), int(m.group(2)) if m.group(2) else None
    return None, None


def series_number(series):
    """「岩波新書 新赤版 ; 1706」→ ("新赤版", "1706")。番号がなければ (None, None)"""
    s = nfkc(series)
    m = re.search(r";\s*([^;.]*?)(\d+[A-Za-z]?(?:-\d+[A-Za-z]?)?)\s*(?:\.|$)", s)
    if not m:
        return None, None
    prefix = re.sub(r"[第\s]", "", m.group(1)) or None
    return prefix, m.group(2)


def price(r):
    """(円, 区分)。区分は「表示価格」（税の記載なし）か「税込」。外貨・各巻の価格は使わない"""
    for p in r["price"]:
        p = nfkc(p)
        if p.startswith("各") or "円" not in p:
            continue
        m = re.match(r"(\d[\d,]*)円", p)
        if m:
            return int(m.group(1).replace(",", "")), "税込" if "税込" in p else "表示価格"
    return None, ""


def pages(r):
    """(本文のページ数, 別立てのページ数, 別立ての位置)

    国立国会図書館の記述「209, 3p」は本文209ページと、別にページ付けされた3ページ（巻末の索引・参考文献などのことが多い）。
    「12, 211p」のように前付けが先に来る記述もあるため、大きい方を本文、小さい方を別立てとし、位置（前・後）を記録する
    """
    for e in r["extent"]:
        e = nfkc(e)
        m = re.search(r"(?:(\d+)\s*,\s*)?(\d+)\s*p", e)
        if m:
            a, b = (int(m.group(1)) if m.group(1) else None), int(m.group(2))
            if a is None:
                return b, 0, ""
            return (a, b, "後") if a >= b else (b, a, "前")
    return None, None, ""


def ndc(r):
    """(第1次区分, 分類記号, 版)。NDC10 → NDC9 → NDC8 → NDC（版不明）の順に使う"""
    for k in ("NDC10", "NDC9", "NDC8", "NDC"):
        for v in r["subjects"].get(k, []):
            m = re.match(r"(\d)(\d{0,2}(?:\.\d+)?)", nfkc(v))
            if m:
                return m.group(1), m.group(0), k
    return "", "", ""


def creators(r):
    """(最初の著者の名前, 生年)。dc:creator の「姓, 名, 生年-」を使う"""
    for c in r["creator"]:
        parts = [p.strip() for p in nfkc(c).split(",")]
        name = "".join(p for p in parts if not re.match(r"^\d{4}", p) and p)
        birth = next((int(p[:4]) for p in parts if re.match(r"^\d{4}", p)), None)
        return name, birth
    return "", None


def translated(r):
    return bool(re.search(r"[\s,]訳|翻訳|訳$|訳,", nfkc(r["author"])))


def paper(r):
    cats = set(r["category"])
    return "紙" in cats or not ({"マイクロ", "デジタル"} & cats)


def normalize(label, category, records, report):
    pat_era = ERAS.get(label, lambda y, s: label)
    report[(label, "書誌レコード")] += len(records)
    groups = {}  # key -> list of records
    by_title = {}
    numbered, unnumbered = [], []
    for r in records:
        if not paper(r):
            report[(label, "除外：マイクロ・デジタルだけの書誌")] += 1
            continue
        s = r["series"][0] if r["series"] else ""
        pre, no = series_number(s)
        (numbered if no else unnumbered).append((r, pre, no))
    for r, pre, no in numbered:
        y, _ = year_month(r)
        era = pat_era(y, r["series"][0])
        key = (era, pre or "", no)
        groups.setdefault(key, []).append(r)
        name, _ = creators(r)
        by_title.setdefault((norm_title(r["title"][0] if r["title"] else ""), name, edition_key(r)), key)
    for r, _, _ in unnumbered:
        name, _ = creators(r)
        tkey = (norm_title(r["title"][0] if r["title"] else ""), name, edition_key(r))
        y, _ = year_month(r)
        era = pat_era(y, r["series"][0] if r["series"] else "")
        # 同じ題名・著者でも、時期が違えば別の版（例：青版の本の新赤版での改版）として別に数える
        if tkey in by_title and by_title[tkey][0] == era:
            groups[by_title[tkey]].append(r)
            report[(label, "統合：番号のない書誌を同じ題名・著者の番号つきの点へ")] += 1
            continue
        key = (era, "", "t:" + "|".join(tkey))
        if key in groups:
            report[(label, "統合：番号のない書誌どうし（同じ題名・著者）")] += 1
        groups.setdefault(key, []).append(r)
    rows = []
    for (era, pre, no), rs in groups.items():
        rs.sort(key=lambda r: (year_month(r)[0] or 9999, year_month(r)[1] or 99))
        first = rs[0]
        y, m = year_month(first)
        pr, basis = price(first)
        pg, extra, extra_pos = pages(first)
        c1, code, ed = ndc(first)
        name, birth = creators(first)
        title = nfkc(first["title"][0] if first["title"] else "")
        rows.append({
            "label": label, "category": category, "era": era, "series_prefix": pre,
            "series_no": "" if no.startswith("t:") else no, "numbered": int(not no.startswith("t:")),
            "title": title.split(" : ")[0], "subtitle": " : ".join(title.split(" : ")[1:]),
            "year": y or "", "month": m or "", "price_yen": pr or "", "price_basis": basis,
            "pages": pg or "", "extra_pages": extra if extra is not None else "", "extra_pages_position": extra_pos,
            "ndc_class": c1, "ndc": code, "ndc_edition": ed, "translated": int(translated(first)),
            "first_creator": name, "first_creator_birth": birth or "", "n_creators": len(first["creator"]),
            "edition": "; ".join(first["edition"]), "isbn": (first["ids"].get("ISBN") or [""])[0],
            "ndl_bibid": (first["ids"].get("NDLBibID") or [""])[0], "records_merged": len(rs),
            "author_statement": nfkc(first["author"]),
        })
    report[(label, "刊行点数（まとめた後）")] += len(rows)
    report[(label, "うち番号のない点")] += sum(1 for r in rows if not r["numbered"])
    return rows


def main():
    cands = {c["label"]: c for c in csv.DictReader((DATA / "label_candidates.csv").open(encoding="utf-8"))}
    report, out = Counter(), []
    for path in sorted(RAW.glob("*.jsonl")):
        label = path.stem
        recs = [json.loads(l) for l in path.open(encoding="utf-8")]
        out += normalize(label, cands[label]["category"], recs, report)
    out.sort(key=lambda r: (r["label"], r["era"], r["year"] or 0, r["series_no"]))
    with (DATA / "titles.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(out[0]))
        w.writeheader()
        w.writerows(out)
    with (DATA / "normalize_report.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "rule", "count"])
        for (label, rule), n in sorted(report.items()):
            w.writerow([label, rule, n])
    by = defaultdict(dict)
    for (label, rule), n in report.items():
        by[label][rule] = n
    for label, d in by.items():
        print(label, d.get("書誌レコード"), "→", d.get("刊行点数（まとめた後）"), "（番号なし", d.get("うち番号のない点", 0), "）")


if __name__ == "__main__":
    main()
