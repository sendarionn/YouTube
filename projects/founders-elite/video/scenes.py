"""動画「上場した創業者は、何歳で起業したのか」の台本と画面

方針（AGENTS.md「ナレーションと映像の役割分担」「映像表現とテキスト量」）
- ナレーションは要点・解釈・結論。読み上げる数値は中心となるもの（33歳、10年、約10歳）に限る
- 細かな数値・分母・定義・出典は画面のラベルと注記で示す
- 画面はドット図、ピクトグラム、アイコンの関係図、年表で構成し、文章は表示しない

数値は data/summary.json・data/founders.csv・data/external_stats.json から読み込む（手入力の数値を置かない）
"""
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
sys.path.insert(0, str(REPO))

from tools.infographic import icons as ic  # noqa: E402
from tools.infographic.canvas import mix, ramp  # noqa: E402
from tools.infographic.video import Line, Scene  # noqa: E402
from cases_scenes import build_cases, load_cases  # noqa: E402

DATA = PROJECT / "data"
W, H, M = 1920, 1080, 120


def load_numbers():
    S = json.load(open(DATA / "summary.json", encoding="utf-8"))
    E = json.load(open(DATA / "external_stats.json", encoding="utf-8"))["jfc_2025"]["values"]
    f = pd.read_csv(DATA / "founders.csv", dtype=str).fillna("")
    car = f[(f.target_20y == "Y") & (f.name != "") & (f.career_p1 != "")]
    age = pd.to_numeric(car.age_at_founding, errors="coerce")
    yb = pd.to_numeric(car.years_before, errors="coerce")
    N = {
        "listings": S["listings_total"],
        "technical": S["technical"],
        "target": S["target_20"],
        "founders_named": S["founders_named_target20"],
        "career_known": S["career_known"],
        "ages": [int(a) for a in age.dropna()],
        "ybs": [int(y) for y in yb.dropna()],
        "age_median": age.median(),
        "age_mean": round(age.mean(), 1),
        "le29_pct": round(100 * (age <= 29).mean(), 1),
        "student_n": int((car.student_founder == "Y").sum()),
        "student_pct": S["student_founder_pct"],
        "yb_n": int(yb.notna().sum()),
        "yb_median": yb.median(),
        "large_n": int((car.large_org == "Y").sum()),
        "large_pct": S["large_org_pct_among_known"],
        "cats": S["career_categories_pct"],
        "jfc_mean": E["mean_age_at_opening"]["value"],
        "jfc_le29": E["age_29_or_under_pct"]["value"],
        "jfc_emp": E["employees_at_opening_mean"]["value"],
    }
    # 集計ファイル同士の整合性（不一致なら描画しない）
    assert len(car) == N["career_known"] == len(N["ages"])
    assert sum(S["years_before_bins"].values()) == N["yb_n"] == len(N["ybs"])
    assert round(100 * N["student_n"] / N["career_known"], 1) == N["student_pct"]
    assert round(100 * N["large_n"] / N["career_known"], 1) == N["large_pct"]
    assert N["age_median"] == S["age_at_founding_median"] and N["age_mean"] == S["age_at_founding_mean"]
    return N


def pf(x):
    """割合・平均は小数1桁で表示する（6.0% を 6% と出さない）"""
    return f"{x:.1f}"


def axis(cv, x0, x1, y, vmin, vmax, X, step, unit, alpha=1.0):
    th = cv.th
    cv.line([(x0, y), (x1, y)], th.grid, 3, alpha)
    first = vmin + (-vmin) % step
    for v in range(first, vmax + 1, step):
        cv.text((X(v), y + 12), f"{v}{unit}", th.size_note, color=th.sub, alpha=alpha, anchor="ma")


def median_mark(cv, x, y_top, y_bot, label, alpha):
    th = cv.th
    cv.line([(x, y_top), (x, y_bot)], th.text, 3, alpha)
    cv.text((x, y_top - 12), label, th.size_body + 8, bold=True, alpha=alpha, anchor="md")


