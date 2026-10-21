"""note 記事と販売資料の生成（AGENTS.md「note 記事の制作」）

承認済みの研究資料から作り、YouTube の台本・動画は使わない
  article：原稿から記事（無料・有料・確認用）、貼り付け用 HTML、図表を出力する
  package：詳細レポート、整理済みデータとデータ辞書、出典一覧、販売用 ZIP を出力する
  check  ：品質確認を行い、publication-checklist.md と manifest を書く
note への投稿、価格の設定、販売の開始はしない
"""
import json
import subprocess
import zipfile
from datetime import date

from tools.infographic.config import REPO

from . import article as art
from . import mdhtml
from . import package as pkg
from .research import NoteError, check_claims, load, sha1  # noqa: F401

DEFAULT_LIMIT_MB = 50  # note の添付ファイルの上限（1ファイル）。config の max_attachment_mb で変更する
HTML_CSS = "body{font-family:sans-serif;max-width:720px;margin:2em auto;line-height:1.8} img{max-width:100%}"


def _manifest_path(p):
    return p.out_dir / "manifest.json"


def _read_manifest(p):
    path = _manifest_path(p)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _write_manifest(p, m):
    p.out_dir.mkdir(parents=True, exist_ok=True)
    _manifest_path(p).write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")


def run_article(p):
    r = art.build(p)
    out = p.out_dir
    out.mkdir(parents=True, exist_ok=True)
    for old in ("article-free.md", "article-paid.md", "article-full.md", "article-free.html", "article-paid.html"):
        (out / old).unlink(missing_ok=True)
    for name, text in r["files"].items():
        (out / name).write_text(text, encoding="utf-8")
        if name != "article-full.md":
            (out / name.replace(".md", ".html")).write_text(mdhtml.page(r["title"], text, HTML_CSS), encoding="utf-8")
    art.render_figures(p, list(r["used"]["figures"]), out)
    m = _read_manifest(p)
    m["article"] = {"title": r["title"], "files": sorted(r["files"]), "places": r["places"], "used": r["used"],
                    "lint": r["lint"], "free_last_paragraph": r["free_last_paragraph"],
                    "manuscript_sha1": sha1(p.private_path("article.md"))}
    _write_manifest(p, m)
    return r


def run_package(p):
    m = _read_manifest(p)
    used_sources = m.get("article", {}).get("used", {}).get("sources", {})
    r = pkg.build(p, used_sources)
    m["package"] = {k: r[k] for k in ("files", "excluded", "problems", "attachments")}
    m["package"]["zip_members"] = r.get("zip_members", [])
    m["package"]["report_used"] = r["used"]
    if p.config.get("report"):
        m["package"]["report_sha1"] = sha1(p.private_path(p.config["report"]))
    _write_manifest(p, m)
    return r


# 品質確認 ------------------------------------------------------------------

def _paragraphs(md):
    return [b.strip() for b in md.split("\n\n") if len(b.strip()) >= 20 and not b.strip().startswith("#")]


def _git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def _ignored(path):
    try:
        path.resolve().relative_to(REPO)
    except ValueError:
        return True  # リポジトリの外は Git の対象外
    return _git("check-ignore", "-q", str(path)).returncode == 0


