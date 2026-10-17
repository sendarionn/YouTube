"""Iの部PDFから企業情報と役員略歴を抽出する

出力: CACHE/part1_extract.jsonl（1社1行、確認前の機械抽出結果）
"""
import json
import re
import sys

import pandas as pd
import pymupdf

from paths import CACHE, DATA

pymupdf.TOOLS.mupdf_display_errors(False)

ZEN = str.maketrans("０１２３４５６７８９，", "0123456789,")
DATE = re.compile(r"(\d{4})年\s*(\d{1,2})月")
BIRTH = re.compile(r"^(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日")
FOUNDER = re.compile(r"当社(を)?(設立|創業)|当社創業|創業者|当社の前身")


def clean(s):
    return re.sub(r"[ 　]+", " ", (s or "").translate(ZEN)).strip()


ERA = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}


def seireki(text):
    """和暦の年を西暦に直す（「平成27年」→「2015年」、「同年」は変換しない）"""
    def rep(m):
        n = 1 if m.group(2) == "元" else int(m.group(2))
        return f"{ERA[m.group(1)] + n}年"
    return re.sub(r"(明治|大正|昭和|平成|令和)\s*(元|\d{1,2})\s*年", rep, text)


def page_texts(doc):
    return [seireki(p.get_text().translate(ZEN)) for p in doc]


def cover_field(text, label):
    m = re.search(rf"【{label}】\s*\n?(.+)(\n.+)?", text)
    if not m:
        return ""
    v = m.group(1) + ("" if m.group(2) is None or "【" in m.group(2) else m.group(2))
    return clean(v.replace("\n", " "))


def section(texts, heading, ends, pages=3):
    """目次を除いた見出しの位置から、終端語までのテキストを返す"""
    pat = re.compile(heading)
    for i, t in enumerate(texts):
        for m in pat.finditer(t):
            if "…" in t[m.end():m.end() + 30]:
                continue
            body = "\n".join([t[m.end():]] + texts[i + 1:i + pages])
            for e in ends:
                body = re.split(e, body)[0]
            # 表のテキストが見出しより前に出力される場合に備えて同ページの前半も返す
            return t[:m.start()], body, i + 1
    return "", "", 0


HIST_DATE = re.compile(r"(\d{4})年\s*(\d{1,2})月(?!\s*\d{1,2}日)")


def history(texts):
    """沿革の年月と概要を順に返す"""
    before, body, page = section(texts, r"【\s*沿\s*革\s*】", [r"【\s*事業の内容\s*】"])
    intro = clean(HIST_DATE.split(body)[0].replace("\n", ""))[:500] if body else ""
    items = []
    for text in (body, before):
        ms = list(HIST_DATE.finditer(text))
        for a, b in zip(ms, ms[1:] + [None]):
            seg = text[a.end():b.start() if b else len(text)]
            seg = clean(re.sub(r"\n|- \d+ -|― \d+ ―|=====PAGE \d+=====", "", seg))
            if seg and "当社" not in intro[:0]:
                items.append([f"{a.group(1)}-{int(a.group(2)):02d}", seg[:200]])
        if items:
            break
    return intro, items, page


BIRTH_LINE = re.compile(r"^\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*(生)?\s*$", re.M)


CAREER_LINE = re.compile(r"\d{4}年\s*\d{1,2}月|入社|入行|入所|入省|入職|就任|現任|設立|創業|退任|退社|転籍|出向|参画|修了|卒業|開業|開設|入局|入学|所長|理事")
TITLE_WORD = re.compile(r"取締役|監査|役|長|員|社|CEO|COO|CFO|CTO|会|委|兼|\(|（")


def officer_pages(texts):
    """「略歴」の見出しと生年月日の行を含む最初の連続ページ"""
    pages = []
    for i, t in enumerate(texts):
        has = BIRTH_LINE.search(t) and re.search(r"略\s*歴", t)
        if has or (pages and pages[-1] == i - 1 and BIRTH_LINE.search(t) and "当社" in t):
            pages.append(i)
        elif pages:
            break
    return pages


