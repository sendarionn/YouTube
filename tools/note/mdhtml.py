"""原稿で使う範囲の Markdown を HTML にする（見出し、段落、箇条書き、引用、画像、表、強調、リンク）

note への貼り付け用 HTML と、PDF の詳細レポートに使う。外部ライブラリに依存しない
"""
import html
import re

INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"`(.+?)`"), r"<code>\1</code>"),
    (re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)"), r'<a href="\2">\1</a>'),
    (re.compile(r"(?<![\"'>=])(https?://[^\s<）)]+)"), r'<a href="\1">\1</a>'),
]


def inline(s):
    s = html.escape(s, quote=False)
    for pat, rep in INLINE:
        s = pat.sub(rep, s)
    return s


def convert(md):
    out, para, lst, table = [], [], None, []

    def flush():
        nonlocal para, lst, table
        if para:
            out.append("<p>" + "<br>".join(inline(x) for x in para) + "</p>")
            para = []
        if lst:
            tag, items = lst
            out.append(f"<{tag}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{tag}>")
            lst = None
        if table:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table
                    if not re.fullmatch(r"\|?[\s:|-]+\|?", r.strip())]
            head, body = rows[0], rows[1:]
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
                       + "</tbody></table>")
            table = []

    for line in md.splitlines():
        s = line.rstrip()
        if not s.strip():
            flush()
            continue
        if s.startswith("|"):
            if para or lst:
                flush()
            table.append(s)
            continue
        if table:
            flush()
        m = re.match(r"(#{1,4})\s+(.*)", s)
        if m:
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
            continue
        m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)$", s.strip())
        if m:
            flush()
            out.append(f'<figure><img src="{html.escape(m.group(2))}" alt="{html.escape(m.group(1))}">'
                       f"<figcaption>{inline(m.group(1))}</figcaption></figure>")
            continue
        m = re.match(r"\s*([-*]|\d+\.)\s+(.*)", s)
        if m:
            tag = "ol" if m.group(1)[0].isdigit() else "ul"
            if para:
                flush()
            if lst and lst[0] != tag:
                flush()
            lst = lst or (tag, [])
            lst[1].append(m.group(2))
            continue
        if s.startswith(">"):
            flush()
            out.append(f"<blockquote>{inline(s.lstrip('> '))}</blockquote>")
            continue
        if lst:
            flush()
        para.append(s.strip())
    flush()
    return "\n".join(out)


def page(title, body_md, css=""):
    return (f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f"<style>{css}</style></head><body>\n{convert(body_md)}\n</body></html>\n")
