"""配布資料（詳細レポート、整理済みデータとデータ辞書、出典一覧、販売用 ZIP）

配布してよいかは config の rights.status で判断する。"ok" 以外（未確認、要申請、個人情報など）は
ファイルの実体を配布せず、出典一覧に出典と理由だけを残す
"""
import csv
import io
import json
import zipfile
from pathlib import Path

from tools.infographic.config import find_font

from . import mdhtml
from .article import Renderer, render_figures, split
from .research import NoteError, _csv_rows, _json_at, sha1

ZIP_DATE = (2000, 1, 1, 0, 0, 0)  # ZIP 内の日時を固定し、同じ入力から同じ ZIP にする
CSS = """
@font-face{font-family:jp;src:url(BIZUDPGothic-Regular.ttf);}
@font-face{font-family:jp;font-weight:bold;src:url(BIZUDPGothic-Bold.ttf);}
body{font-family:jp;font-size:10pt;line-height:1.75;color:#1F2328}
h1{font-size:17pt} h2{font-size:13pt;margin-top:14pt} h3{font-size:11pt}
table{border-collapse:collapse;margin:6pt 0} td,th{border:0.5pt solid #8E98A3;padding:2pt 5pt;font-size:9pt}
figure{margin:8pt 0} img{width:100%} figcaption{font-size:8.5pt;color:#5B6470}
"""


# データ ---------------------------------------------------------------------

def dataset_rows(p, ds):
    """配布用の表（列名のリスト、行のリスト）"""
    kind = ds.get("kind", "csv")
    if kind == "csv":
        rows = _csv_rows(p.research_path(ds["file"]), ds.get("where"))
        cols = ds.get("columns_order") or list(ds["columns"])
        return cols, [[r[c] for c in cols] for r in rows]
    if kind == "json_long":
        cols = list(ds["columns"])
        out = []
        for t in ds["tables"]:
            data = _json_at(json.loads(p.research_path(t["file"]).read_text(encoding="utf-8")), t["path"])
            for k, v in data.items():
                out.append([t["name"], k, v, t["unit"], t.get("denominator", "")])
        return cols, out
    raise NoteError(f"未対応のデータの種類：{kind}")


def write_csv(path, cols, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    w.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue(), encoding="utf-8")


def data_readme(p, included, excluded):
    lines = ["# データ辞書", "",
             f"研究：{p.config['title']}", "文字コード UTF-8、区切りはカンマ、1行目は列名", ""]
    for ds, cols, rows in included:
        lines += [f"## {ds['name']}", "", ds["description"], "",
                  f"- 行数：{len(rows)}", f"- 元データ：{ds['origin']}",
                  f"- 利用条件：{ds['rights']['note']}", "",
                  "| 列 | 意味 | 単位 | 定義 | 欠損値 |", "| --- | --- | --- | --- | --- |"]
        for c in cols:
            d = ds["columns"][c]
            lines.append(f"| {c} | {d['meaning']} | {d.get('unit', '')} | {d.get('definition', '')} | "
                         f"{d.get('missing', 'なし')} |")
        lines.append("")
    if excluded:
        lines += ["## 配布していないデータ", "", "再配布の条件を確認できない、または個人情報を含むため、出典だけを示す", ""]
        for ds in excluded:
            lines.append(f"- {ds['name']}：{ds['rights']['note']}（{ds['rights'].get('source_url', '出典は sources.md')}）")
        lines.append("")
    return "\n".join(lines)


def check_dataset(cols, rows, ds):
    """データ辞書と表の対応（列の過不足、空欄の扱いの記載）"""
    problems = []
    if list(ds["columns"]) != cols:
        problems.append(f"{ds['name']}：データ辞書の列 {list(ds['columns'])} と表の列 {cols} が一致しない")
    for i, c in enumerate(cols):
        if any(str(r[i]) == "" for r in rows) and "missing" not in ds["columns"].get(c, {}):
            problems.append(f"{ds['name']}：列 {c} に空欄があるが、欠損値の扱いが辞書にない")
    return problems


# PDF ----------------------------------------------------------------------

def pdf(md, title, out, base_dir):
    import pymupdf

    font_dir = find_font("BIZUDPGothic-Regular.ttf").parent
    arch = pymupdf.Archive(str(font_dir))
    arch.add(str(base_dir))
    story = pymupdf.Story(mdhtml.convert(md), user_css=CSS, archive=arch)
    w = pymupdf.DocumentWriter(str(out))
    mb = pymupdf.paper_rect("a4")
    more = 1
    while more:
        dev = w.begin_page(mb)
        more, _ = story.place(mb + (56, 60, -56, -60))
        story.draw(dev)
        w.end_page()
    w.close()
    doc = pymupdf.open(str(out))
    doc.subset_fonts()  # 日本語フォントの全体を埋め込むと数十MBになるため、使った文字だけにする
    doc.set_metadata({"title": title, "creationDate": "D:20000101000000", "modDate": "D:20000101000000",
                      "producer": "tools/note", "creator": "tools/note"})
    doc.save(str(out) + ".tmp", garbage=4, deflate=True, deflate_fonts=True, no_new_id=True)
    doc.close()
    Path(str(out) + ".tmp").replace(out)
    return out