def split_name(lines):
    if not lines:
        return "", ""
    name = lines[-1]
    rest = lines[:-1]
    if rest and len(name) <= 4 and len(rest[-1]) <= 4 and not TITLE_WORD.search(rest[-1]):
        name = rest[-1] + " " + name
        rest = rest[:-1]
    return name, " ".join(rest)[-60:]


def officers(texts):
    pages = officer_pages(texts)
    body = "\n".join(texts[i] for i in pages)
    body = re.split(r"社外役員の状況|【\s*監査の状況\s*】", body)[0]
    body = re.sub(r"=====PAGE \d+=====|- \d+ -|― \d+ ―", "", body)
    ms = list(BIRTH_LINE.finditer(body))
    out = []
    for j, m in enumerate(ms):
        head = body[ms[j - 1].end() if j else 0:m.start()]
        if j:
            head = re.split(r"[（(]注[）)][^\n]*\n[^\n]*\n", head)[-1]
        else:
            head = re.split(r"所有株式数[^\n]*\n(（株）\n|\(株\)\n)?", head)[-1]
        lines = [l.strip() for l in head.strip().split("\n") if l.strip()]
        name, title = split_name(lines)
        end = ms[j + 1].start() if j + 1 < len(ms) else len(body)
        chunk = body[m.end():end]
        # 「(注)N」と所有株式数の行は略歴の途中に入る様式があるため、除いて続きを残す
        chunk = re.sub(r"[（(]注[）)]\s*\d*\s*\n?(\s*[\d,，－―\-]+\s*\n)?", "\n", chunk)
        # 末尾に付く次の役員の役職・氏名を除く（最後の経歴らしい行までを残す）
        lines = [l for l in chunk.split("\n") if l.strip()]
        last = max((i for i, l in enumerate(lines) if CAREER_LINE.search(l)), default=len(lines) - 1)
        chunk = clean("/".join(lines[:last + 1]))
        out.append({
            "title": clean(title),
            "name": clean(name),
            "birth": f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}",
            "career": chunk[:1500],
            "founder_flag": bool(FOUNDER.search(chunk.replace("/", ""))),
        })
    return out, (pages[0] + 1 if pages else 0)


def employees(texts):
    for t in texts:
        if "【従業員の状況】" in t and "…" not in t.split("【従業員の状況】")[1][:30]:
            body = t.split("【従業員の状況】", 1)[1]
            res = {}
            for label, part in (("consolidated", body.split("提出会社の状況")[0] if "連結会社の状況" in body else ""),
                                ("parent", body.split("提出会社の状況")[1] if "提出会社の状況" in body else body)):
                m = re.search(r"\n\s*(\d[\d,]*)\s*(?:\(|（|\n)", part)
                res[label] = m.group(1).replace(",", "") if m else ""
            return res
    return {}


def extract(key):
    pdf = CACHE / "pdf" / f"{key}.pdf"
    with pymupdf.open(pdf) as doc:
        texts = page_texts(doc)
        cover = "\n".join(texts[:3])
        intro, hist, hist_page = history(texts)
        offs, off_page = officers(texts)
        return {
            "key": key,
            "rep": cover_field(cover, "代表者の役職氏名"),
            "hq": cover_field(cover, "本店の所在の場所"),
            "history_intro": intro,
            "history": hist,
            "history_page": hist_page,
            "employees": employees(texts),
            "officers": offs,
            "officers_page": off_page,
        }


def main():
    done = {}
    out_path = CACHE / "part1_extract.jsonl"
    if out_path.exists():
        done = {json.loads(l)["key"]: l for l in open(out_path, encoding="utf-8")}
    keys = sorted(p.stem for p in (CACHE / "text").glob("*.txt"))
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    if only:
        keys = [k for k in keys if any(k.startswith(o) for o in only)]
    redo = "--redo" in sys.argv
    for k in keys:
        if k in done and not redo:
            continue
        try:
            rec = extract(k)
        except Exception as e:
            rec = {"key": k, "error": str(e)}
        done[k] = json.dumps(rec, ensure_ascii=False) + "\n"
        print(k, len(rec.get("officers", [])), sum(o["founder_flag"] for o in rec.get("officers", [])), flush=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(done[k] for k in sorted(done))


if __name__ == "__main__":
    main()
