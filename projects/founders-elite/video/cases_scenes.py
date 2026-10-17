"""事例の章「では、彼らはなぜ会社を辞めて起業したのか？」

人物の経歴と発言の出典は ../cases.md
年齢と年数は data/founders.csv から読み込み、統計と同じ定義（創業年−生年、初職の年から創業年まで）を使う
ナレーションでは、本人の発言は「〜と語っています」、制作側の整理は「並べてみます」「うかがえます」で区別する
画面は年表とアイコンの関係図で構成し、ラベルは短い語にとどめる
"""
import pandas as pd

from tools.infographic import icons as ic
from tools.infographic.canvas import gantt, mix, ramp
from tools.infographic.video import Line, Scene

# (氏名, 企業, founders.csv の founder_id)
PEOPLE = [
    ("寺田親弘", "Sansan", "2019-06-19_4443_1"),
    ("佐々木大輔", "freee", "2019-12-17_4478_1"),
    ("南壮一郎", "ビズリーチ", "2021-04-22_4194_1"),
]
W, M = 1920, 120
BLUE, GRAY = (0x2E, 0x6B, 0xD1), (0xC9, 0xCE, 0xD4)  # Theme の accent・muted と同じ値（年表の行の色）


def load_cases(data_dir):
    f = pd.read_csv(data_dir / "founders.csv", dtype=str).fillna("")
    out = {}
    for name, _, fid in PEOPLE:
        r = f[f.founder_id == fid]
        assert len(r) == 1 and r.iloc[0]["name"] == name and r.iloc[0].target_20y == "Y", fid
        r = r.iloc[0]
        out[name] = {"age": int(float(r.age_at_founding)), "yb": int(float(r.years_before))}
    return out


def arrow(cv, x0, x1, y, alpha, color=None):
    th = cv.th
    c = color or th.sub
    cv.line([(x0, y), (x1 - 18, y)], c, 5, alpha)
    if alpha > 0:
        cv.d.polygon([(x1, y), (x1 - 22, y - 14), (x1 - 22, y + 14)], fill=mix(c, th.bg, alpha))


def chain(cv, y, steps, alphas, x0=M + 90, x1=W - M - 90, size=120):
    """アイコンを矢印でつなぐ関係図。steps は (アイコン名, ラベル, 色) のリスト"""
    th = cv.th
    n = len(steps)
    gap = (x1 - x0) / (n - 1)
    for k, ((name, lab, col), a) in enumerate(zip(steps, alphas)):
        x = x0 + gap * k
        ic.icon(cv, name, x, y, size, col or th.text, a)
        cv.text((x, y + size * 0.62), lab, th.size_note + 4, bold=True, alpha=a, anchor="ma", color=col or th.text)
        if k:
            arrow(cv, x - gap + size * 0.62, x - size * 0.62, y, a)


