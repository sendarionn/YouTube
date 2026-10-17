"""classify_careers.classify の回帰テスト"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from classify_careers import classify  # noqa: E402


def row(career, origin="2006-01", birth="1980-01-01"):
    return SimpleNamespace(founder_id="t_1", career_p1=career, origin_ym=origin, birth=birth)


def test_entries_after_origin_are_not_pre_founding():
    # 個人事業（2006年）が起点で、略歴は法人設立（2009年）から始まる例（2024-09-26_245A）
    r = classify(row("2009年3月/株式会社ＩＮＧＳ/設立/代表取締役社長/就任（現任）/2013年11月/株式会社エムズカンパニー/取締役/就任"))
    assert r["years_before"] is None
    assert r["no_prior_job"] == "Y"


def test_first_job_year_uses_first_job_not_first_entry():
    r = classify(row("1999年4月 ㈱Ａ設立 代表取締役 /2002年4月 ㈱Ｂ入社 /2006年1月 当社設立 代表取締役", origin="2006-01"))
    assert r["first_job_year"] == 2002
    assert r["years_before"] == 4
    assert r["serial"] == "Y"


def test_typical_career():
    r = classify(row("2003年4月 ㈱リクルート入社 /2011年3月 当社設立 代表取締役", origin="2011-03"))
    assert r["first_job_year"] == 2003
    assert r["years_before"] == 8
    assert r["no_prior_job"] == "N"


def test_shifted_dates_use_first_date():
    # 年月2つの後に記載2つが続き、1行目の記載が空になる形式（2017-12-13_6698_3）
    r = classify(row("1992年4月/1998年11月/㈱キーエンス入社/コグネックス㈱入社/2003年8月/当社設立取締役", origin="2003-08"))
    assert r["first_job_year"] == 1992
    assert r["years_before"] == 11
