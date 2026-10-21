"""記事の図表（静止画）。研究資料のデータから描き、同じ入力からは同じ画像になる

描画は動画と同じ共通部品（tools/infographic/canvas.py）を使い、配色・フォント・描画品質を DESIGN.md にそろえる
記事の画像はスマートフォンで縮小表示されるため、文字は動画より大きくする
"""
import json
import math

from tools.infographic.canvas import Canvas, Theme, hbars, vbars

from .research import NoteError, _csv_rows, _json_at, _num

THEME = Theme(width=1600, height=1000, margin=100, size_title=60, size_body=44, size_number=96, size_note=30)


def series(p, data):
    """図のデータ（ラベルと値の列）を研究資料から読む"""
    path = p.research_path(data["file"])
    if path.suffix == ".json":
        d = _json_at(json.loads(path.read_text(encoding="utf-8")), data["path"])
        items = list(d.items())
    else:
        rows = _csv_rows(path, data.get("where"))
        items = [(r[data["label"]], _num(r[data["value"]])) for r in rows]
    if data.get("order"):
        m = dict(items)
        items = [(k, m[k]) for k in data["order"]]
    if data.get("labels"):
        items = [(data["labels"].get(k, k), v) for k, v in items]
    return [k for k, _ in items], [v for _, v in items]


def _line(cv, box, xs, ys_list, colors, names, fmt):
    th = cv.th
    x0, y0, x1, y1 = box
    ymax = max(max(ys) for ys in ys_list) * 1.1
    xmin, xmax = min(xs), max(xs)

    def X(x):
        return x0 + (x1 - x0) * (x - xmin) / (xmax - xmin)

    def Y(y):
        return y1 - (y1 - y0) * y / ymax

    # 縦軸の目盛り（0から、きりのよい間隔で3〜5本）
    raw = ymax / 4
    mag = 10 ** math.floor(math.log10(raw))
    ystep = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
    v = ystep
    while v < ymax:
        cv.line([(x0, Y(v)), (x1, Y(v))], th.grid, 1)
        cv.text((x0 - 14, Y(v)), fmt.format(v), th.size_note - 4, color=th.sub, anchor="rm")
        v += ystep
    cv.line([(x0, y1), (x1, y1)], th.grid, 3)
    step = 10 if xmax - xmin > 30 else 5
    for x in range(int(xmin + (-xmin) % step), int(xmax) + 1, step):
        cv.text((X(x), y1 + 16), str(x), th.size_note, color=th.sub, anchor="ma")
    for ys, c, name in zip(ys_list, colors, names):
        pts = [(X(x), Y(y)) for x, y in zip(xs, ys)]
        cv.line(pts, c, 5)
        k = max(range(len(ys)), key=lambda i: ys[i])
        cv.text((pts[k][0], pts[k][1] - 16), f"{name} {fmt.format(ys[k])}", th.size_note + 2, bold=True, color=c,
                anchor="md")


def render(p, fid, spec, path):
    th = THEME
    cv = Canvas(th)
    cv.title(spec["title"])
    note_y = th.height - 70
    box = (th.margin, 200, th.width - th.margin, note_y - 50)
    kind = spec["type"]
    fmt = spec.get("fmt", "{:,}")
    if kind in ("hbar", "vbar"):
        labels, values = series(p, spec["data"])
        if kind == "hbar":
            hbars(cv, box, labels, values, color=th.accent, fmt=fmt, label_w=spec.get("label_w", 420),
                  size=th.size_body - 4, vmax=spec.get("vmax"))
        else:
            vbars(cv, box, labels, values, color=th.accent, fmt=fmt, vmax=spec.get("vmax"),
                  highlight=spec.get("highlight"), value_size=th.size_body - 4)
    elif kind == "line":
        names, colors, ys_list, xs = [], [th.accent, th.compare, th.text], [], None
        for s in spec["series"]:
            labels, values = series(p, s)
            x = [_num(v) for v in labels]
            if spec.get("x_range"):
                a, b = spec["x_range"]
                pairs = [(xx, yy) for xx, yy in zip(x, values) if a <= xx <= b]
                x, values = [q[0] for q in pairs], [q[1] for q in pairs]
            if xs is not None and xs != x:
                raise NoteError(f"{fid}：系列の横軸がそろっていない")
            xs = x
            ys_list.append(values)
            names.append(s["name"])
        _line(cv, (box[0] + 110, box[1] + 60, box[2] - 40, box[3] - 40), xs, ys_list, colors, names, fmt)
    else:
        raise NoteError(f"{fid}：未対応の図の種類 {kind}")
    if spec.get("note"):
        cv.note(spec["note"], y=note_y)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv.finish().save(path, optimize=False)
    return path
