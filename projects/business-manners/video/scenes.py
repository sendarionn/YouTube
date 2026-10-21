"""動画「『了解しました』はなぜ失礼になったのか？ ビジネスマナーの正体」の台本と画面

方針（AGENTS.md「ナレーションと映像の役割分担」、DESIGN.md）
- ナレーションは要点・解釈・結論。年号・書名・細かな数値・出典は画面のラベルと注記で示す
- 画面は年表、積み上げ棒、ピクトグラム、関係図で構成し、文章を読ませない
- アイコンは Tabler Icons（library/icons/、MIT）。年表・グラフ・関係図はここで描く
- 事実（出典あり）と、制作者の解釈・問題提起は台本上で言い方を分ける（「〜と言えます」「〜ではないでしょうか」）

数値は data/ の CSV から読み込む（手入力の数値を置かない）。出典は sources.md と video/claims.md
"""
import csv
import math
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
sys.path.insert(0, str(REPO))

from tools.infographic import svgicons as si  # noqa: E402
from tools.infographic.canvas import hbars, mix, ramp  # noqa: E402
from tools.infographic.video import Line, Scene, Shot  # noqa: E402

DATA = PROJECT / "data"
W, H, M = 1920, 1080, 120
CX = W // 2


def _csv(name):
    with open(DATA / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_numbers():
    N = {}
    counts = _csv("ndl_title_counts.csv")
    for term in ("マナー", "ビジネスマナー"):
        N[term] = {int(r["year"]): int(r["count"]) for r in counts if r["term"] == term}
    N["ryokai"] = [(r["year"], int(r["no_mention"]), int(r["not_rude"]), int(r["rude"])) for r in _csv("ryokai_manner_books.csv")]
    N["ryokai_total"] = sum(a + b + c for _, a, b, c in N["ryokai"])
    N["ryokai_reasons"] = [(r["reason"], int(r["books"])) for r in _csv("ryokai_reasons.csv")]
    h17 = _csv("bunka_h17_gokurou.csv")
    N["h17"] = {(r["target"], r["phrase"]): float(r["percent"]) for r in h17}
    en = _csv("en2025_survey.csv")
    N["en_need"] = {r["option"]: int(r["percent"]) for r in en if r["question"] == "必要か"}
    N["en_imp"] = [(r["option"], int(r["percent"])) for r in en if r["question"] == "重要なもの"]
    N["dict_first"] = min(int(r["year"]) for r in _csv("gokurou_dictionaries.csv") if r["mentions_hierarchy"] == "Y")
    # 集計ファイルと論文の記載の整合性（不一致なら描画しない）
    assert N["ryokai_total"] == 319
    assert N["ryokai"][0] == ("-2002", 49, 0, 0)
    assert N["dict_first"] == 1988
    assert N["h17"][("superior", "お疲れ様（でした）")] == 69.2 and N["h17"][("superior", "御苦労様（でした）")] == 15.1
    assert max(N["マナー"], key=N["マナー"].get) == 2008
    return N


# ---- 共通の部品 ----------------------------------------------------------

def icon(cv, name, cx, cy, s, color=None, alpha=1.0, stroke=1.75):
    si.draw(cv, name, cx, cy, s, color, alpha, stroke)


def card(cv, box, alpha, fill=(255, 255, 255), radius=16):
    cv.rect(box, fill, alpha, radius)


def bubble(cv, x, y, text, alpha, size=44, color=None, fill=(255, 255, 255), tail="left"):
    """吹き出し（左上を (x, y) とする）。幅は文字に合わせる"""
    if alpha <= 0:
        return 0
    w = cv.text_width(text, size, True) + 72
    h = size + 52
    cv.rect((x, y, x + w, y + h), fill, alpha, 22)
    tx = x + 46 if tail == "left" else x + w - 46
    cv.d.polygon([(tx - 14, y + h - 2), (tx + 14, y + h - 2), (tx - 6 if tail == "left" else tx + 6, y + h + 22)],
                 fill=mix(fill, cv.th.bg, alpha))
    cv.text((x + 36, y + 26), text, size, bold=True, color=color, alpha=alpha)
    return w


def label_block(cv, cx, y, lines, alpha, size=28, bold_first=True, color=None):
    """中央揃えの短いラベル（複数行）"""
    for k, ln in enumerate(lines):
        cv.text((cx, y + k * (size + 10)), ln, size, bold=(bold_first and k == 0), color=color, alpha=alpha, anchor="ma")


def year_axis(cv, x0, x1, y, y_start, y_end, step, alpha):
    th = cv.th

    def X(v):
        return x0 + (x1 - x0) * (v - y_start) / (y_end - y_start)
    cv.line([(x0, y), (x1, y)], th.grid, 3, alpha)
    first = y_start + (-y_start) % step
    for v in range(first, y_end + 1, step):
        cv.line([(X(v), y - 8), (X(v), y + 8)], th.grid, 3, alpha)
        cv.text((X(v), y + 18), str(v), th.size_note, color=th.sub, alpha=alpha, anchor="ma")
    return X


def event(cv, x, y_axis, up, icon_name, year, lines, alpha, color=None, stem=120, size=26):
    """年表の出来事：軸上の点、縦線、アイコン、年、ラベル。up=True で軸の上側に置く"""
    if alpha <= 0:
        return
    th = cv.th
    c = color or th.text
    # 軸の上に出るため、背景色ではなく軸の色から混ぜる（出現の途中で軸が途切れて見えない）
    cv.d.ellipse((x - 9, y_axis - 9, x + 9, y_axis + 9), fill=mix(c, th.grid, alpha))
    if up:
        top = y_axis - stem
        cv.line([(x, y_axis - 10), (x, top + 40)], th.grid, 2, alpha)
        icon(cv, icon_name, x, top, 64, c, alpha)
        cv.text((x, top - 70), str(year), th.size_note + 2, bold=True, color=c, alpha=alpha, anchor="ma")
        for k, ln in enumerate(reversed(lines)):
            cv.text((x, top - 82 - (k + 1) * (size + 8)), ln, size, alpha=alpha, anchor="ma")
    else:
        top = y_axis + stem
        cv.line([(x, y_axis + 10), (x, top - 40)], th.grid, 2, alpha)
        icon(cv, icon_name, x, top, 64, c, alpha)
        cv.text((x, top + 44), str(year), th.size_note + 2, bold=True, color=c, alpha=alpha, anchor="ma")
        for k, ln in enumerate(lines):
            cv.text((x, top + 82 + k * (size + 8)), ln, size, alpha=alpha, anchor="ma")


def arrow_to(cv, p0, p1, alpha, color=None, width=4, head=18):
    """任意方向の矢印"""
    if alpha <= 0:
        return
    th = cv.th
    c = color or th.sub
    (x0, y0), (x1, y1) = p0, p1
    ang = math.atan2(y1 - y0, x1 - x0)
    bx, by = x1 - head * math.cos(ang), y1 - head * math.sin(ang)
    cv.line([(x0, y0), (bx, by)], c, width, alpha)
    left = (bx + head * 0.6 * math.cos(ang + math.pi / 2), by + head * 0.6 * math.sin(ang + math.pi / 2))
    right = (bx + head * 0.6 * math.cos(ang - math.pi / 2), by + head * 0.6 * math.sin(ang - math.pi / 2))
    cv.d.polygon([(x1, y1), left, right], fill=mix(c, th.bg, alpha))


def chapter(num, title, line, say=None):
    def d(cv, st):
        th = cv.th
        a = ramp(st.t, 0.1, 0.6)
        cv.text((CX, 420), f"第{num}章", th.size_body, color=th.accent, bold=True, alpha=a, anchor="ma")
        cv.text((CX, 490), title, th.size_title + 8, bold=True, alpha=a, anchor="ma")
        cv.line([(CX - 60, 600), (CX + 60, 600)], th.accent, 4, a)
    return Scene(f"第{num}章 {title}", [Line(line, say)], d, lead=0.9, tail=1.0)


# ---- 場面 ----------------------------------------------------------------

def build(N, voice_credit, music_credit, icon_credit):
    scenes = []

    # 冒頭 ---------------------------------------------------------------
    def d_open(cv, st):
        th = cv.th
        a = ramp(st.t, st.at(0), 0.6)
        icon(cv, "user", 520, 470, 170, th.sub, a)
        label_block(cv, 520, 580, ["若手"], a, 30, color=th.sub)
        icon(cv, "user", 1400, 470, 200, th.text, a)
        label_block(cv, 1400, 590, ["上司"], a, 30)
        # 了解しました
        b = ramp(st.t, st.at(0) + 0.8, 0.5)
        w = cv.text_width("了解しました", 48, True) + 72
        bx = CX - w / 2
        bubble(cv, bx, 300, "了解しました", b, 48)
        # 失礼の印
        c = ramp(st.t, st.at(1) + 1.0, 0.5)
        if c > 0:
            cv.line([(bx + 20, 300 + 50), (bx + w - 20, 300 + 50)], th.accent, 6, c)
            cv.rect((CX - 70, 420, CX + 70, 480), th.accent, c, 30)
            cv.text((CX, 432), "失礼", 34, bold=True, color=(255, 255, 255), alpha=c, anchor="ma")
        # 承知しました
        d2 = ramp(st.t, st.at(2), 0.5)
        w2 = cv.text_width("承知しました", 48, True) + 72
        bubble(cv, CX - w2 / 2, 540, "承知しました", d2, 48)
        # 問い
        q1 = ramp(st.t, st.at(3), 0.6)
        q2 = ramp(st.t, st.at(4), 0.6)
        for x, q, s in ((CX - 220, q1, "いつから？"), (CX + 220, q2, "誰が？")):
            if q > 0:
                card(cv, (x - 170, 720, x + 170, 820), q, th.accent)
                cv.text((x, 744), s, 46, bold=True, color=(255, 255, 255), alpha=q, anchor="ma")

    scenes.append(Scene("冒頭", [
        Line("上司からの連絡に、「了解しました」と返す。"),
        Line("マナー研修やマナーの本では、これは目上の人に失礼だ、と教わることがあります。"),
        Line("代わりに使うべきなのは、「承知しました」。"),
        Line("でも、このルールは、昔からあったのでしょうか。"),
        Line("そして、誰が失礼だと決めたのでしょうか。"),
    ], d_open, lead=0.8, tail=1.4, shots=[
        Shot("スマートフォンで「了解しました」と返信する手元", "冒頭の場面を身近な状況として見せる", line=0, seconds=4,
             angle="手元の俯瞰。画面の文字が読める程度に寄る",
             notes="実在の人名・社名・通知が映らないようにする。端末のロゴは映さない", placeholder="返信の吹き出しの図"),
    ]))

    # 三つの問い -----------------------------------------------------------
    def d_three(cv, st):
        th = cv.th
        cv.title("この動画で分けて考えること", ramp(st.t, st.at(1), 0.5))
        items = [("tool", "実用的合理性", ["その作法は", "実際に役に立つか"]),
                 ("users", "社会的慣習", ["多くの人が", "その作法を期待しているか"]),
                 ("scale", "規範的妥当性", ["守らない人を", "責めてよい理由があるか"])]
        cw, gap = 460, 60
        x0 = CX - (3 * cw + 2 * gap) / 2
        for k, (ic, head, body) in enumerate(items):
            a = ramp(st.t, st.at(2 + k), 0.6)
            x = x0 + k * (cw + gap)
            card(cv, (x, 260, x + cw, 760), a)
            icon(cv, ic, x + cw / 2, 380, 120, th.accent, a)
            cv.text((x + cw / 2, 490), head, th.size_body, bold=True, alpha=a, anchor="ma")
            label_block(cv, x + cw / 2, 580, body, a, 30, bold_first=False, color=th.sub)
        e = ramp(st.t, st.at(5), 0.6)
        if e > 0:
            for k in range(2):
                x = x0 + (k + 1) * (cw + gap) - gap / 2
                cv.text((x, 500), "≠", th.size_title, bold=True, color=th.sub, alpha=e, anchor="mm")

    scenes.append(Scene("三つの問い", [
        Line("この動画では、ビジネスマナーがどう生まれ、広まったのかをたどります。"),
        Line("そのうえで、三つのことを分けて考えます。"),
        Line("その作法は、実際に役に立つのか。"),
        Line("多くの人が、その作法を期待しているのか。"),
        Line("そして、守らない人を責めてよい理由があるのか。"),
        Line("この三つは、似ているようで、別の問いです。"),
    ], d_three, tail=1.4))

    # 第2章 ---------------------------------------------------------------
    scenes.append(chapter(2, "ビジネスマナーを広めた人々",
                          "まず、日本の職場の作法が、誰によって形づくられてきたのかを見ていきます。"))

    # 戦前 ---------------------------------------------------------------
    def d_prewar(cv, st):
        th = cv.th
        cv.title("学校と国の礼法", ramp(st.t, 0, 0.4))
        X = year_axis(cv, M + 60, W - M - 60, 560, 1880, 1950, 10, ramp(st.t, 0.2, 0.5))
        event(cv, X(1883), 560, True, "school", 1883, ["小笠原清務ら", "女子の礼法の教科書"], ramp(st.t, st.at(0), 0.6))
        event(cv, X(1915), 560, False, "user", 1915, ["講道館の礼法", "お辞儀を「約三十度」"], ramp(st.t, st.at(0) + 1.5, 0.6))
        event(cv, X(1941), 560, True, "building-bank", 1941, ["文部省『礼法要項』", "国民の礼法を統一"],
              ramp(st.t, st.at(1), 0.6), color=th.accent)
        event(cv, X(1945), 560, False, "x", 1945, ["GHQの指令で", "修身の授業を停止"], ramp(st.t, st.at(2) + 1.2, 0.6))
        cv.note("出典：東京学芸大学 貴重書（1883年）、中嶋（2021）『体育学研究』66、文部省『学制百年史』",
                ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("戦前", [
        Line("明治以降、礼儀作法は、学校で教えられてきました。"),
        Line("戦時中の1941年には、国が「礼法要項」をまとめ、国民の礼法を一つにそろえようとします。",
             "戦時中の1941年には、国が、礼法要項をまとめ、国民の礼法を一つにそろえようとします。"),
        Line("ただ、これは職場のための作法ではありません。戦後、修身の授業は停止され、再開されませんでした。"),
    ], d_prewar, tail=1.2))

    # 戦後 ---------------------------------------------------------------
    def d_postwar(cv, st):
        th = cv.th
        cv.title("職場の作法を本にした人たち", ramp(st.t, 0, 0.4))
        X = year_axis(cv, M + 60, W - M - 60, 560, 1950, 1980, 5, ramp(st.t, 0.2, 0.5))
        event(cv, X(1952), 560, True, "briefcase", 1952, ["日経連", "『職場のエチケット』"], ramp(st.t, st.at(1), 0.6),
              color=th.accent)
        event(cv, X(1962), 560, False, "phone", 1962, ["電話応対", "コンクール開始"], ramp(st.t, st.at(2), 0.6))
        event(cv, X(1970), 560, True, "book", 1970, ["『新入社員の", "ビジネス・マナー』"], ramp(st.t, st.at(2) + 1.0, 0.6))
        event(cv, X(1972), 560, False, "certificate", 1972, ["秘書検定の", "協会が発足"], ramp(st.t, st.at(2) + 2.0, 0.6))
        event(cv, X(1958), 560, False, "briefcase", 1958, ["日経連", "『職場のモラルと", "エチケット』"], ramp(st.t, st.at(1) + 1.2, 0.6),
              color=th.accent)
        event(cv, X(1978), 560, True, "briefcase", 1978, ["日経連", "『新・職場のエチケット』"], ramp(st.t, st.at(3), 0.6),
              color=th.accent)
        cv.note("国立国会図書館の書誌、日本ICTテレコムユーザー協会、実務技能検定協会の公式情報による",
                ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("戦後", [
        Line("戦後、職場の作法を本にまとめたのは、経営者の団体でした。"),
        Line("1952年には、日経連が「職場のエチケット」という本を出しています。",
             "1952年には、日経連が、職場のエチケット、という本を出しています。"),
        Line("その後も、電話応対のコンクールや秘書の検定など、職場の作法を教え、測る仕組みが作られていきます。"),
        Line("当時の本の多くは、新入社員や女性社員に向けたものでした。"),
    ], d_postwar, tail=1.2))

    # 本の推移 -------------------------------------------------------------
    y0, y1 = 1960, 2025

    def d_books(cv, st):
        th = cv.th
        cv.title("題名に「マナー」を含む本の数", ramp(st.t, 0, 0.4))
        gx0, gx1, gy0, gy1 = M + 120, W - M - 220, 300, 800
        vmax = 100

        def X(y):
            return gx0 + (gx1 - gx0) * (y - y0) / (y1 - y0)

        def Y(v):
            return gy1 - (gy1 - gy0) * v / vmax
        a = ramp(st.t, 0.2, 0.5)
        for v in range(0, vmax + 1, 25):
            cv.line([(gx0, Y(v)), (gx1, Y(v))], th.grid, 2 if v else 3, a)
            cv.text((gx0 - 16, Y(v)), str(v), th.size_note, color=th.sub, alpha=a, anchor="rm")
        cv.text((gx0 - 16, gy0 - 40), "点/年", th.size_note, color=th.sub, alpha=a, anchor="rm")
        for yr in range(1960, 2021, 10):
            cv.text((X(yr), gy1 + 16), str(yr), th.size_note, color=th.sub, alpha=a, anchor="ma")

        def series(data, prog, color, width):
            last = y0 + (y1 - y0) * prog
            pts = [(X(y), Y(data.get(y, 0))) for y in range(y0, y1 + 1) if y <= last]
            if len(pts) >= 2:
                cv.line(pts, color, width)
            return pts
        p1 = ramp(st.t, st.at(0), 3.5)
        pts = series(N["マナー"], p1, th.compare, 5)
        if p1 >= 1:
            cv.text((pts[-1][0] + 16, pts[-1][1]), "マナー", th.size_note + 4, bold=True, color=th.compare, anchor="lm")
        p2 = ramp(st.t, st.at(1), 3.5)
        pts2 = series(N["ビジネスマナー"], p2, th.accent, 6)
        if p2 >= 1:
            cv.text((pts2[-1][0] + 16, pts2[-1][1]), "ビジネスマナー", th.size_note + 4, bold=True, color=th.accent, anchor="lm")
        h = ramp(st.t, st.at(1) + 3.6, 0.6)
        if h > 0:
            v = N["マナー"][2008]
            cv.line([(X(2008), Y(v) - 10), (X(2008), Y(v) - 60)], th.text, 2, h)
            cv.text((X(2008), Y(v) - 70), f"2008年 {v}点", th.size_note + 2, bold=True, alpha=h, anchor="md")
        cv.note("国立国会図書館の所蔵資料で、題名に語を含むもの。版違いを別に数え、出版点数全体の増加は補正していない",
                ramp(st.t, st.at(0), 0.6))

    scenes.append(Scene("本の推移", [
        Line("題名に「マナー」を含む本は、1980年代に入ると、急に増えていきます。",
             "題名にマナーという言葉を含む本は、1980年代に入ると、急に増えていきます。"),
        Line("「ビジネスマナー」という言葉の本も、このころから毎年出るようになり、2000年代の後半に最も多くなりました。",
             "ビジネスマナー、という言葉の本も、このころから毎年出るようになり、2000年代の後半に最も多くなりました。"),
        Line("この時期、マナーを教える人たちの顔ぶれも、広がっていきます。"),
    ], d_books, tail=1.8))

    # 航空会社 -------------------------------------------------------------
    def d_airline(cv, st):
        th = cv.th
        cv.title("1980年代の担い手", ramp(st.t, 0, 0.4))
        x0, x1 = M + 330, W - M - 40
        a = ramp(st.t, 0.2, 0.5)

        def X(v):
            return x0 + (x1 - x0) * (v - 1980) / 12
        for yr in range(1980, 1993, 2):
            cv.line([(X(yr), 250), (X(yr), 830)], th.grid, 2, a)
            cv.text((X(yr), 842), str(yr), th.size_note, color=th.sub, alpha=a, anchor="ma")
        rows = [("plane", "航空会社・元CA", 380, th.accent), ("briefcase", "経営団体・銀行", 560, th.text),
                ("book", "出版社・礼法家", 720, th.text)]
        for k, (ic, lab, y, c) in enumerate(rows):
            ra = ramp(st.t, st.at(0) if k == 0 else st.at(3), 0.6)
            icon(cv, ic, M + 40, y, 56, c, ra)
            cv.text((M + 90, y), lab, th.size_note + 4, bold=True, color=c, alpha=ra, anchor="lm")
            cv.line([(x0, y), (x1, y)], th.grid, 3, ra)

        def dot(yr, y, lines, al, c, up=True):
            if al <= 0:
                return
            x = X(yr)
            cv.d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=mix(c, th.grid, al))
            for k, ln in enumerate(lines):
                yy = y - 30 - (len(lines) - k) * 34 if up else y + 26 + k * 34
                cv.text((x, yy), ln, 26, alpha=al, anchor="ma")
        dot(1982.9, 380, ["日本航空 客室訓練部", "『接客応対の基本』"], ramp(st.t, st.at(1), 0.6), th.accent)
        dot(1986.3, 380, ["均等法施行後", "元CAの研修会社・", "子会社の研修受託"], ramp(st.t, st.at(2) + 1.0, 0.6), th.accent, up=False)
        dot(1989.2, 380, ["JAL子会社", "『いきいきマナー講座』"], ramp(st.t, st.at(2) + 3.0, 0.6), th.accent)
        b = ramp(st.t, st.at(3) + 0.8, 0.6)
        dot(1984.1, 560, ["日経連", "『ビジネスマナー常識集』"], b, th.text, up=False)
        dot(1987.2, 560, ["日本生産性本部・", "富士銀行"], b, th.text, up=False)
        dot(1982.3, 720, ["『ビジネス・マナー』", "の本が毎年刊行"], b, th.text, up=False)
        dot(1986.1, 720, ["佐久間進", "『新小笠原流』"], b, th.text, up=False)
        cv.note("国立国会図書館の書誌。均等法施行後の動きは朝日新聞（1986年）を引く長船（2023、千葉大学博士論文）による",
                ramp(st.t, st.at(2), 0.6))

    scenes.append(Scene("航空会社", [
        Line("その一つが、航空会社です。"),
        Line("日本航空は1982年に、客室乗務員の訓練部門がまとめた、接客応対の本を出しています。"),
        Line("1986年に男女雇用機会均等法が施行されると、マナー研修の需要が増え、元客室乗務員が研修の会社を立ち上げたり、"
             "航空会社の子会社が企業の研修を引き受けたりしたことが、当時の新聞で報じられています。"),
        Line("ただ、同じころ、経営者の団体や銀行、礼法の専門家なども、ビジネスマナーの本を出していました。"),
        Line("航空会社はマナーを作ったのではなく、接客の専門家として、研修や本でマナーを広めた担い手の一つだった、と言えます。"),
        Line("どれだけの企業に影響したのかを示す記録は、見つかりませんでした。"),
    ], d_airline, tail=1.4))

    # なぜ航空会社か ---------------------------------------------------------
    eras = [(1931, 1941, "エアガールの誕生"), (1952, 1966, "着物姿の「客室兵」"), (1967, 1982, "ジャンボ時代の混迷"),
            (1983, 1993, "接客マナーと「自分磨き」"), (1994, 2012, "相続される「おもてなし」")]

    def d_why(cv, st):
        th = cv.th
        cv.title("客室乗務員のイメージの移り変わり", ramp(st.t, 0, 0.4))
        x0, x1 = M + 60, W - M - 60

        def X(v):
            return x0 + (x1 - x0) * (v - 1930) / (2015 - 1930)
        a = ramp(st.t, st.at(1), 0.6)
        for yr in range(1930, 2016, 10):
            cv.text((X(yr), 680), str(yr), th.size_note, color=th.sub, alpha=a, anchor="ma")
        cv.line([(x0, 660), (x1, 660)], th.grid, 3, a)
        for k, (s0, s1, lab) in enumerate(eras):
            p = ramp(st.t, st.at(1) + 0.4 * k, 0.6)
            hi = k == 3
            c = th.accent if hi else th.muted
            y = 540 if k % 2 == 0 else 420
            cv.rect((X(s0), y, X(s1 + 1), y + 70), c, p, 8)
            cv.text(((X(s0) + X(s1 + 1)) / 2, y - 16), lab, 28 if hi else 26, bold=hi,
                    color=th.accent if hi else th.sub, alpha=p, anchor="md")
        icon(cv, "plane", CX, 270, 80, th.text, ramp(st.t, st.at(0), 0.6))
        cv.note("山口誠（2020）『客室乗務員の誕生』岩波新書の章立て（書誌・目次と書評で確認。本文は未確認）",
                ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("なぜ航空会社か", [
        Line("では、なぜ航空会社だったのでしょうか。"),
        Line("客室乗務員の歴史を調べた研究は、客室乗務員が「おもてなし」の手本と見られるようになったのは、1980年代以降の新しいイメージだと論じています。",
             "客室乗務員の歴史を調べた研究は、客室乗務員が、おもてなしの手本と見られるようになったのは、1980年代以降の新しいイメージだと論じています。"),
        Line("接客の専門家というイメージが、研修の講師としての信頼にもつながった、と考えることもできます。"),
    ], d_why, tail=1.4))

    # 担い手のまとめ（2000年代以降を含む） -------------------------------------
    actors = [("school", "学校・国", "〜1945"), ("briefcase", "経営者団体", "1950年代〜"), ("certificate", "検定・協会", "1960年代〜"),
              ("plane", "航空会社・元CA", "1980年代〜"), ("books", "出版", "2000年代に最多"), ("world-www", "ウェブ記事", "2010年代〜")]

    def d_actors(cv, st):
        th = cv.th
        cv.title("ビジネスマナーを広めた担い手", ramp(st.t, 0, 0.4))
        r = 270
        cy = 490
        c = ramp(st.t, st.at(0), 0.6)
        card(cv, (CX - 170, cy - 60, CX + 170, cy + 60), c, th.accent, 60)
        cv.text((CX, cy), "ビジネスマナー", th.size_body, bold=True, color=(255, 255, 255), alpha=c, anchor="mm")
        for k, (ic, lab, era) in enumerate(actors):
            ang = math.radians(-90 + k * 60)
            x, y = CX + math.cos(ang) * r * 1.9, cy + math.sin(ang) * r
            if k < 4:
                al = ramp(st.t, st.at(0) + 0.3 * k, 0.6)
            else:
                al = ramp(st.t, st.at(k - 3), 0.6)
            ex, ey = CX + math.cos(ang) * 200, cy + math.sin(ang) * 72
            sx, sy = x - math.cos(ang) * 120, y - math.sin(ang) * 70
            arrow_to(cv, (sx, sy), (ex, ey), al, th.muted, 4)
            icon(cv, ic, x, y - 30, 64, th.text, al)
            cv.text((x, y + 14), lab, 30, bold=True, alpha=al, anchor="ma")
            cv.text((x, y + 52), era, 26, color=th.sub, alpha=al, anchor="ma")
        cv.note("ビジネス実務マナー技能検定などは2003年から文部科学省後援（実務技能検定協会）", ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("担い手", [
        Line("2000年代には、マナーの本が最も多く出版され、マナーの検定は、文部科学省の後援を受けるようになります。"),
        Line("さらに2010年代には、ウェブの記事が、個別の「失礼」を広めていきます。",
             "さらに2010年代には、ウェブの記事が、個別の、失礼、を広めていきます。"),
        Line("ビジネスマナーは、一つの業界ではなく、多くの担い手が重なって広めてきたものでした。"),
    ], d_actors, tail=1.6))

    # 第3章 ---------------------------------------------------------------
    scenes.append(chapter(3, "「失礼」が生まれるまで",
                          "では、その「失礼」の一つは、どのように生まれたのでしょうか。",
                          "では、その、失礼、の一つは、どのように生まれたのでしょうか。"))

    # 了解の由来 -----------------------------------------------------------
    def d_radio(cv, st):
        th = cv.th
        cv.title("「了解」はもともと無線の応答", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0), 0.6)
        icon(cv, "antenna", 560, 400, 150, th.text, a)
        icon(cv, "antenna", 1360, 400, 150, th.text, a)
        # 電波：アンテナ間の点線が左から右へ伸びる
        w = ramp(st.t, st.at(0) + 0.6, 1.0)
        n_dash = int(14 * w)
        for k in range(n_dash):
            x = 660 + k * 44
            cv.line([(x, 400), (x + 22, 400)], th.accent, 6)
        bubble(cv, 650, 230, "了解", ramp(st.t, st.at(0) + 1.4, 0.5), 44)
        cv.text((CX, 520), "Roger（受信した）＝「了解」", th.size_body, bold=True, alpha=ramp(st.t, st.at(0) + 1.4, 0.6), anchor="ma")
        # 1944年の小説：上官にも部下にも
        b = ramp(st.t, st.at(1), 0.6)
        icon(cv, "book", CX, 640, 70, th.accent, b)
        cv.text((CX, 690), "1944〜45年 海野十三『宇宙戦隊』", th.size_note + 2, bold=True, alpha=b, anchor="ma")
        c = ramp(st.t, st.at(1) + 1.6, 0.6)
        for x, lab in ((CX - 330, "上官 → 部下"), (CX + 330, "部下 → 上官")):
            card(cv, (x - 200, 750, x + 200, 830), c)
            cv.text((x, 772), f"{lab}「了解」", 30, bold=True, alpha=c, anchor="ma")
        cv.note("髙橋・東泉・佐藤（2018）。無線局運用規則（1950）の通話表で「了解」。小説の例は同論文がコーパスで確認した最も古い例",
                ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("了解の由来", [
        Line("「了解」は、もともと無線の通信で、内容を受け取ったことを短く伝える言葉として使われてきました。",
             "了解という言葉は、もともと無線の通信で、内容を受け取ったことを短く伝える言葉として使われてきました。"),
        Line("研究者が確かめた、応答としての古い例は、1944年ごろの小説で、上官にも部下にも使われています。"),
        Line("言葉の意味としては、敬意の上下を含んでいません。"),
    ], d_radio, tail=1.2))

    # マナー本319冊 --------------------------------------------------------
    def d_books319(cv, st):
        th = cv.th
        cv.title(f"マナー本{N['ryokai_total']}冊の「了解」の扱い", ramp(st.t, 0, 0.4))
        data = N["ryokai"]
        gx0, gx1, gy0, gy1 = M + 80, W - M - 80, 230, 760
        n = len(data)
        gap = (gx1 - gx0) / n
        bw = gap * 0.64
        vmax = 50

        def Y(v):
            return gy1 - (gy1 - gy0) * v / vmax
        a = ramp(st.t, st.at(1), 0.5)
        cv.line([(gx0, gy1), (gx1, gy1)], th.grid, 3, a)
        cols = [th.muted, th.compare, th.accent]
        # 出現の順：〜2002 → 2003〜2010 → 2011〜2013 → 2014〜
        stage = [ramp(st.t, st.at(2), 0.8), ramp(st.t, st.at(3), 1.2), ramp(st.t, st.at(3) + 2.5, 1.0), ramp(st.t, st.at(4), 1.0)]

        def stage_of(lab):
            if lab == "-2002":
                return stage[0]
            y = int(lab)
            return stage[1] if y <= 2010 else stage[2] if y <= 2013 else stage[3]
        for i, (lab, nm, ok, rude) in enumerate(data):
            p = stage_of(lab)
            cx = gx0 + gap * (i + 0.5)
            base = gy1
            for v, c in ((nm, cols[0]), (ok, cols[1]), (rude, cols[2])):
                h = (gy1 - gy0) * v / vmax * p
                cv.rect((cx - bw / 2, base - h, cx + bw / 2, base), c, min(1, p * 2))
                base -= h
            cv.text((cx, gy1 + 14), "〜2002" if lab == "-2002" else lab[2:], 24, color=th.sub, alpha=a, anchor="ma")
        cv.text((gx0 + gap * 0.5, Y(49) - 12), "49冊", 28, bold=True, alpha=stage[0], anchor="md")
        # 棒が出る前：調べた本の数を示し、棒が出始めたら消す
        intro = ramp(st.t, st.at(1), 0.6) * (1 - ramp(st.t, st.at(2) - 0.4, 0.5))
        if intro > 0:
            icon(cv, "books", CX, 400, 120, th.accent, intro)
            cv.text((CX, 490), f"{N['ryokai_total']}冊", th.size_number, bold=True, color=th.accent, alpha=intro, anchor="ma")
            cv.text((CX, 640), "敬語・マナー・ビジネスメールの本を出版年ごとに", 32, color=th.sub, alpha=intro, anchor="ma")
        cv.text((gx0, gy1 + 50), "年（下2桁）", 22, color=th.sub, alpha=a)
        # 凡例
        lg = ramp(st.t, st.at(2), 0.6)
        lx = CX + 40
        for k, (c, s) in enumerate(((cols[0], "記述なし"), (cols[1], "使ってよい"), (cols[2], "失礼"))):
            x = lx + k * 230
            cv.rect((x, 300, x + 32, 332), c, lg, 6)
            cv.text((x + 44, 316), s, 30, bold=(k == 2), alpha=lg, anchor="lm")
        cv.note("東京都内の公共図書館で「敬語」「マナー」「ビジネスメール」などで検索した書籍（髙橋・東泉・佐藤 2018 表4）。〜2002は合計",
                ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("マナー本319冊", [
        Line("では、「了解は失礼」という説明は、いつ現れたのでしょうか。",
             "では、了解は失礼、という説明は、いつ現れたのでしょうか。"),
        Line("日本語の研究者たちが、敬語やビジネスメールについての本、319冊を、出版された年ごとに調べています。"),
        Line("2002年までの本には、「了解」についての記述は、一冊もありませんでした。",
             "2002年までの本には、了解、についての記述は、一冊もありませんでした。"),
        Line("2003年ごろから、失礼だとする本と、使ってよいとする本が並び始め、2011年に、失礼だとする本が多数になります。"),
        Line("そして2014年以降、使ってよいとする本は、調べた範囲から姿を消しました。"),
        Line("調べた本に書かれていないからといって、当時、誰もそう考えていなかったとは言えません。"),
        Line("それでも、本に書かれる「常識」になったのは、ここ十数年のことです。",
             "それでも、本に書かれる、常識、になったのは、ここ十数年のことです。"),
    ], d_books319, tail=1.8, shots=[
        Shot("敬語・ビジネスメールの本が並ぶ書店や図書館の棚", "研究で調べた本の量を実物で見せる", line=1, seconds=4,
             angle="棚の正面から横移動。特定の1冊を強調しない",
             notes="撮影許可を得る。調査対象の319冊そのものと誤解されないよう、ナレーションと重ねる位置に注意する",
             placeholder="年ごとの冊数の棒グラフ（撮影素材は棒グラフの前に短く挿入する）"),
    ]))

    # 失礼の根拠 -----------------------------------------------------------
    def d_reasons(cv, st):
        th = cv.th
        cv.title("「失礼」とする本が挙げた理由", ramp(st.t, 0, 0.4))
        top = N["ryokai_reasons"][:4]
        labels = ["敬語として不適切", "上から目線", "「承認」の意味", "軍隊・警察のイメージ"]
        p = [ramp(st.t, st.at(0) + 0.3 * k, 0.8) for k in range(len(top))]
        hbars(cv, (M + 160, 220, W - M - 100, 620), labels, [v for _, v in top], p, color=th.accent, vmax=25,
              fmt="{}冊", label_w=440, size=34)
        b = ramp(st.t, st.at(1), 0.6)
        if b > 0:
            w = cv.text_width("了解いたしました", 44, True) + 72
            bubble(cv, CX - w / 2, 680, "了解いたしました", b, 44)
            cv.text((CX + w / 2 + 30, 730), "→ 敬語として十分", 32, bold=True, color=th.accent, alpha=b, anchor="lm")
        cv.note("1冊で複数の理由を挙げる本がある（髙橋ほか 2018）。「了解いたしました」の見解は国語辞典編纂者の飯間浩明（2016）",
                ramp(st.t, st.at(0), 0.6))

    scenes.append(Scene("失礼の根拠", [
        Line("失礼だとする本が挙げた理由で多かったのは、「敬語ではない」「上から目線に聞こえる」というものでした。",
             "失礼だとする本が挙げた理由で多かったのは、敬語ではない、上から目線に聞こえる、というものでした。"),
        Line("一方で、「了解いたしました」と言えば、敬語として十分だ、とする国語辞典の編纂者もいます。",
             "一方で、了解いたしました、と言えば、敬語として十分だ、とする国語辞典の編纂者もいます。"),
    ], d_reasons, tail=1.4))

    # 了解の広まり ---------------------------------------------------------
    def d_ryokai_media(cv, st):
        th = cv.th
        cv.title("「了解は失礼」が広まった経路", ramp(st.t, 0, 0.4))
        X = year_axis(cv, M + 100, W - M - 100, 560, 2002, 2016, 2, ramp(st.t, 0.2, 0.5))
        event(cv, X(2003), 560, True, "book", 2003, ["マナー本に", "「失礼」説が現れる"], ramp(st.t, st.at(0), 0.6))
        event(cv, X(2009.2), 560, False, "news", 2009, ["新聞の記事", "「承知しました」が正しい"], ramp(st.t, st.at(1), 0.6))
        event(cv, X(2010), 560, True, "notebook", 2010, ["国語辞典の第2版に", "「敬意が不足」の注記"], ramp(st.t, st.at(1) + 1.8, 0.6))
        event(cv, X(2011.5), 560, False, "world-www", 2011, ["ウェブ記事で", "広がる（指摘）"], ramp(st.t, st.at(2), 0.6),
              color=th.accent)
        event(cv, X(2014), 560, True, "book", 2014, ["「使ってよい」とする", "本が見られなくなる"], ramp(st.t, st.at(3), 0.6),
              color=th.accent)
        cv.note("髙橋ほか（2018）、J-CASTニュース（2024）が確認した日本経済新聞電子版2009年3月28日、菊池良（LIG、2016）",
                ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("了解の広まり", [
        Line("この説は、本の外にも広がっていきました。"),
        Line("2009年には新聞の記事に、2010年には国語辞典の注記にも、目上への「了解」を避けるよう勧める説明が現れます。",
             "2009年には新聞の記事に、2010年には国語辞典の注記にも、目上への、了解、を避けるよう勧める説明が現れます。"),
        Line("2011年ごろからは、ウェブの記事が、この説を広く伝えるようになったと指摘されています。"),
        Line("書く媒体が増えるほど、反対の説は見えにくくなっていきました。"),
    ], d_ryokai_media, tail=1.4))

    # ご苦労様 ---------------------------------------------------------------
    def d_gokurou(cv, st):
        th = cv.th
        cv.title("「ご苦労様」がたどった道", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(1), 0.6)
        cv.text((420, 230), "江戸期の用例", th.size_body, bold=True, alpha=a, anchor="ma")
        lit = ramp(st.t, st.at(1) + 0.8, 1.5)
        for k in range(23):
            r, c = divmod(k, 6)
            x, y = 420 - 2.5 * 70 + c * 70, 320 + r * 80
            col = th.accent if k < 20 else th.muted
            col = mix(col, th.muted, lit) if k < 20 else col
            icon(cv, "user", x, y, 58, col, a)
        cv.text((420, 660), "23例中20例", th.size_title, bold=True, color=th.accent, alpha=lit, anchor="ma")
        cv.text((420, 735), "敬意を払う相手へ", 30, color=th.sub, alpha=lit, anchor="ma")
        # 右側の年表
        X = year_axis(cv, 860, W - M - 40, 560, 1970, 2010, 10, ramp(st.t, st.at(2), 0.5))
        event(cv, X(1976), 560, True, "book", 1976, ["敬語の本が", "「目上に失礼」"], ramp(st.t, st.at(2), 0.6), color=th.accent)
        event(cv, X(1988), 560, False, "notebook", N["dict_first"], ["国語辞典に", "注記が載る"], ramp(st.t, st.at(3), 0.6))
        event(cv, X(2007), 560, True, "building-bank", 2007, ["国の「敬語の指針」", "「用いない方が良い」"],
              ramp(st.t, st.at(3) + 2.0, 0.6))
        cv.note("倉持（2011）『明海日本語』16。江戸期は小咄・滑稽本・落語などの23例。文化審議会「敬語の指針」（2007）",
                ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("ご苦労様", [
        Line("同じような道をたどった言葉が、もう一つあります。「ご苦労様」です。",
             "同じような道をたどった言葉が、もう一つあります。ご苦労様、です。"),
        Line("江戸時代の小咄や落語などに残る用例を集めた研究では、23例のうち20例が、敬意を払うべき相手に向けたものでした。"),
        Line("目上の人には失礼だ、という記述で確認できる最も古いものは、1976年の敬語の本です。"),
        Line("1988年からは国語辞典にも注記が載り、2007年には国の「敬語の指針」も、目上には用いない方が良い、としました。",
             "1988年からは国語辞典にも注記が載り、2007年には国の、敬語の指針も、目上には用いない方が良い、としました。"),
    ], d_gokurou, tail=1.6))

    # 2006年調査 -----------------------------------------------------------
    def d_h17(cv, st):
        th = cv.th
        cv.title("仕事を終えた相手に掛ける言葉", ramp(st.t, 0, 0.4))
        phrases = ["お疲れ様（でした）", "御苦労様（でした）", "ありがとう（ございました）"]
        for k, (tgt, lab, ic) in enumerate((("superior", "職階が上の人に", "arrow-up"), ("subordinate", "職階が下の人に", "arrow-down"))):
            a = ramp(st.t, st.at(0) + (0 if k == 0 else 2.5), 0.6)
            x0 = M + 40 + k * 860
            icon(cv, ic, x0 + 30, 250, 48, th.text, a)
            cv.text((x0 + 70, 250), lab, th.size_body, bold=True, alpha=a, anchor="lm")
            vals = [N["h17"][(tgt, p)] for p in phrases]
            p = ramp(st.t, st.at(0) + (0.5 if k == 0 else 3.0), 1.0)
            cols = [th.compare, th.accent, th.muted]
            for j, (ph, v) in enumerate(zip(phrases, vals)):
                y = 340 + j * 130
                cv.text((x0, y), ph, 30, alpha=a, anchor="lm")
                bx = x0
                w = 600 * v / 100 * p
                cv.rect((bx, y + 26, bx + w, y + 72), cols[j], a)
                if p > 0.8:
                    cv.text((bx + w + 14, y + 49), f"{v:.1f}%", 32, bold=True, alpha=a, anchor="lm")
        cv.note("文化庁 平成17年度「国語に関する世論調査」（2006年2〜3月、16歳以上、個別面接、有効回答2,107人）",
                ramp(st.t, st.at(0), 0.6))

    scenes.append(Scene("2006年の調査", [
        Line("2006年の文化庁の調査では、仕事を終えた上司に掛ける言葉として、「お疲れ様」を選んだ人が約7割、「御苦労様」は約15%でした。",
             "2006年の文化庁の調査では、仕事を終えた上司に掛ける言葉として、お疲れ様、を選んだ人が約7割、ごくろうさま、は約15%でした。"),
        Line("根拠の弱いルールでも、広まったあとでは、実際に多くの人が従う慣習になります。"),
    ], d_h17, tail=1.8))

    # 広まり方 ---------------------------------------------------------------
    loop = [("book", "マナー本が", "「失礼」と書く"), ("notebook", "辞書が", "注記を加える"),
            ("world-www", "ウェブ記事が", "繰り返す"), ("presentation", "研修で", "教えられる")]

    def d_loop(cv, st):
        th = cv.th
        cv.title("「失礼」が広まる流れ", ramp(st.t, 0, 0.4))
        cy, rx, ry = 520, 520, 230
        pos = []
        for k in range(4):
            ang = math.radians(-90 + k * 90)
            pos.append((CX + math.cos(ang) * rx, cy + math.sin(ang) * ry))
        apps = [ramp(st.t, st.at(1) + 0.9 * k, 0.6) for k in range(4)]
        for k, ((ic, l1, l2), (x, y), a) in enumerate(zip(loop, pos, apps)):
            card(cv, (x - 150, y - 90, x + 150, y + 90), a)
            icon(cv, ic, x, y - 34, 56, th.text, a)
            cv.text((x, y + 8), l1, 28, bold=True, alpha=a, anchor="ma")
            cv.text((x, y + 44), l2, 26, color=th.sub, alpha=a, anchor="ma")
        for k in range(4):
            (xa, ya), (xb, yb) = pos[k], pos[(k + 1) % 4]
            al = apps[(k + 1) % 4] if k < 3 else ramp(st.t, st.at(3), 0.6)
            dx, dy = xb - xa, yb - ya
            d = math.hypot(dx, dy)
            ux, uy = dx / d, dy / d
            arrow_to(cv, (xa + ux * 200, ya + uy * 120), (xb - ux * 200, yb - uy * 120), al, th.accent, 5)
        c = ramp(st.t, st.at(2), 0.6)
        card(cv, (CX - 210, cy - 50, CX + 210, cy + 50), c, th.accent, 50)
        cv.text((CX, cy), "守らないと失礼だと思われる", 30, bold=True, color=(255, 255, 255), alpha=c, anchor="mm")
        cv.note("「了解」「ご苦労様」の2例で文献から確認できた順序（髙橋ほか 2018、倉持 2011）。ほかのマナーで同じかは未確認",
                ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("広まり方", [
        Line("二つの例には、共通する流れがあります。"),
        Line("本が失礼だと書き、辞書が注記を加え、ウェブの記事や研修が、それを繰り返す。"),
        Line("やがて、守らない人は、本当に失礼だと思われるようになります。"),
        Line("ルールが広まったこと自体が、ルールを守る理由になっていくのです。"),
    ], d_loop, tail=1.6))

    # 第4章 ---------------------------------------------------------------
    scenes.append(chapter(4, "では、守る必要はあるのか？",
                          "では、こうして広まったマナーを、守る必要はあるのでしょうか。"))

    # 二つの判断 -------------------------------------------------------------
    def d_two(cv, st):
        th = cv.th
        cv.title("二つの判断を分ける", ramp(st.t, st.at(0), 0.4))
        for k, (ic, head, sub, quote, ok) in enumerate((
                ("user-check", "自分がどう言うか", "実用的な判断", "気にする人が多いなら\n「承知しました」と言っておこう", "言い換えの手間は小さい"),
                ("user-exclamation", "他人を責めるか", "規範的な判断", "「了解しました」と言う人は\n失礼だ", "別の理由が必要"))):
            a = ramp(st.t, st.at(1 if k == 0 else 3), 0.6)
            x = CX - 440 + k * 880
            card(cv, (x - 380, 220, x + 380, 800), a)
            icon(cv, ic, x, 320, 110, th.accent if k == 0 else th.text, a)
            cv.text((x, 410), head, th.size_body, bold=True, alpha=a, anchor="ma")
            cv.text((x, 468), sub, 28, color=th.sub, alpha=a, anchor="ma")
            for j, ln in enumerate(quote.split("\n")):
                cv.text((x, 560 + j * 46), ln, 32, alpha=a, anchor="ma")
            b = ramp(st.t, st.at(2 if k == 0 else 4), 0.6)
            cv.text((x, 720), ok, 32, bold=True, color=th.accent, alpha=b, anchor="ma")

    scenes.append(Scene("二つの判断", [
        Line("ここで、二つの判断を分けておきます。"),
        Line("一つは、「気にする人が多いなら、自分は承知しましたと言っておこう」という判断です。",
             "一つは、気にする人が多いなら、自分は、承知しましたと言っておこう、という判断です。"),
        Line("言い換える手間は小さく、余計な誤解も避けられるので、これは実用的に筋が通っています。"),
        Line("もう一つは、「了解しましたと言う人は失礼だ」と、他人を責める判断です。",
             "もう一つは、了解しましたと言う人は失礼だ、と、他人を責める判断です。"),
        Line("こちらには、慣習が広まっているという事実とは別に、それを正当化する理由が必要になります。"),
    ], d_two, tail=1.4))

    # 四つの問い -------------------------------------------------------------
    qs = [("mood-confused", "不快に感じる人がいれば", "禁止する理由になるか", "その不快感がルールの広まりから\n生まれたなら、理由は循環する"),
          ("user-question", "慣習を知らない人に", "求めてよいか", "2002年までの本になかったルールを\n新しく働く人は知りようがない"),
          ("scale", "負担と利益は", "釣り合っているか", "言い換えは小さな負担。席次のように\n下の立場だけが負う決まりもある"),
          ("route", "もっと簡単な方法は", "ないか", "敬意を伝えるのが目的なら\n「了解いたしました」でも伝わる")]

    def d_four(cv, st):
        th = cv.th
        cv.title("他人に求める理由は成り立つか", ramp(st.t, st.at(0), 0.4))
        cw, chh = 780, 300
        for k, (ic, q1, q2, ans) in enumerate(qs):
            r, c = divmod(k, 2)
            x = CX - cw - 20 + c * (cw + 40)
            y = 190 + r * (chh + 30)
            a = ramp(st.t, st.at(1 + 2 * k) if 1 + 2 * k < len(st.starts) else st.at(-1), 0.6)
            card(cv, (x, y, x + cw, y + chh), a)
            icon(cv, ic, x + 70, y + 72, 64, th.accent, a)
            cv.text((x + 130, y + 50), q1, 32, bold=True, alpha=a)
            cv.text((x + 130, y + 92), q2, 32, bold=True, alpha=a)
            b = ramp(st.t, st.at(2 + 2 * k) if 2 + 2 * k < len(st.starts) else st.at(1 + 2 * k) + 0.8, 0.6)
            for j, ln in enumerate(ans.split("\n")):
                cv.text((x + 50, y + 170 + j * 44), ln, 29, color=th.sub, alpha=b)

    scenes.append(Scene("四つの問い", [
        Line("では、他人に求める理由は、どこまで成り立つでしょうか。"),
        Line("まず、不快に感じる人がいるから、という理由です。"),
        Line("その不快感が、ルールが広まった結果として生まれたものなら、理由は循環してしまいます。"),
        Line("次に、慣習を知らない人に求めてよいのか。"),
        Line("2002年までの本には書かれていなかったルールを、新しく働き始めた人が、自然に知る方法はありません。"),
        Line("負担と利益はどうでしょう。"),
        Line("言い換えの手間は小さくても、席次のように、立場が下の人だけが毎回気を配る決まりもあります。"),
        Line("そして、目的が敬意を伝えることなら、「了解いたしました」でも伝わります。",
             "そして、目的が敬意を伝えることなら、了解いたしました、でも伝わります。"),
    ], d_four, tail=1.8))

    # 中核と細部 -------------------------------------------------------------
    rows3 = [("id-badge-2", "名刺交換", "名前と連絡先を正確に渡す", "渡す順番・高さ・名刺入れの扱い",
              "名刺は江戸時代からある。交換の手順の初出は未確認"),
             ("user", "お辞儀", "敬意を示す", "15°・30°・45°の角度の区別",
              "戦前の武道に角度の規定。ビジネスの3段階の初出は未確認"),
             ("elevator", "席次", "来客を落ち着いた席へ案内する", "エレベーターやタクシーの立ち位置",
              "床の間の前を上座とする慣行から。乗り物の順位は西洋の右上位に倣うとされる")]

    def d_core(cv, st):
        th = cv.th
        cv.title("役割のある中心と、根拠の見えない細部", ramp(st.t, 0, 0.4))
        hx0, hx1 = 760, 1340
        h = ramp(st.t, st.at(0), 0.6)
        cv.text((hx0 + 0, 220), "中心の役割", 30, bold=True, color=th.accent, alpha=h, anchor="ma")
        cv.text((hx1 + 0, 220), "細かな手順", 30, bold=True, color=th.compare, alpha=h, anchor="ma")
        for k, (ic, name, core, detail, src) in enumerate(rows3):
            a = ramp(st.t, st.at(1) if k == 0 else st.at(2) + 2.2 * (k - 1), 0.6)
            y = 330 + k * 170
            card(cv, (M, y - 70, W - M, y + 80), a)
            icon(cv, ic, M + 70, y - 8, 64, th.text, a)
            cv.text((M + 130, y - 8), name, 36, bold=True, alpha=a, anchor="lm")
            cv.text((hx0, y - 8), core, 30, alpha=a, anchor="mm")
            cv.text((hx1, y - 8), detail, 30, color=th.sub, alpha=a, anchor="mm")
            cv.text((M + 130, y + 46), src, 22, color=th.sub, alpha=a, anchor="lm")
        cv.note("国立国会図書館月報636号（2014）、中嶋（2021）、nippon.com（2024、監修：柴崎直人）。細部の効果を調べた研究は見つからなかった",
                ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("中核と細部", [
        Line("すべてのマナーが、同じように根拠を欠いているわけではありません。"),
        Line("名刺交換には、名前と連絡先を正確に渡すという、はっきりした役割があります。"),
        Line("お辞儀は敬意を示し、席次には、来客を落ち着いた席へ案内する意味があります。"),
        Line("根拠が見つからないのは、渡す順番やお辞儀の角度、エレベーターでの立ち位置といった、細かな手順のほうです。"),
        Line("ただし、効果を調べた研究が見つからないことは、効果がないことを意味しません。"),
    ], d_core, tail=1.6))

    # 慣習の働き -------------------------------------------------------------
    def d_conv(cv, st):
        th = cv.th
        cv.title("慣習には慣習の働きがある", ramp(st.t, st.at(0), 0.4))
        a = ramp(st.t, st.at(1), 0.6)
        # 左：同じ期待をそろえた人たち
        for k in range(5):
            x = 260 + k * 110
            icon(cv, "user", x, 470, 90, th.accent, ramp(st.t, st.at(1) + 0.15 * k, 0.5))
            icon(cv, "check", x, 370, 40, th.accent, ramp(st.t, st.at(1) + 0.6 + 0.15 * k, 0.5))
        cv.text((480, 580), "期待がそろうと迷わない", 32, bold=True, alpha=a, anchor="ma")
        cv.text((480, 630), "起源が偶然でも意味が生まれる", 28, color=th.sub, alpha=ramp(st.t, st.at(2), 0.6), anchor="ma")
        # 右：内心は不要と思っていても続く
        b = ramp(st.t, st.at(3), 0.6)
        for k in range(5):
            x = 1220 + k * 110
            icon(cv, "user", x, 470, 90, th.compare, b)
            icon(cv, "question-mark", x, 370, 40, th.compare, ramp(st.t, st.at(3) + 0.6 + 0.15 * k, 0.5))
        cv.text((1440, 580), "内心は不要と思っていても", 32, bold=True, alpha=b, anchor="ma")
        cv.text((1440, 630), "規範は消えにくい", 28, color=th.sub, alpha=b, anchor="ma")
        cv.line([(CX, 300), (CX, 700)], th.grid, 2, b)
        cv.note("Lewis（1969）の慣習論、Bicchieri ほか「Social Norms」Stanford Encyclopedia of Philosophy（2023改訂）",
                ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("慣習の働き", [
        Line("ただし、慣習には、慣習の働きがあります。"),
        Line("みんなが同じやり方を期待していれば、迷わずに済み、誤解も減ります。"),
        Line("始まりが偶然でも、共有されたあとには意味が生まれる。だから、起源が新しいというだけで、マナーを無意味とは言えません。"),
        Line("一方で、多くの人が内心では不要だと思っていても、規範はなかなか消えないことも知られています。"),
    ], d_conv, tail=1.4))

    # 働く人の評価 -----------------------------------------------------------
    def d_survey(cv, st):
        th = cv.th
        cv.title("働く人が「重要」と考えるマナー", ramp(st.t, 0, 0.4))
        need = N["en_need"]["必要"] + N["en_need"]["どちらかと言えば必要"]
        a = ramp(st.t, st.at(1), 0.6)
        cv.text((330, 300), f"{need}%", th.size_number, bold=True, color=th.accent, alpha=a, anchor="ma")
        cv.text((330, 450), "マナーは必要", th.size_body, bold=True, alpha=a, anchor="ma")
        cv.text((330, 505), "敬意・信頼関係 77%", 28, color=th.sub, alpha=a, anchor="ma")
        cv.text((330, 545), "円滑なコミュニケーション 68%", 28, color=th.sub, alpha=a, anchor="ma")
        imp = dict(N["en_imp"])
        keys = ["挨拶", "言葉遣い（敬語）", "報告・連絡・相談", "名刺交換", "上座・下座"]
        vals = [imp[k] for k in keys]
        p = [ramp(st.t, st.at(2) + 0.25 * k, 0.8) if k < 3 else ramp(st.t, st.at(3) + 0.3 * (k - 3), 0.8) for k in range(5)]
        cols = [th.accent] * 3 + [th.compare] * 2
        hbars(cv, (700, 230, W - M, 760), keys, vals, p, vmax=100, fmt="{}%", label_w=340, size=34, colors=cols)
        cv.note("エン株式会社「ビジネスマナーに関する意識調査」（2025年9月、転職サイト利用者1,435名）。重要なものは「必要」と答えた人の複数回答",
                ramp(st.t, st.at(1), 0.6))

    scenes.append(Scene("働く人の評価", [
        Line("働く人たちは、マナーをどう見ているのでしょうか。"),
        Line("ある調査では、ほとんどの人がマナーは必要だと答え、その理由の多くは、相手への敬意と、円滑なコミュニケーションでした。"),
        Line("重要だとされたのは、挨拶、言葉遣い、そして報告・連絡・相談。",
             "重要だとされたのは、挨拶、言葉遣い、そして、報告、連絡、相談。"),
        Line("名刺交換や席次を挙げた人は、4人に1人ほどです。"),
        Line("目的がはっきりした作法と、手順そのものの作法とを、人々は分けて見ているのかもしれません。"),
    ], d_survey, tail=1.8))

    # 第5章 ---------------------------------------------------------------
    scenes.append(chapter(5, "私たちは何に従っているのか？",
                          "最後に、ここまでの話をまとめます。"))

    # まとめ ---------------------------------------------------------------
    def d_sum(cv, st):
        th = cv.th
        a = ramp(st.t, st.at(0), 0.6)
        for k, (ic, lab, _) in enumerate(actors):
            x = CX - 5 * 120 + k * 240
            icon(cv, ic, x, 260, 64, th.text, ramp(st.t, st.at(0) + 0.2 * k, 0.5))
            cv.text((x, 310), lab, 26, alpha=ramp(st.t, st.at(0) + 0.2 * k, 0.5), anchor="ma")
        b = ramp(st.t, st.at(1), 0.6)
        for k, (head, sub, c) in enumerate((("目的が見える作法", "挨拶・報連相・深夜の連絡を控える", th.accent),
                                            ("根拠が弱い「失礼」", "「了解」「ご苦労様」", th.compare))):
            x = CX - 420 + k * 840
            card(cv, (x - 360, 400, x + 360, 540), b)
            cv.text((x, 430), head, 34, bold=True, color=c, alpha=b, anchor="ma")
            cv.text((x, 486), sub, 28, color=th.sub, alpha=b, anchor="ma")
        q = ramp(st.t, st.at(2), 0.6)
        if q > 0:
            cv.rect((M + 80, 600, W - M - 80, 830), (255, 255, 255), q, 16)
            cv.rect((M + 80, 600, M + 92, 830), th.accent, q)
            icon(cv, "quote", M + 160, 650, 48, th.accent, q)
            cv.text((M + 210, 640), "マニュアルによって敬語の使い方を指導する場合にも、また敬語の使い方を習得する場合にも、", 28, alpha=q)
            cv.text((M + 210, 690), "そこに示された内容を唯一絶対のものとして扱うことを避ける態度が必要である。", 32, bold=True, alpha=q)
            cv.text((W - M - 120, 770), "文化審議会答申「敬語の指針」（2007年）", 26, color=th.sub, alpha=q, anchor="ra")

    scenes.append(Scene("まとめ", [
        Line("歴史をたどると、職場のマナーは、経営者の団体、検定、航空会社、出版、そしてウェブと、多くの担い手によって広められてきました。"),
        Line("その中には、相手への配慮という目的がはっきりした作法もあれば、根拠が後から付けられたように見える「失礼」もあります。",
             "その中には、相手への配慮という目的がはっきりした作法もあれば、根拠が後から付けられたように見える、失礼、もあります。"),
        Line("国の敬語の指針は、マニュアルに示された言葉を、唯一絶対のものとして扱わない態度が必要だ、と書いています。"),
    ], d_sum, tail=2.4))

    # 問い ---------------------------------------------------------------
    def d_q(cv, st):
        th = cv.th
        a = ramp(st.t, st.at(0), 0.6)
        cv.text((CX, 260), "今回確かめたのは代表的な例。すべてのマナーで同じことが起きたとは言えない", 30, color=th.sub, alpha=a, anchor="ma")
        b = ramp(st.t, st.at(2), 0.8)
        cv.text((CX, 420), "相手への配慮のためのマナーが、", th.size_title, bold=True, alpha=b, anchor="ma")
        cv.text((CX, 510), "いつの間にか、相手に従わせるための", th.size_title, bold=True, alpha=b, anchor="ma")
        cv.text((CX, 600), "ルールになっていないだろうか？", th.size_title, bold=True, color=th.accent, alpha=b, anchor="ma")
        c = ramp(st.t, st.at(3), 0.6)
        icon(cv, "search", CX - 300, 760, 56, th.text, c)
        cv.text((CX - 250, 760), "その「失礼」は、いつ、誰が言い始めたのか", 34, bold=True, alpha=c, anchor="lm")

    scenes.append(Scene("問い", [
        Line("今回確かめられたのは、いくつかの代表的な例です。すべてのマナーで同じことが起きたとは言えません。"),
        Line("それでも、問いは残ります。"),
        Line("相手への配慮のためのマナーが、いつの間にか、相手に従わせるためのルールになっていないでしょうか。"),
        Line("目的の見えない「失礼」に出会ったら、それがいつ、誰によって言われ始めたのかを、確かめてみてもいいのかもしれません。",
             "目的の見えない、失礼、に出会ったら、それがいつ、誰によって言われ始めたのかを、確かめてみてもいいのかもしれません。"),
    ], d_q, tail=3.0))

    # 出典とクレジット --------------------------------------------------------
    refs = ["髙橋圭子・東泉裕子・佐藤万里（2018）国立国語研究所『言語資源活用ワークショップ2018発表論文集』",
            "倉持益子（2011）「『御苦労』系労い言葉の変遷」『明海日本語』16",
            "文化審議会答申「敬語の指針」（2007）／文化庁 平成17年度「国語に関する世論調査」",
            "長船亜紀子（2023）千葉大学博士論文／山口誠（2020）『客室乗務員の誕生』岩波新書",
            "中嶋哲也（2021）『体育学研究』66／国立国会図書館サーチの書誌／エン株式会社（2025）調査"]

    def d_credit(cv, st):
        th = cv.th
        a = ramp(st.t, 0.2, 0.6)
        cv.text((CX, 150), "主な出典", th.size_body, bold=True, alpha=a, anchor="ma")
        for k, r in enumerate(refs):
            cv.text((CX, 230 + k * 50), r, 26, alpha=a, anchor="ma")
        cv.text((CX, 540), "全出典は概要欄に記載", 26, color=th.sub, alpha=a, anchor="ma")
        for k, c in enumerate([voice_credit, music_credit, icon_credit]):
            cv.text((CX, 660 + k * 50), c, 26, color=th.sub, alpha=a, anchor="ma")

    scenes.append(Scene("出典", [], d_credit, lead=7.0, tail=0.0))
    return scenes
