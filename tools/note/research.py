"""研究資料（SSoT）と設定の読み込み

設定：projects/<slug>/note/config.json（Git 管理。公開してよい内容だけ）
原稿：<NOTE_PRIVATE_DIR>/<slug>/note/（Git 管理外。有料部分を含むため）
数値・出典・主張・図表のデータは、すべて研究資料のファイルから読む。YouTube の台本（video/）は参照しない
"""
import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from tools.infographic.config import OUTPUT, REPO

PROJECTS = REPO / "projects"
PRIVATE = Path(os.environ.get("NOTE_PRIVATE_DIR", REPO / "private"))
FORBIDDEN_PARTS = {"video"}  # 媒体向けの成果物（YouTube）から記事を作らない


class NoteError(Exception):
    pass


def sha1(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


@dataclass
class Project:
    slug: str
    config: dict
    project_dir: Path
    research_dir: Path
    private_dir: Path
    out_dir: Path

    @property
    def trial(self):
        return self.config.get("mode", "trial") != "production"

    def research_path(self, rel):
        """研究資料のパス。研究資料の外や video/ を指すものは拒否する"""
        p = (self.research_dir / rel).resolve()
        root = self.research_dir.resolve()
        if root not in p.parents and p != root:
            raise NoteError(f"研究資料の外を参照している：{rel}")
        if FORBIDDEN_PARTS & set(p.relative_to(root).parts):
            raise NoteError(f"YouTube 向けの成果物は情報源にできない：{rel}")
        if not p.exists():
            raise NoteError(f"研究資料が見つからない：{rel}")
        return p

    def private_path(self, name):
        p = self.private_dir / name
        if not p.exists():
            raise NoteError(f"原稿が見つからない：{p}（Git 管理外の保存先。NOTE_PRIVATE_DIR）")
        return p


def load(slug, private=None, out=None):
    project_dir = PROJECTS / slug
    cfg_path = project_dir / "note" / "config.json"
    if not cfg_path.exists():
        raise NoteError(f"設定がない：{cfg_path}")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    p = Project(slug, cfg, project_dir, project_dir / cfg.get("research_root", "research"),
                Path(private or PRIVATE) / slug / "note", Path(out or OUTPUT) / slug / "note")
    check_approval(p)
    return p


def approved_versions(project_dir):
    """progress.md の「研究版」表に記録された版"""
    path = project_dir / "progress.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^## 研究版\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    rows = [r for r in m.group(1).splitlines() if r.startswith("|") and not set(r) <= set("|- ")]
    return [r.split("|")[1].strip() for r in rows[1:] if r.split("|")[1].strip()]


def check_approval(p):
    """本制作（production）は、progress.md に承認済みの研究版がある場合だけ実行できる

    試験生成（trial）は承認を必要としないが、研究版の承認とはみなさない（progress.md は変更しない）
    """
    mode = p.config.get("mode", "trial")
    if mode not in ("trial", "production"):
        raise NoteError(f"mode は trial か production：{mode}")
    if mode == "production":
        v = p.config.get("research_version")
        if not v or v not in approved_versions(p.project_dir):
            raise NoteError(f"研究版 {v} の承認が progress.md に記録されていない。本制作はできない（試験生成は mode=trial）")


# 数値 ---------------------------------------------------------------------

def _json_at(data, path):
    keys = path if isinstance(path, list) else str(path).split(".")
    for k in keys:
        data = data[k]
    return data


def _csv_rows(path, where=None):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for k, v in (where or {}).items():
        if isinstance(v, list):  # [下限, 上限]（両端を含む数値の範囲）
            rows = [r for r in rows if v[0] <= float(r[k]) <= v[1]]
        else:
            rows = [r for r in rows if r[k] == str(v)]
    return rows


def _num(s):
    x = float(s)
    return int(x) if x.is_integer() else x


def resolve_number(p, key):
    spec = p.config.get("numbers", {}).get(key)
    if spec is None:
        raise NoteError(f"数値 {key} が config の numbers にない")
    if "expr" in spec:
        # 他の数値から計算する値（例 "jfc_age - age_mean"）。使えるのは数値のキー、数、四則演算と括弧だけ
        v = _eval(spec["expr"], lambda k: resolve_number(p, k)[1])
        return spec.get("fmt", "{}").format(v), v
    path = p.research_path(spec["file"])
    if path.suffix == ".json":
        v = _json_at(json.loads(path.read_text(encoding="utf-8")), spec["path"])
    else:
        rows = _csv_rows(path, spec.get("where"))
        if "sum" in spec:
            v = sum(_num(r[spec["sum"]]) for r in rows)
        elif "count" in spec:
            v = len(rows)
        else:
            if len(rows) != 1:
                raise NoteError(f"数値 {key}：条件に合う行が {len(rows)} 行（1行にする）")
            v = _num(rows[0][spec["column"]])
    return spec.get("fmt", "{}").format(v), v


def _eval(expr, lookup):
    import ast
    import operator

    ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.Name):
            return lookup(n.id)
        raise NoteError(f"計算式に使えない要素：{expr}")

    return ev(ast.parse(expr, mode="eval"))


# 出典 ---------------------------------------------------------------------

def load_sources(p):
    """出典の一覧 {ID: {short, text, url}}

    研究資料の出典表（sources.file の Markdown 表、1列目がID・2列目が資料）と、config の sources.items を合わせる
    """
    scfg = p.config.get("sources", {})
    out = {}
    if scfg.get("file"):
        for line in p.research_path(scfg["file"]).read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if line.startswith("|") and len(cells) >= 2 and re.fullmatch(r"S\d+(-\d+)?", cells[0]):
                url = re.search(r"https?://\S+", line)
                text = cells[1] if not re.fullmatch(r"S10-\d+", cells[0]) else "、".join(cells[1:5])
                out[cells[0]] = {"text": text, "url": url.group(0) if url else ""}
    for sid, item in scfg.get("items", {}).items():
        out[sid] = {**out.get(sid, {}), **item}
    for sid, short in scfg.get("short", {}).items():
        if sid not in out:
            raise NoteError(f"出典 {sid} が研究資料の出典表にない")
        out[sid]["short"] = short
    return out


def check_claims(p):
    """主張と根拠の対応表（config の claims）の根拠ファイルが研究資料に実在するか"""
    problems = []
    for cid, c in p.config.get("claims", {}).items():
        for ev in c.get("evidence", []):
            try:
                p.research_path(ev.split("#")[0])
            except NoteError as e:
                problems.append(f"{cid}：{e}")
    return problems
