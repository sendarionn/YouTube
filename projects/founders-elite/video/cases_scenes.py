"""事例の章「では、彼らはなぜ会社を辞めて起業したのか？」

人物の経歴と発言の出典は ../cases.md
年齢と年数は data/founders.csv から読み込み、統計と同じ定義（創業年−生年、初職の年から創業年まで）を使う
本人の発言は「〜と語っています」、制作側の整理は「整理すると」で区別する
"""
import pandas as pd

from tools.infographic.canvas import flow, gantt, ramp, table, vbars
from tools.infographic.video import Line, Scene

# (氏名, 企業, 上場時の社名, founders.csv の founder_id)
PEOPLE = [
    ("寺田親弘", "Sansan", "Sansan", "2019-06-19_4443_1"),
    ("佐々木大輔", "freee", "フリー", "2019-12-17_4478_1"),
    ("南壮一郎", "ビズリーチ", "ビジョナル", "2021-04-22_4194_1"),
]


def load_cases(data_dir):
    f = pd.read_csv(data_dir / "founders.csv", dtype=str).fillna("")
    out = {}
    for name, _, _, fid in PEOPLE:
        r = f[f.founder_id == fid]
        assert len(r) == 1 and r.iloc[0]["name"] == name and r.iloc[0].target_20y == "Y", fid
        r = r.iloc[0]
        out[name] = {"age": int(float(r.age_at_founding)), "yb": int(float(r.years_before)),
                     "origin": r.origin_ym, "listing": r.listing_year}
    return out