def run_check(p):
    m = _read_manifest(p)
    if "article" not in m:
        raise NoteError("先に article を実行する")
    out = p.out_dir
    a, k = m["article"], m.get("package", {})
    results = []

    def item(name, ok, detail=""):
        results.append({"item": name, "ok": bool(ok), "detail": detail})

    item("研究資料だけを情報源にしている（video/ を参照しない、根拠ファイルが実在する）", not check_claims(p),
         "；".join(check_claims(p)))
    item("原稿の数値・表の注意点がない", not a["lint"], "；".join(a["lint"][:5]))
    free = (out / "article-free.md").read_text(encoding="utf-8")
    paid_path = out / "article-paid.md"
    if paid_path.exists():
        paid = paid_path.read_text(encoding="utf-8")
        leaked = [x for x in _paragraphs(paid) if x in free and not x.startswith("- ")]
        item("無料部分に有料部分の文章が含まれない", not leaked, "；".join(x[:30] for x in leaked))
        full = (out / "article-full.md").read_text(encoding="utf-8")
        item("確認用原稿に無料・有料の両方と境界がある", "ここから有料" in full and paid.strip()[:40] in full)
        tracked = _git("ls-files", "-z", "--", str(p.project_dir)).stdout.split("\0")
        hits = []
        for f in filter(None, tracked):
            text = (REPO / f).read_text(encoding="utf-8", errors="ignore") if (REPO / f).exists() else ""
            hits += [f"{f}：{x[:20]}" for x in _paragraphs(paid) if x in text]
        item("有料部分の文章が Git 管理のファイルに含まれない", not hits, "；".join(hits[:3]))
    item("出力先と原稿の保存先が Git 管理外", _ignored(out) and _ignored(p.private_dir), f"{out}、{p.private_dir}")
    missing = [f for f in [*a["files"], *(x["file"] for x in a["places"] if x["kind"] == "図")] if not (out / f).exists()]
    item("記事と図表のファイルがそろっている", not missing, "、".join(missing))
    if k:
        item("データ辞書と CSV の列・欠損値の記載が一致する", not k["problems"], "；".join(k["problems"]))
        zips = [x for x in k["attachments"] if x["file"].endswith(".zip")]
        for z in zips:
            path = out / z["file"]
            with zipfile.ZipFile(path) as zf:
                bad = zf.testzip()
                names = [n.split("/", 1)[1] for n in zf.namelist()]
                same = all(zf.read(f"{zf.namelist()[0].split('/')[0]}/{n}") == (out / n).read_bytes()
                           for n in names if n != "README.txt")
            item(f"ZIP を展開でき、中身が出力と一致する（{z['file']}）", bad is None and same, f"{len(names)} ファイル")
            leaked = [e["name"] for e in k["excluded"] if any(n.endswith(e["name"]) for n in names)]
            item("配布しないデータ・素材が ZIP に含まれない", not leaked, "、".join(leaked))
        limit = p.config.get("max_attachment_mb", DEFAULT_LIMIT_MB)
        over = [f"{x['file']}（{x['bytes'] / 1e6:.1f}MB）" for x in k["attachments"] if x["bytes"] > limit * 1e6]
        item(f"添付ファイルが1ファイル {limit}MB 以下", not over, "、".join(over))
    item("研究版と生成物の対応を記録している", True,
         p.config.get("research_version") or "研究版の承認なし（試験生成）")
    m["check"] = results
    m["mode"] = "trial" if p.trial else "production"
    m["research_version"] = p.config.get("research_version")
    _write_manifest(p, m)
    (out / "publication-checklist.md").write_text(checklist(p, m), encoding="utf-8")
    write_public_manifest(p, m)
    return results


