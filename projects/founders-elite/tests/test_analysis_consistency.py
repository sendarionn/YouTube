"""analysis.md の主な数値が集計ファイル（summary.json）と一致することの確認（progress.md「訂正の記録」）"""
import csv
import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
S = json.loads((PROJECT / "data" / "summary.json").read_text(encoding="utf-8"))
TEXT = (PROJECT / "analysis.md").read_text(encoding="utf-8")

# analysis.md の記述と summary.json のキー
PATTERNS = {
    r"判明しなかった人は(\d+\.\d)%": "large_org_pct_edu_unknown",
    r"学歴が判明した人は、大手組織の勤務経験の割合が(\d+\.\d)%": "large_org_pct_edu_known",
    r"上記の大手組織のいずれか \| (\d+\.\d)%": "large_org_pct_among_known",
    r"学生起業（勤務歴なし・25歳以下）(\d+\.\d)%": "student_founder_pct",
    r"略歴に勤務先の記載がない人(\d+\.\d)%": "no_prior_job_pct",
    r"連続起業（創業前に別会社を設立）(\d+\.\d)%": "serial_pct",
    r"中央値33歳、平均(\d+\.\d)歳": "age_at_founding_mean",
}


def test_values_match_summary():
    for pat, key in PATTERNS.items():
        m = re.search(pat, TEXT)
        assert m, pat
        assert float(m.group(1)) == S[key], (pat, m.group(1), S[key])


def test_age_table_matches_counts():
    n = S["career_known"]
    for label, count in S["age_bins"].items():
        assert f"| {label} | {count} | {100 * count / n:.1f}% |" in TEXT, label


def test_edu_unknown_share_recomputed_from_founders():
    """summary.json の値を founders.csv から計算し直す（分母：学歴が不明で職歴の分類がある人）"""
    with open(PROJECT / "data" / "founders.csv", encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["target_20y"] == "Y"]
    for known, key in ((False, "large_org_pct_edu_unknown"), (True, "large_org_pct_edu_known")):
        g = [r for r in rows if (r["education_level"] != "不明") == known and r["large_org"] != ""]
        num = sum(r["large_org"] == "Y" for r in g)
        assert round(100 * num / len(g), 1) == S[key]