def build_cases(N, C):
    th_M = 120
    W = 1920
    ages = sorted({c["age"] for c in C.values()})
    ybs = sorted({c["yb"] for c in C.values()})
    age_txt = f"{ages[0]}〜{ages[-1]}歳" if len(ages) > 1 else f"{ages[0]}歳"
    yb_txt = f"{ybs[0]}〜{ybs[-1]}年" if len(ybs) > 1 else f"{ybs[0]}年"

    # 章の扉
    def d_door(cv, st):
        th = cv.th
        a = ramp(st.t, st.at(0), 0.6)
        cv.text((W // 2, 300), f"創業時の年齢 中央値{N['age_median']:g}歳", th.size_title, bold=True, alpha=a, anchor="ma")
        cv.text((W // 2, 400), f"最初の就職から創業まで 中央値{N['yb_median']:g}年", th.size_title, bold=True,
                alpha=a, anchor="ma")
        b = ramp(st.t, st.at(1), 0.6)
        cv.line([(W // 2 - 420, 520), (W // 2 + 420, 520)], th.grid, 3, b)
        cv.text((W // 2, 580), "では、彼らはなぜ", th.size_title, alpha=b, color=th.accent, anchor="ma")
        cv.text((W // 2, 660), "会社を辞めて起業したのか？", th.size_title, bold=True, alpha=b, color=th.accent, anchor="ma")

    door = Scene("事例：問い", [
        Line(f"上場した会社の創業者の多くは、最初の就職から{N['yb_median']:g}年ほど働いてから、起業していました。"),
        Line("では、その経験は、起業にどうつながったのでしょうか。"),
    ], d_door, tail=1.4)

    # 事例の選び方と、統計の中での位置
    a_labels, a_vals = list(N["age5"].keys()), list(N["age5"].values())
    y_labels, y_vals = list(N["yb5"].keys()), list(N["yb5"].values())

    def bin_index(labels, v):
        for k, lab in enumerate(labels):
            nums = [int(x) for x in "".join(ch if ch.isdigit() else " " for ch in lab).split()]
            lo = nums[0] if "以下" not in lab else -1
            hi = nums[1] if len(nums) > 1 else (nums[0] if "以下" in lab else 999)
            if lo <= v <= hi:
                return k
        raise ValueError(v)

    a_hl = sorted({bin_index(a_labels, c["age"]) for c in C.values()})
    y_hl = sorted({bin_index(y_labels, c["yb"]) for c in C.values()})

    def d_select(cv, st):
        th = cv.th
        cv.title("紹介する3人", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0), 0.6)
        for k, (name, co, _, _) in enumerate(PEOPLE):
            cv.text((th_M + k * 560, 200), f"{name}（{co}）", th.size_body, bold=True, alpha=a)
        b = ramp(st.t, st.at(2), 0.8)
        hl = st.t >= st.at(2)
        cv.text((th_M, 290), f"創業時の年齢（歳）　3人は{age_txt}", th.size_note + 4, bold=True, alpha=b)
        vbars(cv, (th_M, 340, 900, 820), [lab.replace("歳", "") for lab in a_labels], a_vals, b,
              highlight=a_hl if hl else None, fmt="{}人", label_size=22, value_size=26, alpha=b)
        cv.text((1000, 290), f"最初の就職から創業まで　3人は{yb_txt}", th.size_note + 4, bold=True, alpha=b)
        vbars(cv, (1000, 340, 1800, 820), y_labels, y_vals, b, highlight=y_hl if hl else None, fmt="{}人",
              label_size=22, value_size=26, alpha=b)
        cv.note(f"n={N['career_known']}（初職の年は{N['yb_n']}人）。青は3人が入る階級。3人は無作為に選んだ例ではない",
                ramp(st.t, st.at(3), 0.6))

    select = Scene("事例：選び方", [
        Line("ここからは、具体的な3人の創業者を見ていきます。"),
        Line("選んだのは、今回の調査対象に含まれていて、本人がインタビューなどで、起業の理由を語っている人です。"),
        Line(f"3人とも、創業時の年齢は{age_txt}、最初の就職から創業までは{yb_txt}で、統計の真ん中に近い人たちです。",
             say=f"3人とも、創業時の年齢は{age_txt.replace('〜', '歳から')}、最初の就職から創業までは{yb_txt.replace('〜', '年から')}で、統計の真ん中に近い人たちです。"),
        Line("ただし、有名な創業者ほど、経歴や動機がくわしく公開されています。3人は、無作為に選んだ例ではありません。"),
    ], d_select, tail=1.4)

    def person_scene(idx, title, rows, start, end, markers, steps, step_at, lines, source, gantt_at, mark_at):
        def d(cv, st):
            th = cv.th
            cv.title(title, ramp(st.t, 0, 0.4))
            ps = [ramp(st.t, st.at(gantt_at[k]), 0.8) for k in range(len(rows))]
            ms = [(y, lab, ramp(st.t, st.at(mark_at[k]), 0.6)) for k, (y, lab) in enumerate(markers)]
            gantt(cv, (th_M, 180, 1800, 520), rows, start, end, ps, label_w=380, markers=ms)
            flow(cv, (th_M, 600, 1800, 850), steps, [ramp(st.t, st.at(i), 0.6) for i in step_at])
            cv.note(source, ramp(st.t, st.at(0), 0.6), y=870)
        return Scene(f"事例{idx}", lines, d, tail=1.6)

    # 年表の色：前職は薄い灰色、創業した会社は強調色（Theme の accent・muted と同じ値）
    BLUE, GRAY = (0x2E, 0x6B, 0xD1), (0xC9, 0xCE, 0xD4)

    terada = person_scene(
        1, "① 寺田親弘さん（Sansan）",
        [("三井物産（商社）", 1999.25, 2007.45, GRAY), ("Sansan（創業）", 2007.45, 2019.5, BLUE)],
        1999, 2021, [(2007.45, "2007年 創業"), (2019.47, "2019年 上場")],
        [("会社員時代", "三井物産でシリコンバレーのベンチャー企業の日本向け事業を支援、社内ベンチャーの立ち上げ"),
         ("本人が語る問題", "毎日もらう名刺の管理が煩わしい。データベース化できないかとずっと考えていた"),
         ("起業", "もともと起業志向で、会社員は修行の場。2007年、仲間4人と名刺管理の会社を設立")],
        [1, 4, 6],
        [Line("一人目は、名刺管理サービスのSansanを創業した、寺田親弘さんです。"),
         Line("1999年に三井物産に入社し、シリコンバレーで、ベンチャー企業の日本向けの事業を支援する仕事や、社内ベンチャーの立ち上げを経験しました。"),
         Line("寺田さんは、父親が事業をしていたこともあり、もともと起業を志していたと語っています。"),
         Line("三井物産は、そのための修行の場として選んだそうです。"),
         Line("事業のテーマに選んだのは、名刺でした。"),
         Line("毎日たくさんもらう名刺の管理が煩わしく、データベースにできないかと、会社員のころから考えていたといいます。"),
         Line("2007年に、4人の仲間と会社を立ち上げ、2019年に上場しました。")],
        "出典：週刊東洋経済（2019年8月）、Forbes JAPAN（EY Japan提供記事、2022年）、上場申請書類の役員略歴",
        gantt_at=[1, 6], mark_at=[6, 6])

    sasaki = person_scene(
        2, "② 佐々木大輔さん（freee）",
        [("博報堂（広告）", 2004.25, 2006.5, GRAY), ("投資ファンド", 2006.5, 2007.35, GRAY),
         ("ALBERT（CFO）", 2007.35, 2008.35, GRAY), ("グーグル", 2008.35, 2012.5, GRAY),
         ("freee（創業）", 2012.5, 2019.95, BLUE)],
        2004, 2021, [(2012.5, "2012年 創業"), (2019.96, "2019年 上場")],
        [("会社員時代", "グーグルでアジアの中小企業向けマーケティング。その前はスタートアップのCFO"),
         ("本人が語る問題", "中小企業のテクノロジー活用の遅れ。経理担当が一日中入力作業をしていた"),
         ("起業", "会計ソフトの業界にイノベーションがなかった。まずやってみるべきだと考え、自分で作り始めた")],
        [1, 2, 5],
        [Line("二人目は、クラウド会計ソフトのfreeeを創業した、佐々木大輔さんです。", say="二人目は、クラウド会計ソフトのフリーを創業した、佐々木大輔さんです。"),
         Line("博報堂、投資ファンド、スタートアップを経て、グーグルで、アジアの中小企業向けのマーケティングを担当しました。"),
         Line("その仕事の中で、日本の中小企業はテクノロジーの活用が遅れている、という危機感を持ったと語っています。"),
         Line("思い出したのが、グーグルに入る前、スタートアップで財務の責任者をしていたときのことです。"),
         Line("経理担当の人が一日中入力作業をしていて、使っていた会計ソフトがその原因になっていたといいます。"),
         Line("会計ソフトの業界を調べると、何のイノベーションも起きていなかった。そこで、まず自分でやってみようと、プログラミングを始めたそうです。"),
         Line("2012年に会社を設立し、2019年に上場しました。")],
        "出典：flier「freee誕生秘話」（佐々木氏インタビュー）、有価証券報告書の役員略歴",
        gantt_at=[1, 1, 3, 1, 6], mark_at=[6, 6])

    minami = person_scene(
        3, "③ 南壮一郎さん（ビズリーチ）",
        [("モルガン・スタンレー証券", 1999.55, 2001.0, GRAY), ("投資会社など", 2001.0, 2004.7, GRAY),
         ("楽天野球団（創業メンバー）", 2004.7, 2007.6, GRAY), ("ビズリーチ（創業）", 2007.6, 2021.3, BLUE)],
        1999, 2021, [(2007.6, "2007年 創業"), (2009.3, "2009年 サービス開始"), (2021.3, "2021年 上場")],
        [("会社員時代", "金融を経て楽天の球団の立ち上げ。楽天にいたがインターネット事業はしていなかった"),
         ("本人が語る問題", "自分の転職活動で、日本の転職活動の非効率さを感じた"),
         ("起業", "インターネットの事業をやると決めて会社を設立。楽天のネット通販のように企業と求職者を直接つなぐ")],
        [1, 4, 5],
        [Line("三人目は、転職サイトのビズリーチを創業した、南壮一郎さんです。"),
         Line("モルガン・スタンレー証券などで金融の仕事をした後、楽天のプロ野球球団の立ち上げに加わりました。"),
         Line("球団を辞めたことと起業とは、直接は関係がない、と南さんは話しています。"),
         Line("楽天にいながら、インターネットの事業には関わっていなかったため、インターネットの事業をやってみようと考えたそうです。"),
         Line("ちょうどそのころ、自分の転職活動の経験から、日本の転職活動は非効率だと感じていました。"),
         Line("楽天がネット通販で起こした変化と、ビズリーチは似ている、と南さんは語っています。"),
         Line("2007年に会社を設立し、2009年に転職サイトを始め、2021年に持株会社のビジョナルとして上場しました。")],
        "出典：ニュースイッチ（2015年9月）、ライフハッカー・ジャパン（2014年1月、本人寄稿）、上場申請書類の役員略歴と沿革",
        gantt_at=[1, 1, 1, 3], mark_at=[3, 6, 6])

    # 共通点と相違点
    def d_compare(cv, st):
        th = cv.th
        cv.title("3人を並べると（制作側の整理）", ramp(st.t, 0, 0.4))
        rows = [
            ["寺田さん", "名刺の管理が煩わしい", "会社員としての日常業務", "起業が先（学生時代から志望）"],
            ["佐々木さん", "経理の入力作業、中小企業のIT活用の遅れ", "CFOとグーグルでの仕事", "問題が先（気づいてから作り始めた）"],
            ["南さん", "日本の転職活動の非効率さ", "自分の転職活動", "起業が先（ネット事業をやると決めた）"],
        ]
        al = [ramp(st.t, st.at(0), 0.6)] * 3
        table(cv, (th_M, 190, 1800, 640), ["", "事業のもとになった問題", "問題に出会った場", "順番"], rows,
              [260, 520, 420, 480], alphas=al, size=32)
        b = ramp(st.t, st.at(1), 0.6)
        cv.text((th_M, 690), "共通点：自分が実際に困った、または見た問題を、事業のテーマにした", th.size_body - 2, bold=True, alpha=b)
        c2 = ramp(st.t, st.at(2), 0.6)
        cv.text((th_M, 770), "相違点：起業を決めた時期と、テーマに出会った時期の順番", th.size_body - 2, bold=True, alpha=c2)
        cv.note("本人の発言をもとに制作側が整理したもの", ramp(st.t, st.at(0), 0.6))

    compare = Scene("事例：比較", [
        Line("3人の話を並べて、整理してみます。"),
        Line("共通しているのは、自分が実際に困ったり、目の前で見たりした問題を、事業のテーマにしていることです。"),
        Line("一方で、順番は違います。寺田さんと南さんは、起業すると決めてから、テーマを見つけました。"),
        Line("佐々木さんは、仕事の中で問題に気づいてから、それを解決するために作り始めています。"),
    ], d_compare, tail=1.6)

    # 考察
    def d_reflect(cv, st):
        th = cv.th
        cv.title("会社員の経験と起業の関係", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0), 0.6)
        cv.text((W // 2, 280), "3人の話から見えるのは", th.size_body, color=th.sub, alpha=a, anchor="ma")
        cv.text((W // 2, 350), "会社員の時間が、事業のもとになる問題と出会う場になっていた", th.size_title - 4, bold=True,
                alpha=a, anchor="ma", color=th.accent)
        b = ramp(st.t, st.at(1), 0.6)
        for k, s in enumerate(["3人の事例だけでは、成功の共通条件とは言えない",
                               "会社員の経験が、上場できた理由だとは言えない",
                               "特定の会社で働くと有利だ、とも言えない"]):
            cv.text((th_M + 260, 520 + k * 80), "・" + s, th.size_body, alpha=ramp(st.t, st.at(1) + 0.5 * k, 0.6))
        cv.note("考察は制作側によるもの。3人は統計の傾向を具体化する事例で、統計的な代表ではない", b)

    reflect = Scene("事例：考察", [
        Line("3人の話からは、会社員として過ごした時間が、事業のもとになる問題と出会う場になっていたことが、うかがえます。"),
        Line("ただし、これは、3人の事例から見えることです。"),
        Line("会社員の経験が、上場できた理由だとまでは言えませんし、特定の会社で働くと有利だ、ということでもありません。"),
    ], d_reflect, tail=1.6)

    return [door, select, terada, sasaki, minami, compare, reflect]
