"""note 記事の生成のテスト（一時ディレクトリに研究資料・設定・原稿を作って実行する）"""
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools import note  # noqa: E402
from tools.note import article, research  # noqa: E402
from tools.infographic.config import OUTPUT, REPO  # noqa: E402

PAID_SENTENCE = "有料部分だけに書く詳しい分析の文章で、無料部分には出てはいけない内容です。"

MANUSCRIPT = f"""# テストの記事

無料部分では、対象は{{{{n:total}}}}件で、中央値は{{{{n:median}}}}歳でした{{{{s:A1}}}}。<!--C:C1-->

{{{{fig:chart-001}}}}

動画：{{{{link:YOUTUBE_URL}}}}

<!-- paid -->

## 詳しい分析

{PAID_SENTENCE}割合は{{{{n:share}}}}%です。<!--C:C1-->

{{{{attach:data.zip}}}}
"""


def make_project(tmp_path, monkeypatch, **cfg_over):
    projects = tmp_path / "projects"
    pdir = projects / "demo"
    (pdir / "data").mkdir(parents=True)
    (pdir / "video").mkdir()
    (pdir / "video" / "narration.md").write_text("台本", encoding="utf-8")
    (pdir / "data" / "summary.json").write_text(json.dumps({"total": 120, "median": 33.0, "bins": {"20代": 30, "30代": 60}}),
                                                encoding="utf-8")
    (pdir / "data" / "items.csv").write_text("kind,value,share\nA,10,12.5\nB,20,\n", encoding="utf-8")
    (pdir / "data" / "third.csv").write_text("x\n1\n", encoding="utf-8")
    (pdir / "analysis.md").write_text("# 分析\n", encoding="utf-8")
    (pdir / "progress.md").write_text("# 進捗\n\n## 研究版\n\n| 版 | 承認日 | コミット | 範囲 |\n| --- | --- | --- | --- |\n"
                                      "| research-v1 | 2026-10-21 | abc | 全体 |\n", encoding="utf-8")
    cfg = {
        "title": "テストの記事", "mode": "trial", "research_root": ".", "report": None,
        "links": {"YOUTUBE_URL": None},
        "numbers": {"total": {"file": "data/summary.json", "path": "total"},
                    "median": {"file": "data/summary.json", "path": "median", "fmt": "{:.0f}"},
                    "share": {"file": "data/items.csv", "where": {"kind": "A"}, "column": "share"}},
        "sources": {"items": {"A1": {"short": "資料A", "text": "資料A（2025）", "url": "https://example.org/a"}}},
        "claims": {"C1": {"text": "主張", "evidence": ["data/summary.json", "analysis.md#分析"]}},
        "figures": {"chart-001": {"type": "vbar", "title": "分布", "fmt": "{}人",
                                  "data": {"file": "data/summary.json", "path": "bins"}}},
        "datasets": [
            {"name": "items.csv", "kind": "csv", "file": "data/items.csv", "description": "項目", "origin": "本調査",
             "rights": {"status": "ok", "note": "本調査の集計"},
             "columns": {"kind": {"meaning": "種類"}, "value": {"meaning": "値", "unit": "件"},
                         "share": {"meaning": "割合", "unit": "%", "missing": "空欄は未集計"}}},
            {"name": "third.csv", "kind": "csv", "file": "data/third.csv", "origin": "第三者の論文",
             "rights": {"status": "unverified", "note": "再配布の条件を確認していない", "source_url": "https://example.org/t"},
             "columns": {}}],
        "delivery": {"name": "data.zip", "root": "demo-data"},
    }
    cfg.update(cfg_over)
    (pdir / "note").mkdir()
    (pdir / "note" / "config.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    private = tmp_path / "private"
    (private / "demo" / "note").mkdir(parents=True)
    (private / "demo" / "note" / "article.md").write_text(MANUSCRIPT, encoding="utf-8")
    monkeypatch.setattr(research, "PROJECTS", projects)
    return research.load("demo", private=private, out=tmp_path / "out"), pdir


def run_all(p):
    note.run_article(p)
    note.run_package(p)
    return note.run_check(p)


def test_generate_from_research_only(tmp_path, monkeypatch):
    p, pdir = make_project(tmp_path, monkeypatch)
    results = run_all(p)
    assert all(r["ok"] for r in results), [r for r in results if not r["ok"]]
    free = (p.out_dir / "article-free.md").read_text(encoding="utf-8")
    paid = (p.out_dir / "article-paid.md").read_text(encoding="utf-8")
    full = (p.out_dir / "article-full.md").read_text(encoding="utf-8")
    # 数値は研究資料の値と一致する
    assert "120件" in free and "33歳" in free and "12.5%" in paid
    # 無料・有料の分離
    assert PAID_SENTENCE not in free and PAID_SENTENCE in paid and PAID_SENTENCE in full
    assert "ここから有料" in full and "<!--" not in full
    # 未確定のリンクはプレースホルダーのまま
    assert "{{YOUTUBE_URL}}" in free
    assert (p.out_dir / "assets" / "chart-001.png").exists()
    checklist = (p.out_dir / "publication-checklist.md").read_text(encoding="utf-8")
    assert "試験生成" in checklist and "有料ラインの位置" in checklist and "data.zip" in checklist


def test_video_material_is_rejected(tmp_path, monkeypatch):
    p, _ = make_project(tmp_path, monkeypatch)
    with pytest.raises(research.NoteError):
        p.research_path("video/narration.md")
    p.config["numbers"]["bad"] = {"file": "video/narration.md", "path": "x"}
    with pytest.raises(research.NoteError):
        research.resolve_number(p, "bad")


def test_lint_finds_literal_numbers_and_tables():
    out = article.lint("対象は120人でした。{{n:x}}人は可。{{t:25歳以下}}は可。\n| a | b |\n")
    assert any("120人" in x for x in out)
    assert any("表" in x for x in out)
    assert len(out) == 2


def test_free_only_article(tmp_path, monkeypatch):
    p, _ = make_project(tmp_path, monkeypatch)
    p.private_path("article.md").write_text("# 無料だけ\n\n本文{{n:total}}件。\n", encoding="utf-8")
    r = article.build(p)
    assert set(r["files"]) == {"article-free.md", "article-full.md"}


def test_excluded_and_zip(tmp_path, monkeypatch):
    p, _ = make_project(tmp_path, monkeypatch)
    run_all(p)
    z = p.out_dir / "delivery" / "data.zip"
    with zipfile.ZipFile(z) as zf:
        assert zf.testzip() is None
        names = zf.namelist()
        assert "demo-data/data/items.csv" in names and not any("third" in n for n in names)
        assert all(i.date_time == (2000, 1, 1, 0, 0, 0) for i in zf.infolist())
    readme = (p.out_dir / "data" / "README.md").read_text(encoding="utf-8")
    assert "third.csv" in readme and "https://example.org/t" in readme
    m = json.loads((p.out_dir / "manifest.json").read_text())
    assert m["package"]["excluded"][0]["name"] == "third.csv"


def test_dictionary_mismatch_and_missing_values(tmp_path, monkeypatch):
    p, _ = make_project(tmp_path, monkeypatch)
    ds = p.config["datasets"][0]
    del ds["columns"]["share"]["missing"]
    ds["columns"]["extra"] = {"meaning": "余分"}
    ds["columns_order"] = ["kind", "value", "share"]
    note.run_article(p)
    r = note.run_package(p)
    assert any("一致しない" in x for x in r["problems"]) and any("欠損値" in x for x in r["problems"])


def test_attachment_size_limit(tmp_path, monkeypatch):
    p, _ = make_project(tmp_path, monkeypatch, max_attachment_mb=0.0001)
    results = run_all(p)
    assert not next(r for r in results if "MB 以下" in r["item"])["ok"]


def test_reproducible(tmp_path, monkeypatch):
    p, _ = make_project(tmp_path, monkeypatch)
    run_all(p)
    names = ["article-free.md", "article-paid.md", "article-full.md", "assets/chart-001.png",
             "data/items.csv", "data/README.md", "delivery/data.zip"]
    first = {n: research.sha1(p.out_dir / n) for n in names}
    run_all(p)
    assert first == {n: research.sha1(p.out_dir / n) for n in names}


def test_public_manifest_has_no_paid_text(tmp_path, monkeypatch):
    p, pdir = make_project(tmp_path, monkeypatch)
    run_all(p)
    pub = (pdir / "note" / "manifest.public.json").read_text(encoding="utf-8")
    data = json.loads(pub)
    assert PAID_SENTENCE[:15] not in pub
    assert data["mode"] == "trial" and data["research_version"] is None
    assert data["outputs"]["article-paid.md"]["visibility"] == "paid"
    assert data["outputs"]["article-free.md"]["visibility"] == "free"
    assert set(data["research_files"]) >= {"data/summary.json", "analysis.md"}


def test_production_requires_approved_version(tmp_path, monkeypatch):
    _, pdir = make_project(tmp_path, monkeypatch)
    cfg = json.loads((pdir / "note" / "config.json").read_text())
    for v in (None, "research-v2"):  # 未記録の版、版の指定なし
        cfg.update(mode="production", research_version=v)
        (pdir / "note" / "config.json").write_text(json.dumps(cfg, ensure_ascii=False))
        with pytest.raises(research.NoteError):
            research.load("demo", private=tmp_path / "private", out=tmp_path / "out")
    cfg["research_version"] = "research-v1"
    (pdir / "note" / "config.json").write_text(json.dumps(cfg, ensure_ascii=False))
    before = (pdir / "progress.md").read_text()
    p = research.load("demo", private=tmp_path / "private", out=tmp_path / "out")
    assert not p.trial
    run_all(p)
    assert (pdir / "progress.md").read_text() == before  # 生成は承認の記録を変えない


def test_repository_keeps_paid_material_out_of_git():
    assert note._ignored(REPO / "private" / "x" / "note" / "article.md")
    assert note._ignored(OUTPUT / "x" / "note" / "article-paid.md")


@pytest.mark.parametrize("slug", ["business-manners", "founders-elite"])
def test_existing_projects_trial(slug, tmp_path):
    """既存2プロジェクトの試験生成（原稿は Git 管理外のため、ない環境では飛ばす）"""
    if not (research.PRIVATE / slug / "note" / "article.md").exists():
        pytest.skip("原稿が Git 管理外の保存先にない")
    p = research.load(slug, out=tmp_path / "out")
    assert p.trial and p.config["research_version"] is None
    pub_path = p.project_dir / "note" / "manifest.public.json"
    saved = pub_path.read_text(encoding="utf-8") if pub_path.exists() else None
    try:
        results = run_all(p)
    finally:
        if saved is not None:  # テストで Git 管理の記録を書き換えない
            pub_path.write_text(saved, encoding="utf-8")
        else:
            pub_path.unlink(missing_ok=True)
    assert all(r["ok"] for r in results), [r for r in results if not r["ok"]]