# 職歴の分類のうち「大手組織」に数えたもの（methodology.md）とアイコン
LARGE_CATS = [("finance", "金融", "bank"), ("jp_large_maker_infra", "国内大手メーカー・インフラ", "factory"),
              ("consulting", "コンサル", "presentation"), ("net_megaventure", "ネット大手", "browser"),
              ("foreign_tech", "外資系IT", "browser"), ("trading", "総合商社", "briefcase")]


def build(N, voice_credit, music_credit=""):
    jfc_gap = round(N["jfc_mean"] - N["age_mean"])

    # 1 導入
    def d_intro(cv, st):
        th = cv.th
        a = ramp(st.t, st.at(0), 0.6)
        ic.person(cv, 640, 450, 260, th.text, a, cap=True)
        b = ramp(st.t, st.at(0) + 1.0, 0.6)
        cv.line([(800, 450), (1060, 450)], th.sub, 6, b)
        if b > 0:
            cv.d.polygon([(1090, 450), (1050, 430), (1050, 470)], fill=mix(th.sub, th.bg, b))
        ic.chart_up(cv, 1260, 450, 240, th.accent, b)
        q = ramp(st.t, st.at(2), 0.6)
        cv.text((W // 2, 760), "上場した創業者は、何歳で起業したのか", th.size_title, bold=True, alpha=q, anchor="ma")

    intro = Scene("導入", [
        Line("学生のうちに会社を立ち上げて、若くして成功する。"),
        Line("起業家と聞くと、そんな姿を思い浮かべる人も多いかもしれません。"),
        Line("では、実際に上場するまで会社を育てた創業者は、何歳で、どんな道を通って起業したのでしょうか。"),
    ], d_intro, lead=0.8, tail=1.2)

    # 2 調べた対象：1社＝1マス
    cols, cell = 45, 26
    n_tech, n_target = N["technical"], N["target"]
    n_other = N["listings"] - n_tech - n_target

    def d_scope(cv, st):
        th = cv.th
        cv.title("調べた会社", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0), 1.5)
        b = ramp(st.t, st.at(1), 0.8)
        x0, y0 = M, 200
        shown = int(N["listings"] * a)
        for k in range(shown):
            r, c = divmod(k, cols)
            if k < n_target:
                col = mix(th.accent, th.muted, b)
            elif k < n_target + n_other:
                col = th.muted
            else:
                col = mix(th.bg, th.muted, b * 0.75)
            x, y = x0 + c * cell, y0 + r * cell
            cv.d.rectangle((x, y, x + cell - 5, y + cell - 5), fill=col)
        lx = x0 + cols * cell + 40
        a2 = min(1.0, a * 2)
        cv.text((lx, 220), "東証の新規上場 2016–2025年", th.size_note + 4, color=th.sub, alpha=a2)
        cv.text((lx, 260), f"{N['listings']}社", th.size_title, bold=True, alpha=a2)
        cv.text((lx, 380), "個人創業・独立・大学発、創業20年以内", th.size_note + 4, color=th.accent, alpha=b)
        cv.text((lx, 420), f"{n_target}社", th.size_title, bold=True, color=th.accent, alpha=b)
        c2 = ramp(st.t, st.at(2), 0.6)
        ic.sheet(cv, lx + 45, 620, 110, th.text, c2)
        for k in range(5):
            ic.person(cv, lx + 150 + k * 50, 620, 60, th.accent, c2)
        cv.text((lx, 700), f"創業者 {N['founders_named']}人", th.size_body, bold=True, alpha=c2)
        cv.text((lx, 755), f"生年・職歴が判明 {N['career_known']}人", th.size_note + 4, alpha=c2)
        cv.note(f"1マス＝1社。薄いマスはテクニカル上場（{n_tech}社）、灰色は子会社・古い会社など対象外。上場企業の創業者だけの集計",
                ramp(st.t, st.at(3), 0.6))

    scope = Scene("調査対象", [
        Line("調べたのは、過去10年間に、東京証券取引所に上場した会社です。"),
        Line("そのうち、個人が立ち上げた会社などで、創業から20年以内に上場した会社に絞りました。"),
        Line("創業者の生まれた年と職歴を、上場の申請書類から集めています。"),
        Line("これは上場まで届いた会社だけの話で、起業した人全体を表すものではありません。"),
    ], d_scope)

    # 3 創業時の年齢：1人＝1点
    amin, amax = 18, 66
    box_age = (M + 40, 300, W - M - 40, 820)

    def d_age(cv, st):
        th = cv.th
        cv.title("創業したときの年齢", ramp(st.t, 0, 0.4))
        p = ramp(st.t, st.at(1) - 0.3, 3.0)
        hl = ramp(st.t, st.at(3), 0.8)

        def color_of(v):
            return th.accent if v <= 29 else mix(th.muted, th.accent, hl)
        X, _ = ic.dot_hist(cv, box_age, N["ages"], amin, amax, p, color_of=color_of)
        axis(cv, box_age[0], box_age[2], box_age[3] + 8, amin, amax, X, 5, "歳", ramp(st.t, st.at(0), 0.5))
        m = ramp(st.t, st.at(2), 0.6)
        median_mark(cv, X(N["age_median"]), 290, box_age[3], f"中央値 {N['age_median']:g}歳", m)
        cv.text((W - M, 230), f"平均 {pf(N['age_mean'])}歳", th.size_body, alpha=m, anchor="ra")
        h = ramp(st.t, st.at(3), 0.6)
        cv.text((X(22), 330), "29歳以下", th.size_note + 6, color=th.accent, alpha=h, anchor="ma")
        cv.text((X(22), 370), f"{pf(N['le29_pct'])}%", th.size_title, bold=True, color=th.accent, alpha=h, anchor="ma")
        cv.note(f"1点＝1人（{N['career_known']}人）。年齢＝創業年−生年。創業年は前身の個人事業を含む事業の起点",
                ramp(st.t, st.at(1), 0.6))

    age = Scene("年齢", [
        Line("まず、創業したときの年齢です。"),
        Line("点の一つ一つが、創業者一人を表しています。"),
        Line(f"多いのは20代の後半から30代で、中央値は{N['age_median']:g}歳でした。"),
        Line("20代のうちに起業した人も、3人に1人ほどいます。"),
    ], d_age, tail=1.6)

    # 4 学生起業に近い人：100人のピクトグラム
    def d_student(cv, st):
        th = cv.th
        cv.title("学生のうちに起業したとみられる人", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0), 0.6)
        gx = (W - (700 + 120 + 460)) / 2
        ic.people_grid(cv, (gx, 190, gx + 700, 850), 100, round(N["student_pct"]), 10,
                       ramp(st.t, st.at(1), 1.2), alpha=a, cap_on=True)
        b = ramp(st.t, st.at(1) + 1.0, 0.6)
        nx = gx + 700 + 120 + 230
        cv.text((nx, 360), f"{pf(N['student_pct'])}%", th.size_number + 40, bold=True, color=th.accent, alpha=b, anchor="ma")
        cv.text((nx, 540), f"{N['student_n']}人 / {N['career_known']}人", th.size_body, alpha=b, anchor="ma")
        cv.note("1人の形＝1%。役員略歴に勤務先がなく、創業時25歳以下の人。在学中かは未確認。アルバイト等は略歴に載らない",
                ramp(st.t, st.at(2), 0.6))

    student = Scene("学生起業", [
        Line("一方で、学生のうちに起業したとみられる人は、ごく一部です。"),
        Line("役員の経歴に勤務先が一つもなく、20代半ばまでに創業した人は、100人に6人ほどでした。"),
        Line("経歴から判断したもので、在学中だったかどうかまでは確かめていません。"),
    ], d_student, tail=1.4)

    # 5 最初の就職から創業まで：1人＝1点
    ymin, ymax = 0, 40
    box_y = (M + 40, 300, W - M - 40, 820)

    def d_years(cv, st):
        th = cv.th
        cv.title("最初の就職から創業までの年数", ramp(st.t, 0, 0.4))
        p = ramp(st.t, st.at(1) - 0.5, 3.0)
        X, _ = ic.dot_hist(cv, box_y, N["ybs"], ymin, ymax, p)
        axis(cv, box_y[0], box_y[2], box_y[3] + 8, ymin, ymax, X, 5, "年", ramp(st.t, st.at(0), 0.5))
        m = ramp(st.t, st.at(1) + 1.0, 0.6)
        median_mark(cv, X(N["yb_median"]), 290, box_y[3], f"中央値 {N['yb_median']:g}年", m)
        b = ramp(st.t, st.at(0), 0.6)
        ic.briefcase(cv, X(0), 210, 70, th.sub, b)
        cv.text((X(0) + 50, 210), "就職", th.size_note + 4, color=th.sub, alpha=b, anchor="lm")
        ic.flag(cv, X(30), 210, 80, th.sub, b)
        cv.text((X(30) + 40, 210), "創業", th.size_note + 4, color=th.sub, alpha=b, anchor="lm")
        cv.line([(X(0) + 130, 210), (X(30) - 40, 210)], th.grid, 3, b)
        cv.note(f"1点＝1人（初職の年が分かった{N['yb_n']}人）。初職＝創業前の最初の入社・入行など。転職や別の起業の期間を含む",
                ramp(st.t, st.at(3), 0.6))

    years = Scene("職歴の年数", [
        Line("では、多くの人は、創業する前に何をしていたのでしょうか。"),
        Line(f"最初に就職してから創業するまでの年数は、中央値で{N['yb_median']:g}年でした。"),
        Line("会社などで数年から十数年働いてから、自分の会社を立ち上げた人が中心です。"),
        Line("この年数には、転職や、別の会社を立ち上げた期間も含まれます。"),
    ], d_years, tail=1.4)

    # 6 創業前の勤務先
    def d_employer(cv, st):
        th = cv.th
        cv.title("創業前に働いていた組織", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(1), 0.6)
        ic.people_grid(cv, (M, 200, M + 560, 760), 100, round(N["large_pct"]), 10, ramp(st.t, st.at(1), 1.2), alpha=a)
        cv.text((M + 280, 780), f"{pf(N['large_pct'])}%（{N['large_n']}人）", th.size_body, bold=True, color=th.accent,
                alpha=ramp(st.t, st.at(1) + 1.0, 0.6), anchor="ma")
        x0 = 860
        for k, (key, lab, icon_name) in enumerate(LARGE_CATS):
            p = ramp(st.t, st.at(1) + 1.2 + 0.25 * k, 0.6)
            y = 250 + k * 95
            ic.icon(cv, icon_name, x0, y, 64, th.text, p)
            cv.text((x0 + 60, y), lab, th.size_note + 2, alpha=p, anchor="lm")
            bx = x0 + 420
            w = 480 * N["cats"][key] / 20 * p
            cv.rect((bx, y - 18, bx + w, y + 18), th.accent, p)
            cv.text((bx + w + 14, y), f"{pf(N['cats'][key])}%", th.size_note + 2, bold=True, alpha=p, anchor="lm")
        cv.note("1人の形＝1%。一人が複数に該当。分類は社名による機械的な判定で、勤務当時の規模は確認していない",
                ramp(st.t, st.at(2), 0.6))

    employer = Scene("勤務先", [
        Line("創業前に働いていた組織も見てみます。"),
        Line("半分あまりの人が、金融やコンサルティング、大手メーカー、ネット大手といった、大きな組織で働いた経験を持っていました。"),
        Line("ただし、分類は社名から機械的に判定したもので、当時の会社の規模までは確かめていません。"),
    ], d_employer, tail=1.6)

    # 7 一般の新規開業者との比較
    def d_compare(cv, st):
        th = cv.th
        cv.title("ほかの起業家と比べると", ramp(st.t, 0, 0.4))
        lo, hi = 20, 60
        x0, x1, y = M + 80, W - M - 80, 560

        def X(v):
            return x0 + (x1 - x0) * (v - lo) / (hi - lo)

        out = 1 - ramp(st.t, st.at(2), 0.4)
        a = ramp(st.t, st.at(1), 0.6) * out
        if st.t < st.at(2) + 0.4:
            cv.line([(x0, y), (x1, y)], th.grid, 4, a)
            for v in range(lo, hi + 1, 10):
                cv.text((X(v), y + 16), f"{v}歳", th.size_note + 2, color=th.sub, alpha=a, anchor="ma")
            b = ramp(st.t, st.at(1) + 0.8, 0.8) * out
            xi, xj = X(N["age_mean"]), X(N["jfc_mean"])
            ic.building(cv, xi, y - 110, 180, th.accent, a)
            cv.text((xi, y + 70), "上場した会社の創業者", th.size_note + 4, color=th.accent, alpha=a, anchor="ma")
            cv.text((xi, y + 110), f"平均 {pf(N['age_mean'])}歳", th.size_body, bold=True, color=th.accent, alpha=a, anchor="ma")
            ic.shop(cv, xj, y - 90, 160, th.compare, b)
            cv.text((xj, y + 70), "新規開業者（公庫の調査）", th.size_note + 4, color=th.compare, alpha=b, anchor="ma")
            cv.text((xj, y + 110), f"平均 {pf(N['jfc_mean'])}歳", th.size_body, bold=True, color=th.compare, alpha=b, anchor="ma")
            g = ramp(st.t, st.at(1) + 1.8, 0.6) * out
            cv.line([(xi + 30, y - 250), (xj - 30, y - 250)], th.text, 4, g)
            cv.text(((xi + xj) / 2, y - 270), f"約{jfc_gap}歳", th.size_title, bold=True, alpha=g, anchor="md")
        if st.t >= st.at(2) + 0.3:
            b = ramp(st.t, st.at(2) + 0.3, 0.6)
            cv.text((W // 2, 200), "20代で起業した人の割合", th.size_body, bold=True, alpha=b, anchor="ma")
            for k, (lab, v, col, ico) in enumerate([("上場した会社の創業者", N["le29_pct"], th.accent, "building"),
                                                     ("新規開業者（公庫の調査）", N["jfc_le29"], th.compare, "shop")]):
                xg = M + 60 + k * 860
                ic.icon(cv, ico, xg, 330, 80, col, b)
                cv.text((xg + 60, 330), lab, th.size_note + 6, color=col, alpha=b, anchor="lm")
                ic.people_grid(cv, (xg - 40, 400, xg + 700, 780), 100, round(v), 20,
                               ramp(st.t, st.at(2) + 0.6 + 0.4 * k, 1.0), on=col, alpha=b)
                cv.text((xg + 330, 790), f"{pf(v)}%", th.size_body + 8, bold=True, color=col, alpha=b, anchor="ma")
        cv.note("出典：日本政策金融公庫「2025年度新規開業実態調査」。平均どうしの比較。公庫は開業時の年齢、創業者は創業年−生年。1人の形＝1%",
                ramp(st.t, st.at(1), 0.6))

    compare = Scene("公庫との比較", [
        Line("では、ほかの起業家と比べると、どうでしょうか。"),
        Line(f"日本政策金融公庫が調べた、新しく開業した人たちと比べると、上場した会社の創業者は、平均で、およそ{jfc_gap}歳若く起業していました。"),
        Line("20代で起業した人の割合も、上場した会社の創業者のほうが、ずっと多くなっています。"),
    ], d_compare, tail=1.8)

    # 8 比較の注意
    def d_caveat(cv, st):
        th = cv.th
        cv.title("比べている相手は違う", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0), 0.6)
        ic.shop(cv, 560, 500, 220, th.compare, a)
        for k in range(3):
            ic.person(cv, 480 + k * 80, 700, 70, th.compare, a)
        cv.text((560, 780), f"開業時の従業者 平均{pf(N['jfc_emp'])}人", th.size_note + 4, color=th.compare, alpha=a, anchor="ma")
        b = ramp(st.t, st.at(0) + 0.8, 0.6)
        ic.building(cv, 1360, 480, 420, th.accent, b)
        cv.text((1360, 740), "上場を目指す会社", th.size_note + 4, color=th.accent, alpha=b, anchor="ma")
        c = ramp(st.t, st.at(1), 0.6)
        cv.text((W // 2 - 10, 500), "≠", th.size_number + 40, bold=True, alpha=c, anchor="mm")
        cv.note("公庫の調査：公庫が2024年4〜9月に融資した、開業1年以内の企業（回答2,165社）。成功・失敗の比較ではない", a)

    caveat = Scene("比較の注意", [
        Line("ただし、公庫の調査の対象は、公庫から融資を受けた、開業して間もない企業で、従業員が数人ほどの小さな事業が中心です。"),
        Line("上場を目指す会社とは規模が大きく違うので、この差を、成功した人とそうでない人の違いとして読むことはできません。"),
    ], d_caveat, tail=1.4)

    cases = build_cases(N, load_cases(DATA))

    # 結論：年齢の線の上に道のりを置く
    def d_conclusion(cv, st):
        th = cv.th
        cv.title("上場した会社の創業者に多かった道のり", ramp(st.t, 0, 0.4))
        lo, hi = 18, 50
        x0, x1, y = M + 60, W - M - 60, 600

        def X(v):
            return x0 + (x1 - x0) * (v - lo) / (hi - lo)

        a = ramp(st.t, st.at(0), 0.6)
        cv.line([(x0, y), (x1, y)], th.grid, 4, a)
        for v in range(20, hi + 1, 5):
            cv.text((X(v), y + 18), f"{v}歳", th.size_note, color=th.sub, alpha=a, anchor="ma")
        ic.person(cv, X(19.5), y - 110, 110, th.muted, a, cap=True)
        ic.shop(cv, X(N["jfc_mean"]), y - 110, 130, th.muted, a)
        cv.text((X(N["jfc_mean"]), y + 60), f"新規開業者の平均 {pf(N['jfc_mean'])}歳", th.size_note, color=th.sub, alpha=a,
                anchor="ma")
        b = ramp(st.t, st.at(1), 0.8)
        start = N["age_median"] - N["yb_median"]
        ic.briefcase(cv, X(start), y - 200, 90, th.accent, b)
        cv.rect((X(start), y - 12, X(start) + (X(N["age_median"]) - X(start)) * b, y + 12), th.accent, b)
        cv.text(((X(start) + X(N["age_median"])) / 2, y - 60), f"就職から創業 中央値{N['yb_median']:g}年", th.size_note + 6,
                bold=True, color=th.accent, alpha=b, anchor="ma")
        c = ramp(st.t, st.at(1) + 1.2, 0.6)
        ic.bulb(cv, X(N["age_median"]), y - 160, 130, th.accent, c)
        cv.text((X(N["age_median"]), y + 60), f"創業 中央値{N['age_median']:g}歳", th.size_body, bold=True, color=th.accent,
                alpha=c, anchor="ma")
        cv.note("創業時年齢と、就職から創業までの年数は、いずれも中央値。就職の年齢はその差から求めた目安。成功の条件ではない",
                ramp(st.t, st.at(1), 0.6))

    conclusion = Scene("結論", [
        Line("上場した会社の創業者の中心は、学生のうちに起業した人でも、長く勤めてから独立した人でもありませんでした。"),
        Line(f"創業時の年齢の中央値は{N['age_median']:g}歳、最初の就職から創業までの年数の中央値は{N['yb_median']:g}年。社会人として一定の経験を積んでから起業した人が、典型的な姿です。"),
        Line("ただし、これは成功の条件ではなく、上場まで届いた人たちの経歴に見られた傾向です。"),
    ], d_conclusion, tail=2.4)

    def d_credits(cv, st):
        th = cv.th
        a = ramp(st.t, 0, 0.6)
        cv.title("出典とクレジット", a)
        lines = [
            ("JPX「新規上場会社情報」（2016〜2021年は Internet Archive の保存版）", th.text),
            ("各社の上場申請のための有価証券報告書（Iの部）、有価証券報告書", th.text),
            ("日本政策金融公庫総合研究所「2025年度新規開業実態調査」", th.text),
            ("事例：週刊東洋経済、Forbes JAPAN、flier、ニュースイッチ、ライフハッカー・ジャパン", th.text),
            ("詳細と注意事項は概要欄", th.text),
            (f"音声：{voice_credit}", th.sub),
            (f"音楽：{music_credit}", th.sub),
            ("フォント：BIZ UDPゴシック（SIL Open Font License 1.1）", th.sub),
        ]
        x0 = (W - max(cv.text_width(s, 30) for s, _ in lines)) / 2
        for k, (s, col) in enumerate(lines):
            cv.text((x0, 220 + k * 76), s, 30, alpha=a, color=col)

    credits = Scene("出典", [], d_credits, lead=8.0, tail=0.0)

    return [intro, scope, age, student, years, employer, compare, caveat, *cases, conclusion, credits]