def build_cases(N, C):
    ages = sorted({c["age"] for c in C.values()})
    ybs = sorted({c["yb"] for c in C.values()})

    # 章の扉
    def d_door(cv, st):
        th = cv.th
        a = ramp(st.t, st.at(0), 0.6)
        ic.briefcase(cv, 640, 400, 200, th.text, a)
        b = ramp(st.t, st.at(1), 0.6)
        arrow(cv, 790, 1090, 400, b)
        cv.text((940, 360), "？", th.size_number, bold=True, alpha=b, anchor="md")
        ic.bulb(cv, 1280, 400, 220, th.accent, b)
        cv.text((W // 2, 680), "では、彼らはなぜ会社を辞めて起業したのか？", th.size_title, bold=True, alpha=b, anchor="ma")

    door = Scene("事例：問い", [
        Line(f"上場した会社の創業者が、最初の就職から起業するまでの年数は、中央値で{N['yb_median']:g}年でした。"),
        Line("では、その経験は、起業にどうつながったのでしょうか。"),
    ], d_door, tail=1.4)

    # 3人の位置
    def d_select(cv, st):
        th = cv.th
        cv.title("紹介する3人", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(1), 0.6)
        for k, (name, co, _) in enumerate(PEOPLE):
            x = M + 60 + k * 580
            ic.person(cv, x, 250, 110, th.accent, a)
            cv.text((x + 70, 230), name, th.size_body, bold=True, alpha=a, anchor="lm")
            cv.text((x + 70, 280), co, th.size_note + 4, color=th.sub, alpha=a, anchor="lm")
        b = ramp(st.t, st.at(2), 0.8)
        for k, (vals, lo, hi, mine, unit, med, lab) in enumerate([
                (N["ages"], 18, 66, ages, "歳", N["age_median"], "創業時の年齢"),
                (N["ybs"], 0, 40, ybs, "年", N["yb_median"], "最初の就職から創業まで")]):
            bx0 = M + k * 860
            box = (bx0, 440, bx0 + 800, 790)
            X, _ = ic.dot_hist(cv, box, vals, lo, hi, 1.0, color_of=lambda v, m=mine: th.accent if v in m else th.muted,
                               alpha=b)
            cv.line([(box[0], box[3] + 6), (box[2], box[3] + 6)], th.grid, 2, b)
            for v in range(lo + (-lo) % 10, hi + 1, 10):
                cv.text((X(v), box[3] + 14), f"{v}{unit}", th.size_note - 2, color=th.sub, alpha=b, anchor="ma")
            cv.text((bx0, 380), lab, th.size_note + 6, bold=True, alpha=b)
            rng = f"{mine[0]}〜{mine[-1]}{unit}" if len(mine) > 1 else f"{mine[0]}{unit}"
            cv.text((bx0 + 800, 384), f"3人は{rng}（中央値{med:g}{unit}）", th.size_note + 2, color=th.accent, alpha=b,
                    anchor="ra")
        cv.note("1点＝1人。青い列に3人が入る。3人は起業の理由を本人が語っている人から選んだ事例で、無作為に選んだ例ではない",
                ramp(st.t, st.at(3), 0.6))

    select = Scene("事例：選び方", [
        Line("ここからは、3人の創業者を例に見ていきます。"),
        Line("Sansanの寺田親弘さん、freeeの佐々木大輔さん、ビズリーチの南壮一郎さんです。",
             say="サンサンの寺田親弘さん、フリーの佐々木大輔さん、ビズリーチの南壮一郎さんです。"),
        Line("3人とも、起業した年齢と、それまで働いた年数が、中央値に近い人たちです。"),
        Line("ただし、起業の理由を本人がくわしく語っている人から選んだので、無作為に選んだ例ではありません。"),
    ], d_select, tail=1.4)

    def person_scene(idx, title, rows, start, end, markers, mark_at, gantt_at, steps, step_at, lines, source):
        def d(cv, st):
            th = cv.th
            cv.title(title, ramp(st.t, 0, 0.4))
            ps = [ramp(st.t, st.at(i), 0.8) for i in gantt_at]
            ms = [(y, lab, ramp(st.t, st.at(i), 0.6)) for (y, lab), i in zip(markers, mark_at)]
            gantt(cv, (M, 170, W - M, 470), rows, start, end, ps, label_w=360, markers=ms)
            steps_c = [(n, lab, th.accent if col == "A" else th.text) for n, lab, col in steps]
            chain(cv, 700, steps_c, [ramp(st.t, st.at(i), 0.6) for i in step_at])
            cv.note(source, ramp(st.t, st.at(0), 0.6), y=880)
        return Scene(f"事例{idx}", lines, d, tail=1.6)

    terada = person_scene(
        1, "寺田親弘さん（Sansan）",
        [("三井物産", 1999.25, 2007.45, GRAY), ("Sansan", 2007.45, 2019.5, BLUE)],
        1999, 2021, [(2007.45, "2007 創業"), (2019.47, "2019 上場")], [5, 5], [2, 5],
        [("flag", "学生時代から起業志望", None), ("briefcase", "三井物産で修行", None), ("cards", "名刺の管理", "A"),
         ("bulb", "データベース化", "A"), ("chart_up", "Sansan", "A")],
        [1, 2, 4, 4, 5],
        [Line("一人目は、名刺管理のSansanを創業した、寺田親弘さんです。", say="一人目は、名刺管理のサンサンを創業した、寺田親弘さんです。"),
         Line("寺田さんは、父親が事業をしていたこともあり、学生のころから起業を考えていたと語っています。"),
         Line("新卒で入った三井物産は、そのための修行の場だったといいます。"),
         Line("シリコンバレーでの仕事などを経て、テーマに選んだのは、毎日のように受け取る名刺でした。"),
         Line("名刺の管理が煩わしく、データベースにできないかと、会社員のころから考えていたそうです。"),
         Line("2007年に仲間と会社を立ち上げ、12年後に上場しました。")],
        "出典：週刊東洋経済（2019年8月）、Forbes JAPAN（EY Japan提供記事、2022年）、上場申請書類の役員略歴")

    sasaki = person_scene(
        2, "佐々木大輔さん（freee）",
        [("博報堂", 2004.25, 2006.5, GRAY), ("投資ファンド", 2006.5, 2007.35, GRAY), ("ALBERT（CFO）", 2007.35, 2008.35, GRAY),
         ("グーグル", 2008.35, 2012.5, GRAY), ("freee", 2012.5, 2019.95, BLUE)],
        2004, 2021, [(2012.5, "2012 創業"), (2019.96, "2019 上場")], [4, 4], [1, 1, 2, 1, 4],
        [("browser", "グーグルで中小企業向け", None), ("sheet", "経理の入力作業", "A"), ("bulb", "会計ソフトを作り直す", "A"),
         ("chart_up", "freee", "A")],
        [1, 2, 3, 4],
        [Line("二人目は、クラウド会計ソフトのfreeeを創業した、佐々木大輔さんです。", say="二人目は、クラウド会計ソフトのフリーを創業した、佐々木大輔さんです。"),
         Line("広告会社やスタートアップなどを経て、グーグルで中小企業向けの仕事をする中で、日本の中小企業はテクノロジーの活用が遅れている、と危機感を持ったと語っています。"),
         Line("思い出したのは、以前スタートアップで財務を任されていたとき、経理の担当者が一日中、入力作業に追われていたことでした。"),
         Line("会計ソフトの業界にイノベーションが起きていないと分かり、自分で作り始めたそうです。"),
         Line("2012年に会社を設立し、7年後に上場しました。")],
        "出典：flier「freee誕生秘話」（佐々木氏インタビュー）、有価証券報告書の役員略歴")

    minami = person_scene(
        3, "南壮一郎さん（ビズリーチ）",
        [("モルガン・スタンレー", 1999.55, 2001.0, GRAY), ("投資会社など", 2001.0, 2004.7, GRAY),
         ("楽天の球団", 2004.7, 2007.6, GRAY), ("ビズリーチ", 2007.6, 2021.3, BLUE)],
        1999, 2022, [(2007.6, "2007 設立"), (2009.3, "2009 サービス開始"), (2021.3, "2021 上場")], [3, 4, 5], [1, 1, 1, 3],
        [("briefcase", "金融、楽天の球団", None), ("flag", "ネット事業をやると決める", None), ("magnifier", "転職活動の非効率", "A"),
         ("bulb", "企業と求職者を直接つなぐ", "A"), ("chart_up", "ビズリーチ", "A")],
        [1, 3, 3, 4, 5],
        [Line("三人目は、転職サイトのビズリーチを創業した、南壮一郎さんです。"),
         Line("金融の仕事の後、楽天のプロ野球球団の立ち上げに加わりました。"),
         Line("球団を辞めたことと起業は、直接関係がない、と南さんは話しています。"),
         Line("インターネットの事業をやってみようと考えたとき、結びついたのが、自分の転職活動で感じた非効率さでした。"),
         Line("楽天市場が店と消費者を直接つないだように、企業と求職者を直接つなぐ。南さんは、ビズリーチをそう説明しています。"),
         Line("2007年に会社を設立し、2021年に上場しました。")],
        "出典：ニュースイッチ（2015年9月）、ライフハッカー・ジャパン（2014年1月、本人寄稿）、上場申請書類の役員略歴と沿革。上場時の社名はビジョナル")

    # 3人を並べる：決意（旗）と問題の順番
    # 名前・アイコン3つ・順番のラベルを1つのグループとして中央に置く（アイコン列の左端 CX0）
    CX0 = W / 2 - 380

    def d_compare(cv, st):
        th = cv.th
        cv.title("3人を並べると", ramp(st.t, 0, 0.4))
        rows = [("寺田さん", ["flag", "cards", "bulb"]), ("南さん", ["flag", "magnifier", "bulb"]),
                ("佐々木さん", ["sheet", "bulb", "flag"])]
        a = ramp(st.t, st.at(0), 0.6)
        common = ramp(st.t, st.at(1), 0.8)
        order = ramp(st.t, st.at(2), 0.6)
        for r, (name, seq) in enumerate(rows):
            y = 300 + r * 190 + (40 if r == 2 else 0)
            cv.text((CX0 - 90, y), name, th.size_body, bold=True, alpha=a, anchor="rm")
            for k, name_i in enumerate(seq):
                x = CX0 + k * 380
                problem = name_i in ("cards", "magnifier", "sheet")
                ic.icon(cv, name_i, x, y, 110, mix(th.accent, th.text, common) if problem else th.text, a)
                if k:
                    arrow(cv, x - 380 + 80, x - 80, y, a)
        cv.line([(CX0 - 330, 605), (CX0 + 760 + 330, 605)], th.grid, 3, order)
        cv.text((CX0 + 760 + 110, 395), "決意が先", th.size_note + 6, bold=True, color=th.sub, alpha=order, anchor="lm")
        cv.text((CX0 + 760 + 110, 720), "問題が先", th.size_note + 6, bold=True, color=th.sub, alpha=order, anchor="lm")
        cv.note("本人の発言をもとに制作側が整理。旗＝起業すると決めたこと、青＝事業のもとになった問題、電球＝事業のアイデア", a)

    compare = Scene("事例：比較", [
        Line("3人の話を、こちらで並べてみます。"),
        Line("共通しているのは、自分が実際に困ったり、目の前で見たりした問題を、事業のテーマにしていることです。"),
        Line("一方で、順番は違います。寺田さんと南さんは、まず起業すると決め、その後でテーマに出会いました。"),
        Line("佐々木さんは、問題に気づいてから、それを解決するために作り始めています。"),
    ], d_compare, tail=1.6)

    # 考察
    def d_reflect(cv, st):
        th = cv.th
        cv.title("会社員の時間と起業", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0), 0.6)
        ic.briefcase(cv, 420, 400, 180, th.text, a)
        arrow(cv, 560, 760, 400, a)
        for k, name in enumerate(["cards", "sheet", "magnifier"]):
            ic.icon(cv, name, 860 + k * 160, 400, 120, th.accent, a)
        arrow(cv, 1300, 1480, 400, a)
        ic.bulb(cv, 1600, 400, 180, th.accent, a)
        cv.text((420, 520), "会社員の時間", th.size_note + 6, bold=True, alpha=a, anchor="ma")
        cv.text((1020, 520), "事業のもとになる問題", th.size_note + 6, bold=True, color=th.accent, alpha=a, anchor="ma")
        cv.text((1600, 520), "起業", th.size_note + 6, bold=True, color=th.accent, alpha=a, anchor="ma")
        for k, lab in enumerate(["成功の条件", "上場の理由", "有利な会社"]):
            x = 470 + k * 440
            al = ramp(st.t, st.at(1) + 0.4 * k, 0.6)
            ic.cross(cv, x - 60, 720, 70, th.sub, al)
            cv.text((x, 720), lab, th.size_body, alpha=al, anchor="lm")
        cv.note("考察は制作側によるもの。×は、3人の事例からは言えないこと", ramp(st.t, st.at(1), 0.6))

    reflect = Scene("事例：考察", [
        Line("3人の話からは、会社員として過ごした時間が、事業のもとになる問題と出会う場になっていたことが、うかがえます。"),
        Line("ただし、これは3人の例から見えることです。会社員の経験が上場の理由だとも、特定の会社で働くと有利だとも言えません。"),
    ], d_reflect, tail=1.6)

    return [door, select, terada, sasaki, minami, compare, reflect]
