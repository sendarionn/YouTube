"""1フレームを描く部品

DESIGN.md の方針に合わせ、動きは「出現（フェード）」と「棒の伸長」だけにする
半透明の重ね合わせは使わず、背景色との線形補間でフェードを表現する（高速で、文字の重なりも起きない）
"""
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

from .config import find_font


def ease(p):
    """0〜1 を ease-out（3次）で補間"""
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def ramp(t, start, dur=0.5):
    """時刻 t における、start から dur 秒かけた進行度（0〜1、ease-out）"""
    if t is None or start is None:
        return 0.0
    return ease((t - start) / dur) if dur > 0 else float(t >= start)


def mix(c1, c2, a):
    """c2 から c1 へ a の割合で近づけた色（a=1 で c1）"""
    return tuple(round(c2[i] + (c1[i] - c2[i]) * a) for i in range(3))


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@dataclass
class Theme:
    width: int = 1920
    height: int = 1080
    margin: int = 120
    bg: tuple = hexrgb("F6F5F2")
    text: tuple = hexrgb("1F2328")
    sub: tuple = hexrgb("5B6470")
    grid: tuple = hexrgb("D9DCE0")
    accent: tuple = hexrgb("2E6BD1")
    compare: tuple = hexrgb("8E98A3")
    muted: tuple = hexrgb("C9CED4")
    font_regular: str = "BIZUDPGothic-Regular.ttf"
    font_bold: str = "BIZUDPGothic-Bold.ttf"
    # 文字サイズは3段階（タイトル・主要数値・補足）＋字幕と注記
    size_title: int = 56
    size_number: int = 120
    size_body: int = 40
    size_note: int = 26
    size_caption: int = 40
    caption_top: int = 948
    caption_bottom: int = 1040
    _fonts: dict = field(default_factory=dict, repr=False)

    def font(self, size, bold=False):
        k = (size, bold)
        if k not in self._fonts:
            self._fonts[k] = ImageFont.truetype(str(find_font(self.font_bold if bold else self.font_regular)), size)
        return self._fonts[k]