def checklist(p, m):
    a, k = m["article"], m.get("package", {})
    lines = [f"# 公開前の確認：{a['title']}", ""]
    if p.trial:
        lines += ["**試験生成**：研究版の承認がないため公開・販売に使わない。この生成は研究の承認を意味しない", ""]
    else:
        lines += [f"研究版：{p.config['research_version']}", ""]
    lines += ["## 転載の手順", "",
              "1. note で新しいテキスト記事を作り、タイトルに記事のタイトルを入れる",
              "2. `article-free.html` をブラウザで開き、本文を全選択してコピーし、note の本文に貼り付ける",
              "   - Markdown（.md）をそのまま貼ると記号が文字として残るため、HTML から貼る",
              "   - 見出し・強調・リンク・箇条書きが保たれているか確認し、崩れた箇所は note の編集画面で直す",
              "3. 「図表の挿入位置」の各位置に、`assets/` の画像を note の画像挿入から入れる（貼り付けた HTML の画像は取り込まれないことがある）"]
    if (p.out_dir / "article-paid.md").exists():
        lines += ["4. 無料部分の最後に続けて `article-paid.html` の本文を貼り付ける",
                  "5. 公開設定で「有料」を選び、価格を決め、有料エリアの開始位置を下の「有料ラインの位置」に合わせる",
                  "   - 原稿の境界の記号は note の有料ラインに自動では変換されない。必ず note の画面で設定する",
                  "6. 添付ファイルを「添付ファイル」の位置（有料ラインより後）に挿入する"]
    lines += ["", "## 図表の挿入位置", ""]
    for x in a["places"]:
        if x["kind"] == "図":
            lines.append(f"- {'無料' if x['section'] == 'free' else '有料'}部分、見出し「{x['after_heading']}」の中："
                         f"`{x['file']}`（{x['caption']}）")
    if a.get("free_last_paragraph"):
        lines += ["", "## 有料ラインの位置", "", "無料部分の最後の段落の直後（この段落までが無料）", "",
                  "> " + a["free_last_paragraph"].replace("\n", " ")[:120]]
    lines += ["", "## 添付ファイル", ""]
    places = {x["id"]: x for x in a["places"] if x["kind"] == "添付"}
    for x in k.get("attachments", []):
        name = x["file"].split("/")[-1]
        pl = places.get(name)
        where = f"有料部分、見出し「{pl['after_heading']}」の中（［添付ファイル：{name}］の位置）" if pl else "位置の指定なし"
        lines.append(f"- `{x['file']}`：{x['bytes'] / 1e6:.2f}MB。{where}")
    if not k.get("attachments"):
        lines.append("- なし")
    if k.get("excluded"):
        lines += ["", "配布しないもの（出典のリンクだけ残す）", ""]
        lines += [f"- {e['name']}：{e['reason']}" for e in k["excluded"]]
    links = a["used"]["links"]
    lines += ["", "## 相互リンク", ""]
    lines += [f"- `{{{{{key}}}}}`：{url or '未確定。公開して URL が確定したら config.json の links に書いて article を再実行する'}"
              for key, url in links.items()] or ["- なし"]
    lines += ["", "## 自動確認の結果", ""]
    lines += [f"- [{'x' if r['ok'] else ' '}] {r['item']}" + (f"：{r['detail']}" if r["detail"] and not r["ok"] else "")
              for r in m["check"]]
    lines += ["", "## 手動で確認すること（未確認）", "",
              "- [ ] note の編集画面で見出し・段落・リンク・箇条書きが崩れていない",
              "- [ ] 図表がスマートフォンの表示で読める",
              "- [ ] 有料ラインが「有料ラインの位置」にあり、プレビューで無料部分だけが見える",
              "- [ ] 添付ファイルがアップロードでき、購入後にダウンロードして展開できる",
              "- [ ] 価格と無料・有料の区分（ユーザーが決める）",
              "- [ ] 相互リンクのプレースホルダーが残っていない",
              "- [ ] 公開・販売開始の許可（ユーザーの明示的な指示）", ""]
    return "\n".join(lines)


def write_public_manifest(p, m):
    """Git 管理する公開用の記録（本文・データは含めず、対応関係とハッシュだけ）"""
    files = sorted(set(m["article"]["files"]) | set(m.get("package", {}).get("files", {}))
                   | {x["file"] for x in m["article"]["places"] if x["kind"] == "図"})
    research_files = sorted({spec["file"] for spec in p.config.get("numbers", {}).values() if "file" in spec}
                            | {ev.split("#")[0] for c in p.config.get("claims", {}).values() for ev in c["evidence"]})
    pub = {
        "title": m["article"]["title"],
        "mode": m["mode"],
        "research_version": m["research_version"],
        "research_commit": _git("rev-parse", "HEAD").stdout.strip(),
        "research_files": {f: sha1(p.research_path(f)) for f in research_files},
        "config_sha1": sha1(p.project_dir / "note" / "config.json"),
        "manuscript_sha1": m["article"]["manuscript_sha1"],
        "outputs": {f: {"visibility": _visibility(f, m), "sha1": sha1(p.out_dir / f)} for f in files
                    if (p.out_dir / f).exists()},
        "claims": m["article"]["used"]["claims"],
        "numbers": m["article"]["used"]["numbers"],
        "sources": sorted(set(m["article"]["used"]["sources"]) | set(m.get("package", {}).get("report_used", {}).get("sources", {}))),
        "excluded": m.get("package", {}).get("excluded", []),
        "check": {r["item"]: r["ok"] for r in m["check"]},
        "generated": date.today().isoformat(),
    }
    path = p.project_dir / "note" / "manifest.public.json"
    path.write_text(json.dumps(pub, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return pub


def _visibility(f, m):
    free = {x["file"] for x in m["article"]["places"] if x["kind"] == "図" and x["section"] == "free"}
    return "free" if f.startswith("article-free") or f in free else "paid"