# 全体 ---------------------------------------------------------------------

def build(p, article_used=None):
    out = p.out_dir
    cfg = p.config
    result = {"files": {}, "excluded": [], "problems": [], "attachments": []}
    renderer = Renderer(p)

    # 詳細レポート
    report_md = None
    if cfg.get("report"):
        text = p.private_path(cfg["report"]).read_text(encoding="utf-8")
        title, body, paid = split(text)
        if paid:
            raise NoteError("詳細レポートに有料の境界は使わない（レポート全体が販売資料）")
        md, places = renderer.render(body, "report")
        render_figures(p, [x["id"] for x in places if x["kind"] == "図"], out)
        src = renderer.source_list("report")
        report_md = f"# {title}\n\n{md}\n" + (f"\n{src}\n" if src else "")
        (out / "report.md").write_text(report_md, encoding="utf-8")
        result["files"]["report.md"] = "delivery"
        if cfg.get("pdf"):
            pdf(report_md, title, out / "report.pdf", out)
            result["files"]["report.pdf"] = "delivery"

    # データ
    included, excluded = [], []
    for ds in cfg.get("datasets", []):
        if ds["rights"]["status"] != "ok":
            excluded.append(ds)
            continue
        cols, rows = dataset_rows(p, ds)
        result["problems"] += check_dataset(cols, rows, ds)
        write_csv(out / "data" / ds["name"], cols, rows)
        included.append((ds, cols, rows))
        result["files"][f"data/{ds['name']}"] = "delivery"
    if included or excluded:
        (out / "data" / "README.md").write_text(data_readme(p, included, excluded), encoding="utf-8")
        result["files"]["data/README.md"] = "delivery"
    result["excluded"] = [{"name": d["name"], "reason": d["rights"]["note"], "status": d["rights"]["status"]}
                          for d in excluded]

    # 出典一覧（記事・レポート・データの出典をまとめる）
    used = dict(article_used or {})
    used.update(renderer.used["sources"])
    sources = renderer.sources
    lines = ["# 出典一覧", ""]
    for sid in sorted(used, key=lambda s: [int(x) for x in s[1:].split("-")] if s[1:].replace("-", "").isdigit() else [999]):
        s = sources[sid]
        text = s["text"].replace(s.get("url", ""), "").strip() if s.get("url") else s["text"]
        lines.append(f"- {sid}：{text}" + (f" {s['url']}" if s.get("url") else ""))
    for ds in [d for d, _, _ in included] + excluded:
        lines.append(f"- データ {ds['name']}：{ds['origin']}" + (f" {ds['rights']['source_url']}" if ds['rights'].get('source_url') else ""))
    (out / "sources.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    result["files"]["sources.md"] = "delivery"

    # 販売用 ZIP
    zcfg = cfg.get("delivery")
    if zcfg:
        members = [f for f, v in result["files"].items() if v == "delivery"]
        if report_md:
            members += sorted(f"assets/{x}.png" for x in renderer.used["figures"])
        for extra in zcfg.get("code", []):
            if extra["rights"]["status"] != "ok":
                result["excluded"].append({"name": extra["file"], "reason": extra["rights"]["note"],
                                           "status": extra["rights"]["status"]})
                continue
            src = p.research_path(extra["file"])
            dst = out / "code" / Path(extra["file"]).name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            members.append(f"code/{dst.name}")
        readme = ["添付資料の一覧", "", f"{cfg['title']}", ""]
        readme += [f"- {m}：{zcfg.get('descriptions', {}).get(m, _describe(m))}" for m in members]
        readme += ["", "利用条件は data/README.md と sources.md を参照"]
        zpath = out / "delivery" / zcfg["name"]
        zpath.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in [("README.txt", "\n".join(readme).encode())] + [(m, (out / m).read_bytes()) for m in members]:
                info = zipfile.ZipInfo(f"{zcfg['root']}/{name}", ZIP_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, data)
        result["files"][f"delivery/{zcfg['name']}"] = "attachment"
        result["zip_members"] = ["README.txt"] + members
    for f, kind in result["files"].items():
        if kind == "attachment":
            size = (out / f).stat().st_size
            result["attachments"].append({"file": f, "bytes": size, "sha1": sha1(out / f)})
    result["used"] = renderer.used
    return result


def _describe(m):
    if m.startswith("data/") and m.endswith(".csv"):
        return "整理済みデータ（列の定義は data/README.md）"
    return {"report.md": "詳細分析レポート（Markdown）", "report.pdf": "詳細分析レポート（PDF）",
            "data/README.md": "データ辞書（列の意味・単位・定義・欠損値）", "sources.md": "出典一覧"}.get(
        m, "図表" if m.startswith("assets/") else "分析コード" if m.startswith("code/") else "")
