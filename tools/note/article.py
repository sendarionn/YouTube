"""原稿から記事（無料・有料・確認用）を組み立てる

原稿（Markdown）で使える記法
  {{n:キー}}       数値（config の numbers。研究資料のファイルから読む）
  {{s:ID}}         出典の短い表記（「（髙橋ほか 2018）」）。記事末尾の出典一覧に加える
  {{fig:ID}}       図表（config の figures。研究資料のデータから描く）
  {{t:文字}}       定義や区分の境界として書く数値（「25歳以下」など）。集計値ではないことを示し、そのまま出力する
  {{link:名前}}    相互リンクなどの URL（config の links。未確定ならプレースホルダーのまま残す）
  {{attach:名前}}  添付ファイルの配置位置（package で作るファイル）
  <!--C:ID-->      直前の文の根拠（config の claims）。出力では消える
  <!-- paid -->    ここから有料部分（1回だけ）

原稿は一度書いたら保存し、再出力では書き直さない（同じ原稿と研究資料からは同じ記事になる）
"""
import re

from . import charts
from .research import NoteError, load_sources, resolve_number

PAID = "<!-- paid -->"
TOKEN = re.compile(r"\{\{(n|s|t|fig|link|attach):([^}]+)\}\}")
CLAIM = re.compile(r"<!--C:([\w-]+)-->")
# 研究資料から引かずに直接書いた数値（単位つき）を見つける
LITERAL_NUMBER = re.compile(r"(?<![\d.,])\d[\d,.]*\s*(%|％|人|歳|冊|点|社|件|倍)")


def split(text):
    """(タイトル, 無料部分, 有料部分 or None)"""
    if text.count(PAID) > 1:
        raise NoteError("有料部分の境界（<!-- paid -->）が複数ある")
    m = re.match(r"#\s+(.+)\n", text)
    if not m:
        raise NoteError("原稿の1行目は「# タイトル」にする")
    body = text[m.end():]
    if PAID in body:
        free, paid = body.split(PAID)
        return m.group(1).strip(), free.strip(), paid.strip() or None
    return m.group(1).strip(), body.strip(), None


def lint(text):
    """原稿の注意点（数値の直書き、note が対応しない表）"""
    out = []
    plain = CLAIM.sub("", TOKEN.sub("", text))
    for line in plain.splitlines():
        if line.lstrip().startswith("|"):
            out.append(f"表は note の本文で使えない（図にする）：{line[:40]}")
        for m in LITERAL_NUMBER.finditer(line):
            out.append(f"数値を直接書いている（{{{{n:}}}} で研究資料から引く）：{m.group(0)}")
    return out


class Renderer:
    def __init__(self, p):
        self.p = p
        self.sources = load_sources(p)
        self.used = {"numbers": {}, "sources": {}, "figures": {}, "claims": {}, "links": {}, "attachments": {}}

    def render(self, text, section):
        """記法を展開した Markdown と、図・添付の挿入位置を返す"""
        claims = self.p.config.get("claims", {})
        for cid in CLAIM.findall(text):
            if cid not in claims:
                raise NoteError(f"主張 {cid} が config の claims にない")
            self.used["claims"].setdefault(cid, section)
        text = CLAIM.sub("", text)
        places = []
        heading = "（冒頭）"
        out_lines = []
        for line in text.splitlines():
            if line.startswith("#"):
                line = TOKEN.sub(lambda m: self._token(m, section, heading, places), line)
                heading = line.lstrip("# ").strip()
            out_lines.append(TOKEN.sub(lambda m: self._token(m, section, heading, places), line))
        return re.sub(r"[ \t]+\n", "\n", "\n".join(out_lines)), places

    def _token(self, m, section, heading, places):
        kind, key = m.group(1), m.group(2).strip()
        if kind == "n":
            s, v = resolve_number(self.p, key)
            self.used["numbers"].setdefault(key, section)
            return s
        if kind == "t":
            return m.group(2)
        if kind == "s":
            ids = [k.strip() for k in key.split(",")]
            for sid in ids:
                if sid not in self.sources or "short" not in self.sources[sid]:
                    raise NoteError(f"出典 {sid} の短い表記が config の sources.short にない")
                self.used["sources"].setdefault(sid, section)
            return "（" + "、".join(self.sources[s]["short"] for s in ids) + "）"
        if kind == "fig":
            spec = self.p.config.get("figures", {}).get(key)
            if spec is None:
                raise NoteError(f"図 {key} が config の figures にない")
            self.used["figures"].setdefault(key, section)
            places.append({"kind": "図", "id": key, "file": f"assets/{key}.png", "section": section,
                           "after_heading": heading, "caption": spec.get("caption", spec["title"])})
            return f"![{spec.get('caption', spec['title'])}](assets/{key}.png)"
        if kind == "link":
            url = self.p.config.get("links", {}).get(key)
            self.used["links"][key] = url
            return url or "{{" + key + "}}"
        if kind == "attach":
            self.used["attachments"].setdefault(key, section)
            places.append({"kind": "添付", "id": key, "section": section, "after_heading": heading})
            return f"［添付ファイル：{key}］"
        raise NoteError(m.group(0))

    def source_list(self, section):
        ids = [s for s, sec in self.used["sources"].items() if sec == section]
        if not ids:
            return ""
        lines = ["## 出典", ""]
        for sid in ids:
            s = self.sources[sid]
            text = s["text"].replace(s.get("url", ""), "").strip() if s.get("url") else s["text"]
            lines.append(f"- {text}" + (f" {s['url']}" if s.get("url") else ""))
        return "\n".join(lines)


def build(p, manuscript="article.md"):
    """記事を組み立てる。戻り値：{ファイル名: 本文}、挿入位置、使った数値・出典・主張など"""
    text = p.private_path(manuscript).read_text(encoding="utf-8")
    title, free, paid = split(text)
    r = Renderer(p)
    free_md, free_places = r.render(free, "free")
    files = {}
    free_src = r.source_list("free")
    files["article-free.md"] = f"# {title}\n\n{free_md}\n" + (f"\n{free_src}\n" if free_src else "")
    places = free_places
    if paid:
        paid_md, paid_places = r.render(paid, "paid")
        paid_src = r.source_list("paid")
        files["article-paid.md"] = f"{paid_md}\n" + (f"\n{paid_src}\n" if paid_src else "")
        places += paid_places
        files["article-full.md"] = (f"# {title}\n\n{free_md}\n" + (f"\n{free_src}\n" if free_src else "")
                                    + "\n――――――――　ここから有料（note の有料ライン）　――――――――\n\n"
                                    + files["article-paid.md"])
    else:
        files["article-full.md"] = files["article-free.md"]
    return {"title": title, "files": files, "places": places, "used": r.used, "lint": lint(text),
            "free_last_paragraph": _last_paragraph(free_md) if paid else None}


def _last_paragraph(md):
    paras = [b.strip() for b in md.split("\n\n") if b.strip() and not b.lstrip().startswith(("#", "!["))]
    return paras[-1] if paras else ""


def render_figures(p, ids, out_dir):
    figs = p.config.get("figures", {})
    return {fid: charts.render(p, fid, figs[fid], out_dir / "assets" / f"{fid}.png") for fid in ids}
