"""サムネイル：レーベルの地図を1枚絵にする（DESIGN.md「サムネイル」、記録は thumbnail.md）

- 主役：分野の割合の近さで並べたレーベルの点（本編の「レーベルの地図」と同じ配置と色）
- 文字：題材に含まれるレーベル名だけ（説明文・タイトルの繰り返しは置かない）
- 右下（再生時間の表示）には重要な要素を置かない
出力：output/shinsho-labels/video/thumbnail.png（1280×720）と、縮小確認用の 320px・168px
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE))

from scenes import CAT_COLOR, DATA, cat_key, tag  # noqa: E402
from tools.infographic.canvas import Canvas, Theme, mix  # noqa: E402
from tools.infographic.config import OUTPUT  # noqa: E402

OUT = OUTPUT / "shinsho-labels" / "video"
# レーベル名：(配置, 引き出し線の先のずれ)。塊の中のシリーズは塊の外へ引き出す
NAMED = {"ブルーバックス": ("rm", (-30, 58)), "交通新聞社新書": ("rm", None), "ヨベル新書": ("rm", None),
         "歴史新書y": ("rm", None), "中公新書": ("rm", (-150, -100))}


def main():
    th = Theme(width=1280, height=720, size_title=40, size_body=30, size_note=20)
    layout = json.loads((HERE / "map_layout.json").read_text(encoding="utf-8"))
    S = {r["label"]: r for r in csv.DictReader((DATA / "summary_labels.csv").open(encoding="utf-8"))}
    xs = [p[0] for p in layout["xy"]]
    ys = [p[1] for p in layout["xy"]]
    box = (110, 60, 1170, 640)

    def X(x):
        return box[0] + (x - min(xs)) / (max(xs) - min(xs)) * (box[2] - box[0])

    def Y(y):
        return box[1] + (y - min(ys)) / (max(ys) - min(ys)) * (box[3] - box[1])

    cv = Canvas(th)
    pts = sorted(zip(layout["labels"], layout["xy"]), key=lambda p: -float(S[p[0]]["titles_per_year"]))
    for l, (x, y) in pts:
        c = cat_key(S[l]["category"])
        r = 6 + 2.4 * float(S[l]["titles_per_year"]) ** 0.5
        cx, cy = X(x), Y(y)
        cv.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=mix(CAT_COLOR[c], th.bg, 0.9), outline=(255, 255, 255), width=2)
    for l, (x, y) in zip(layout["labels"], layout["xy"]):
        if l not in NAMED:
            continue
        c = cat_key(S[l]["category"])
        r = 6 + 2.4 * float(S[l]["titles_per_year"]) ** 0.5
        anchor, off = NAMED[l]
        if off:
            tag(cv, (X(x) + off[0], Y(y) + off[1]), l, th.size_body, CAT_COLOR[c], anchor=anchor, leader=(X(x), Y(y)))
        else:
            dx = (r + 10) * (-1 if anchor == "rm" else 1)
            tag(cv, (X(x) + dx, Y(y)), l, th.size_body, CAT_COLOR[c], anchor=anchor)
    img = cv.finish()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "thumbnail.png"
    img.save(path)
    for w in (320, 168):
        img.resize((w, w * 9 // 16)).save(OUT / f"thumbnail_{w}.png")
    return path


if __name__ == "__main__":
    print(main())