class Canvas:
    def __init__(self, theme):
        self.th = theme
        self.img = Image.new("RGB", (theme.width, theme.height), theme.bg)
        self.d = ImageDraw.Draw(self.img)

    # 文字
    def text(self, xy, s, size=None, bold=False, color=None, alpha=1.0, anchor="la"):
        if alpha <= 0:
            return
        f = self.th.font(size or self.th.size_body, bold)
        self.d.text(xy, s, font=f, fill=mix(color or self.th.text, self.th.bg, alpha), anchor=anchor)

    def text_width(self, s, size=None, bold=False):
        return self.d.textlength(s, font=self.th.font(size or self.th.size_body, bold))

    def wrap(self, s, width, size=None, bold=False):
        """幅に収まるよう1文字単位で折り返す（句読点・閉じ括弧を行頭に置かない）"""
        lines, cur = [], ""
        for ch in s:
            if self.text_width(cur + ch, size, bold) > width and cur:
                if ch in "、。）」％%・ー":
                    ch, cur = cur[-1] + ch, cur[:-1]
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        if cur:
            lines.append(cur)
        return lines

    # 図形
    def rect(self, box, color, alpha=1.0, radius=0):
        if alpha <= 0 or box[2] <= box[0] or box[3] <= box[1]:
            return
        c = mix(color, self.th.bg, alpha)
        if radius:
            self.d.rounded_rectangle(box, radius=radius, fill=c)
        else:
            self.d.rectangle(box, fill=c)

    def line(self, xy, color=None, width=2, alpha=1.0):
        if alpha > 0:
            self.d.line(xy, fill=mix(color or self.th.grid, self.th.bg, alpha), width=width)

    # 画面の定型部分
    def title(self, s, alpha=1.0):
        self.text((self.th.margin, 92), s, self.th.size_title, bold=True, alpha=alpha)

    def note(self, s, alpha=1.0, y=890):
        """分母・定義・出典などの注記（字幕帯より上の固定位置）"""
        self.text((self.th.margin, y), s, self.th.size_note, color=self.th.sub, alpha=alpha)

    def caption(self, s):
        """字幕（画面下の帯。図表と重ならない位置に固定）"""
        if not s:
            return
        th = self.th
        lines = self.wrap(s, th.width - 2 * th.margin - 80, th.size_caption)
        if len(lines) > 2:
            raise ValueError(f"字幕が3行以上になります：{s}")
        self.rect((0, th.caption_top, th.width, th.caption_bottom + 10), hexrgb("FFFFFF"))
        self.line([(0, th.caption_top), (th.width, th.caption_top)], th.grid, 2)
        lh = th.size_caption + 10
        y0 = (th.caption_top + th.caption_bottom) // 2 - lh * len(lines) // 2 + 4
        for i, ln in enumerate(lines):
            self.text((th.width // 2, y0 + i * lh), ln, th.size_caption, anchor="ma")


def vbars(cv, box, labels, values, progress=1.0, color=None, highlight=None, vmax=None,
          fmt="{:,}", alpha=1.0, label_size=None, value_size=None, colors=None):
    """縦棒グラフ（軸は0から）。highlight の棒だけ強調色、他は muted"""
    th = cv.th
    x0, y0, x1, y1 = box
    vmax = vmax or max(values)
    n = len(values)
    gap = (x1 - x0) / n
    bw = gap * 0.62
    ls = label_size or th.size_note + 4
    vs = value_size or th.size_body
    base = y1 - ls - 24
    cv.line([(x0, base), (x1, base)], th.grid, 3, alpha)
    for i, (lab, v) in enumerate(zip(labels, values)):
        cx = x0 + gap * (i + 0.5)
        h = (base - y0 - vs - 20) * v / vmax * progress
        c = (colors[i] if colors else (color or th.accent) if highlight is None or i in highlight else th.muted)
        cv.rect((cx - bw / 2, base - h, cx + bw / 2, base), c, alpha)
        cv.text((cx, base + 14), lab, ls, color=th.sub, alpha=alpha, anchor="ma")
        if progress > 0.98:
            cv.text((cx, base - h - 12), fmt.format(v), vs, bold=True, alpha=alpha, anchor="md")


def hbars(cv, box, labels, values, progress=1.0, color=None, vmax=None, fmt="{}", alpha=1.0,
          label_w=420, size=None, colors=None, row_h=None):
    """横棒グラフ（軸は0から）。progress は棒ごとのリストでもよい"""
    th = cv.th
    x0, y0, x1, y1 = box
    vmax = vmax or max(values)
    n = len(values)
    rh = row_h or (y1 - y0) / n
    s = size or th.size_body
    bx0 = x0 + label_w
    bx1 = x1 - 220
    for i, (lab, v) in enumerate(zip(labels, values)):
        p = progress[i] if isinstance(progress, (list, tuple)) else progress
        a = alpha if not isinstance(progress, (list, tuple)) else alpha * min(1.0, p * 3)
        cy = y0 + rh * (i + 0.5)
        bh = min(rh * 0.56, 64)
        c = colors[i] if colors else (color or th.accent)
        cv.text((x0, cy), lab, s, alpha=a, anchor="lm")
        w = (bx1 - bx0) * v / vmax * p
        cv.rect((bx0, cy - bh / 2, bx0 + w, cy + bh / 2), c, a)
        if p > 0.98:
            cv.text((bx0 + w + 18, cy), fmt.format(v), s, bold=True, alpha=a, anchor="lm")
    cv.line([(bx0, y0), (bx0, y0 + rh * n)], th.text, 2, alpha)


def waffle(cv, box, n_on, total=100, cols=10, progress=1.0, on=None, off=None, alpha=1.0):
    """total マスのうち n_on マスを強調する割合図（progress に応じて強調マスが順に色付く）"""
    th = cv.th
    x0, y0, x1, y1 = box
    rows = (total + cols - 1) // cols
    cell = min((x1 - x0) / cols, (y1 - y0) / rows)
    pad = cell * 0.14
    lit = int(round(n_on * progress))
    for k in range(total):
        r, c = divmod(k, cols)
        bx = x0 + c * cell
        by = y0 + r * cell
        col = (on or th.accent) if k < lit else (off or th.muted)
        cv.rect((bx + pad, by + pad, bx + cell - pad, by + cell - pad), col, alpha, radius=int(cell * 0.12))
