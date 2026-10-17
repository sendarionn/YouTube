"""動画「上場した創業者は、何歳で起業したのか」の台本と画面

数値は data/summary.json・data/breakdowns.json・data/founders.csv・data/external_stats.json から読み込み、
画面とナレーションに同じ値を使う（手入力の数値を置かない）
"""
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
sys.path.insert(0, str(REPO))

from tools.infographic.canvas import hbars, ramp, vbars, waffle  # noqa: E402
from tools.infographic.video import Line, Scene  # noqa: E402

DATA = PROJECT / "data"


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
        "judged": S["listings_total"] - S["technical"],
        "target": S["target_20"],
        "companies_named": S["companies_target20_with_named_founder"],
        "founders_named": S["founders_named_target20"],
        "career_known": S["career_known"],
        "age_bins": S["age_bins"],
        # 動画では階級幅をそろえる（5歳刻み）
        "age5": bin_counts(age, [(None, 24, "24歳以下"), (25, 29, "25〜29歳"), (30, 34, "30〜34歳"), (35, 39, "35〜39歳"),
                                 (40, 44, "40〜44歳"), (45, 49, "45〜49歳"), (50, None, "50歳以上")]),
        "yb5": bin_counts(yb, [(0, 4, "0〜4年"), (5, 9, "5〜9年"), (10, 14, "10〜14年"), (15, 19, "15〜19年"),
                               (20, 24, "20〜24年"), (25, None, "25年以上")]),
        "age_median": age.median(),
        "age_mean": round(age.mean(), 1),
        "le29_n": int((age <= 29).sum()),
        "le29_pct": round(100 * (age <= 29).mean(), 1),
        "student_n": int((car.student_founder == "Y").sum()),
        "student_pct": S["student_founder_pct"],
        "yb_bins": S["years_before_bins"],
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
    assert len(car) == N["career_known"]
    assert sum(N["age_bins"].values()) == N["career_known"]
    assert sum(N["yb_bins"].values()) == N["yb_n"]
    assert sum(N["age5"].values()) == N["career_known"] and sum(N["yb5"].values()) == N["yb_n"]
    assert round(100 * N["student_n"] / N["career_known"], 1) == N["student_pct"]
    assert round(100 * N["large_n"] / N["career_known"], 1) == N["large_pct"]
    assert N["age_median"] == S["age_at_founding_median"] and N["age_mean"] == S["age_at_founding_mean"]
    return N


def bin_counts(x, bins):
    x = x.dropna()
    out = {}
    for lo, hi, lab in bins:
        m = pd.Series(True, index=x.index)
        if lo is not None:
            m &= x >= lo
        if hi is not None:
            m &= x <= hi
        out[lab] = int(m.sum())
    return out


def pf(x):
    """割合・平均は小数1桁で表示する（6.0% を 6% と出さない）"""
    return f"{x:.1f}"


# 職歴の分類のうち「大手組織」に数えたもの（methodology.md）
LARGE_CATS = [("finance", "金融"), ("jp_large_maker_infra", "国内大手メーカー・インフラ等"), ("consulting", "コンサルティング"),
              ("net_megaventure", "ネット大手"), ("foreign_tech", "外資系IT"), ("trading", "総合商社")]

SRC_P1 = "出典：各社の上場申請書類（Iの部）・有価証券報告書の役員略歴をもとに集計"
SRC_JFC = "出典：日本政策金融公庫「2025年度新規開業実態調査」"


def build(N):
    M = 120  # 左右の余白
    W = 1920

    # 導入
    def d_intro(cv, st):
        th = cv.th
        a = ramp(st.t, st.at(0), 0.6)
        cv.text((W // 2, 300), "学生のうちに起業して", 72, bold=True, alpha=a, anchor="ma")
        cv.text((W // 2, 410), "若くして成功？", 72, bold=True, alpha=ramp(st.t, st.at(0) + 0.8, 0.6), anchor="ma")
        b = ramp(st.t, st.at(2), 0.6)
        cv.line([(W // 2 - 360, 560), (W // 2 + 360, 560)], th.grid, 3, b)
        cv.text((W // 2, 620), "上場した創業者は", th.size_title, alpha=b, anchor="ma", color=th.accent)
        cv.text((W // 2, 700), "何歳で、どんな経歴を経て起業したのか", th.size_title, bold=True,
                alpha=ramp(st.t, st.at(3), 0.6), anchor="ma")

    intro = Scene("導入", [
        Line("学生のうちに会社を立ち上げ、若くして大成功する。"),
        Line("起業家の成功と聞いて、そんな姿を思い浮かべる人もいるかもしれません。"),
        Line("では、実際に株式の上場まで会社を育てた創業者は、"),
        Line("何歳で、どんな経歴を経て起業したのでしょうか。", say="なんさいで、どんな経歴を経て起業したのでしょうか。"),
    ], d_intro, lead=0.8, tail=1.0)

    # 調査対象
    def d_scope(cv, st):
        th = cv.th
        cv.title("調べた対象", ramp(st.t, 0, 0.4))
        rows = [
            (0, N["listings"], "社", "2016〜2025年に東証へ新規上場"),
            (1, N["judged"], "社", f"テクニカル上場（{N['technical']}社）を除く"),
            (3, N["target"], "社", "個人創業・独立・大学発、創業20年以内"),
            (5, N["companies_named"], "社", "創業者の氏名を特定"),
        ]
        x0, bar_x, bar_w = M, M + 300, 620
        y = 210
        for k, (li, v, unit, lab) in enumerate(rows):
            p = ramp(st.t, st.at(li), 0.8)
            cy = y + k * 130
            cv.text((x0 + 260, cy), f"{v:,}{unit}", 52, bold=True, alpha=min(1, p * 2), anchor="rm")
            cv.rect((bar_x, cy - 26, bar_x + bar_w * v / N["listings"] * p, cy + 26),
                    th.accent if k == 2 else th.muted, min(1, p * 2))
            cv.text((bar_x + bar_w + 40, cy), lab, 34, alpha=min(1, p * 2), anchor="lm")
            assert bar_x + bar_w + 40 + cv.text_width(lab, 34) <= W - M, lab
        p = ramp(st.t, st.at(5), 0.6)
        q = ramp(st.t, st.at(6), 0.6)
        cy = y + 4 * 130 + 10
        cv.text((x0 + 260, cy), f"{N['founders_named']:,}人", 52, bold=True, alpha=p, anchor="rm")
        cv.text((bar_x, cy), "創業者（共同創業者を含む）", 34, alpha=p, anchor="lm")
        cv.text((x0 + 260, cy + 90), f"{N['career_known']:,}人", 52, bold=True, alpha=q, anchor="rm", color=th.accent)
        cv.text((bar_x, cy + 90), "生年と職歴を確認（以降の集計の対象）", 34, alpha=q, anchor="lm")
        cv.note("上場企業の創業者に限った集計で、起業家全体を代表するものではありません。棒の長さは社数", ramp(st.t, st.at(4), 0.6))

    scope = Scene("調査対象", [
        Line("調べたのは、2016年から2025年までに、東京証券取引所に新規上場した会社です。"),
        Line(f"持株会社の設立などによる、テクニカル上場を除いた{N['judged']}社について、"),
        Line("上場申請書類に載っている会社の沿革と、役員の経歴を読みました。"),
        Line("そのうち、個人が創業した会社、社内事業から独立した会社、大学発の会社で、"),
        Line(f"創業から上場まで20年以内の{N['target']}社を対象にしています。"),
        Line(f"創業者の名前が分かったのは、{N['companies_named']}社の{N['founders_named']}人。"),
        Line(f"生まれた年と職歴まで確認できたのは、{N['career_known']}人でした。"),
    ], d_scope)

    # 創業時の年齢
    labels = list(N["age5"].keys())
    ages = list(N["age5"].values())

    def d_age(cv, st):
        th = cv.th
        cv.title("創業したときの年齢", ramp(st.t, 0, 0.4))
        p = ramp(st.t, st.at(0) + 0.3, 1.0)
        hl = None
        if st.t >= st.at(1):
            hl = [1, 2, 3]
        if st.t >= st.at(2):
            hl = [0, 1]
        vbars(cv, (M, 200, 1260, 860), labels, ages, p, highlight=hl, fmt="{}人", label_size=26, value_size=36)
        a = ramp(st.t, st.at(1), 0.6)
        cv.text((1340, 260), "中央値", th.size_body, color=th.sub, alpha=a)
        cv.text((1340, 310), f"{N['age_median']:g}歳", th.size_number, bold=True, alpha=a, color=th.accent)
        cv.text((1340, 470), f"平均 {pf(N['age_mean'])}歳", th.size_body + 4, bold=True, alpha=a)
        b = ramp(st.t, st.at(2), 0.6)
        cv.text((1340, 580), "29歳以下", th.size_body, color=th.sub, alpha=b)
        cv.text((1340, 630), f"{pf(N['le29_pct'])}%", th.size_number - 20, bold=True, alpha=b, color=th.accent)
        cv.note(f"n={N['career_known']}。創業時の年齢＝創業年−生年（現在の事業の起点となった前身の個人事業を含む）",
                ramp(st.t, st.at(3), 0.6))

    age = Scene("年齢", [
        Line("まず、創業したときの年齢です。"),
        Line(f"人数が多いのは20代後半から30代で、真ん中の人は{N['age_median']:g}歳、平均は{pf(N['age_mean'])}歳でした。"),
        Line(f"29歳以下で創業した人も、{pf(N['le29_pct'])}%います。"),
        Line("創業時の年齢は、創業した年から、生まれた年を引いて計算しています。"),
    ], d_age)

    # 学生起業
    def d_student(cv, st):
        th = cv.th
        cv.title("学生起業に近い人", ramp(st.t, 0, 0.4))
        waffle(cv, (M + 40, 200, M + 40 + 640, 840), round(N["student_pct"]), 100, 10,
               ramp(st.t, st.at(1), 1.2), alpha=ramp(st.t, st.at(0), 0.6))
        a = ramp(st.t, st.at(1) + 0.8, 0.6)
        cv.text((960, 300), f"{pf(N['student_pct'])}%", th.size_number + 40, bold=True, alpha=a, color=th.accent)
        cv.text((960, 480), f"{N['student_n']}人 / {N['career_known']}人", th.size_body + 4, bold=True, alpha=a)
        cv.text((960, 560), "勤務先の記載がなく、", th.size_body, alpha=a)
        cv.text((960, 615), "25歳以下で創業した人", th.size_body, alpha=a)
        b = ramp(st.t, st.at(2), 0.6)
        cv.text((960, 720), "在学中かどうかは確認していない", th.size_body, color=th.sub, alpha=b)
        cv.note("1マス＝1%。役員略歴に勤務先の記載がなく、創業時25歳以下の人。アルバイトなどは略歴に載らない",
                ramp(st.t, st.at(2), 0.6))

    student = Scene("学生起業", [
        Line("一方で、学生起業に近い人は、多くありません。"),
        Line(f"役員の経歴に勤務先がなく、25歳以下で創業した人は、{pf(N['student_pct'])}%でした。"),
        Line("これは経歴の記載から判定したもので、"),
        Line("在学中だったかどうかを、一人ずつ確かめた数字ではありません。"),
    ], d_student)

    # 初職から創業まで
    yl = list(N["yb5"].keys())
    yv = list(N["yb5"].values())

    def d_years(cv, st):
        th = cv.th
        cv.title("最初の就職から創業までの年数", ramp(st.t, 0, 0.4))
        p = ramp(st.t, st.at(0) + 0.3, 1.0)
        vbars(cv, (M, 200, 1260, 860), yl, yv, p, highlight=[1, 2] if st.t >= st.at(1) else None, fmt="{}人",
              label_size=26, value_size=36)
        a = ramp(st.t, st.at(1), 0.6)
        cv.text((1340, 260), "中央値", th.size_body, color=th.sub, alpha=a)
        cv.text((1340, 310), f"{N['yb_median']:g}年", th.size_number, bold=True, alpha=a, color=th.accent)
        b = ramp(st.t, st.at(2), 0.6)
        for k, s in enumerate(["同じ会社の勤続年数ではなく", "転職や、別の会社を", "立ち上げた期間を含む"]):
            cv.text((1340, 500 + k * 56), s, th.size_body - 4, alpha=b)
        cv.note(f"初職の年が分かった{N['yb_n']}人。初職＝創業前の最初の入社・入行・入所など。自営や研究職の助手は数えない",
                ramp(st.t, st.at(1), 0.6))

    years = Scene("職歴の年数", [
        Line("では、創業するまでに、何をしていたのでしょうか。"),
        Line(f"最初に就職してから創業するまでの年数は、真ん中の人で{N['yb_median']:g}年でした。"),
        Line("ただし、これは一つの会社に、勤め続けた年数ではありません。"),
        Line("転職や、別の会社を立ち上げた期間も含めた、最初の就職からの年数です。"),
    ], d_years)

    # 勤務先
    cat_vals = [N["cats"][k] for k, _ in LARGE_CATS]
    cat_labels = [lab for _, lab in LARGE_CATS]

    def d_employer(cv, st):
        th = cv.th
        cv.title("創業前の勤務先", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(2), 0.6)
        cv.text((M, 230), "右のいずれかで", th.size_body, color=th.sub, alpha=a)
        cv.text((M, 280), "働いた経験あり", th.size_body, color=th.sub, alpha=a)
        cv.text((M, 340), f"{pf(N['large_pct'])}%", th.size_number, bold=True, color=th.accent, alpha=a)
        cv.text((M, 490), f"{N['large_n']}人 / {N['career_known']}人", th.size_body, bold=True, alpha=a)
        ps = [ramp(st.t, st.at(1) + 0.25 * k, 0.7) for k in range(len(cat_vals))]
        hbars(cv, (680, 210, 1800, 840), cat_labels, cat_vals, ps, vmax=20, fmt="{:.1f}%", label_w=540, size=34)
        cv.note("一人が複数に該当。分類は社名の辞書による判定で、勤務当時の会社の規模は確認していない",
                ramp(st.t, st.at(3), 0.6))

    employer = Scene("勤務先", [
        Line("創業前の勤務先を見てみます。"),
        Line("金融、コンサルティング、国内の大手メーカーやインフラ、ネット大手などで、"),
        Line(f"働いた経験がある人は、{N['career_known']}人のうち{pf(N['large_pct'])}%でした。"),
        Line("勤務先の分類は、社名から機械的に判定したもので、"),
        Line("勤めていた当時の会社の規模までは、確かめていません。"),
    ], d_employer)

    # 公庫との比較
    def d_compare(cv, st):
        th = cv.th
        cv.title("一般の新規開業者との比較", ramp(st.t, 0, 0.4))
        first = st.t < st.at(4)
        if st.t < st.at(2):
            # 比較のグラフを出す前は、ここまでの要点と問いを表示する
            a0 = ramp(st.t, st.at(0), 0.6)
            cv.text((W // 2, 300), f"創業時の年齢 中央値{N['age_median']:g}歳", th.size_title, bold=True, alpha=a0, anchor="ma")
            cv.text((W // 2, 400), f"最初の就職から創業まで 中央値{N['yb_median']:g}年", th.size_title, bold=True,
                    alpha=a0, anchor="ma")
            cv.text((W // 2, 590), "一般の新規開業者と比べると？", th.size_title, alpha=ramp(st.t, st.at(1), 0.6),
                    color=th.accent, anchor="ma")
            return
        if first:
            p0 = ramp(st.t, st.at(2), 0.8)
            p1 = ramp(st.t, st.at(3), 0.8)
            cv.text((M, 230), "開業・創業時の平均年齢", th.size_body, bold=True, alpha=ramp(st.t, st.at(2), 0.5))
            hbars(cv, (M, 300, 1800, 640), ["公庫の調査（開業者）", "上場した会社の創業者"],
                  [N["jfc_mean"], N["age_mean"]], [p0, p1], vmax=50, fmt="{:.1f}歳", label_w=480,
                  colors=[th.compare, th.accent], alpha=ramp(st.t, st.at(2), 0.5))
            d = ramp(st.t, st.at(3) + 1.0, 0.6)
            cv.text((M + 480, 700), f"差は約{round(N['jfc_mean'] - N['age_mean'])}歳", th.size_body + 8, bold=True, alpha=d)
        else:
            p = ramp(st.t, st.at(4), 0.8)
            cv.text((M, 230), "29歳以下で開業・創業した人の割合", th.size_body, bold=True, alpha=p)
            hbars(cv, (M, 300, 1800, 640), ["公庫の調査（開業者）", "上場した会社の創業者"],
                  [N["jfc_le29"], N["le29_pct"]], [p, ramp(st.t, st.at(4) + 0.4, 0.8)], vmax=50, fmt="{:.1f}%",
                  label_w=480, colors=[th.compare, th.accent])
        cv.note(SRC_JFC + "。公庫の値は開業時の年齢（アンケート）、創業者は創業年−生年", ramp(st.t, st.at(2), 0.6))

    compare = Scene("公庫との比較", [
        Line("ここまでを見ると、社会人として経験を積んでから起業する、堅実な姿が浮かびます。"),
        Line("ところが、一般の新規開業者と比べると、別の特徴が見えてきます。"),
        Line(f"日本政策金融公庫の2025年度の調査では、開業した人の平均年齢は{pf(N['jfc_mean'])}歳。"),
        Line(f"今回の創業者の平均、{pf(N['age_mean'])}歳より、およそ{round(N['jfc_mean'] - N['age_mean'])}歳上です。"),
        Line(f"29歳以下の割合も、公庫の調査では{pf(N['jfc_le29'])}%ですが、今回の創業者では{pf(N['le29_pct'])}%でした。"),
    ], d_compare, tail=1.6)

    # 比較の注意
    def d_caveat(cv, st):
        th = cv.th
        cv.title("二つの調査は対象が違う", ramp(st.t, 0, 0.4))
        cards = [
            ("上場した会社の創業者", th.accent, ["東証に上場した会社のみ", "上場申請書類などの役員略歴", "創業年−生年で年齢を計算"], 0),
            ("公庫の調査の開業者", th.compare, ["公庫が融資した開業1年以内の企業", f"開業時の従業者は平均{N['jfc_emp']:g}人",
                                        "アンケート（2,165社が回答）"], 0),
        ]
        for k, (head, col, items, _) in enumerate(cards):
            a = ramp(st.t, st.at(0) + 0.5 * k, 0.6)
            x = M + k * 860
            cv.rect((x, 200, x + 800, 680), (255, 255, 255), a, radius=12)
            cv.rect((x, 200, x + 12, 680), col, a)
            cv.text((x + 50, 240), head, th.size_body + 4, bold=True, alpha=a)
            for j, s in enumerate(items):
                cv.text((x + 50, 350 + j * 110), "・" + s, th.size_body - 4, alpha=a)
        b = ramp(st.t, st.at(2), 0.6)
        cv.text((W // 2, 740), "成功した人とそうでない人の比較ではない", th.size_body, bold=True, alpha=b, anchor="ma")
        cv.note(SRC_JFC, ramp(st.t, st.at(0), 0.6), y=880)

    caveat = Scene("比較の注意", [
        Line("ただし、公庫の調査の対象は、公庫が融資した、開業から1年以内の企業です。"),
        Line(f"開業時の従業者は平均{N['jfc_emp']:g}人で、上場を目指す会社とは、規模が大きく違います。"),
        Line("そのため、この差を、成功した人と、そうでない人の違いとして読むことはできません。"),
    ], d_caveat)

    # 結論
    def d_conclusion(cv, st):
        th = cv.th
        cv.title("上場した会社の創業者に多かった経歴", ramp(st.t, 0, 0.4))
        items = [
            (f"{N['age_median']:g}歳", "創業時の年齢（中央値）", st.at(2)),
            (f"{N['yb_median']:g}年", "最初の就職から創業まで（中央値）", st.at(2) + 0.6),
            (f"{pf(N['large_pct'])}%", "金融・コンサル・大手などの勤務経験", st.at(2) + 1.2),
            (f"{pf(N['student_pct'])}%", "勤務先の記載がなく25歳以下で創業", st.at(1)),
        ]
        for k, (num, lab, t0) in enumerate(items):
            a = ramp(st.t, t0, 0.6)
            x = M + (k % 2) * 860
            y = 220 + (k // 2) * 260
            cv.text((x, y), num, th.size_number - 10, bold=True, alpha=a, color=th.accent if k < 3 else th.sub)
            cv.text((x, y + 140), lab, th.size_body, alpha=a)
        b = ramp(st.t, st.at(3), 0.6)
        cv.text((W // 2, 790), "成功の条件ではなく、上場まで到達した人たちに見られた傾向", th.size_body, bold=True,
                alpha=b, anchor="ma")

    conclusion = Scene("結論", [
        Line("今回調べた、上場した会社の創業者に多かったのは、"),
        Line("学生のうちに起業した人でも、長く勤めてから独立した人でもなく、"),
        Line(f"{N['yb_median']:g}年ほど社会人として働き、30代前半で創業した人でした。"),
        Line("ただし、これは、成功の条件を示すものではありません。"),
        Line("上場まで到達した人たちの経歴に、こうした傾向が見られた、ということです。"),
    ], d_conclusion, tail=2.0)

    # 出典
    def d_credits(cv, st):
        th = cv.th
        a = ramp(st.t, 0, 0.6)
        cv.title("出典と注意", a)
        lines = [
            "JPX「新規上場会社情報」（2016〜2025年。2016〜2021年は Internet Archive の保存版）",
            "各社の上場申請のための有価証券報告書（Iの部）、有価証券報告書（役員の状況・沿革）",
            "日本政策金融公庫総合研究所「2025年度新規開業実態調査」（2025年12月）",
            "集計方法、定義、調査の限界は概要欄に記載",
            "",
            "音声：Open JTalk、HTS Voice \"Mei\"（© Nagoya Institute of Technology, CC BY 3.0）",
            "フォント：BIZ UDPゴシック（SIL Open Font License 1.1）",
        ]
        for k, s in enumerate(lines):
            cv.text((M, 220 + k * 70), s, 32, alpha=a, color=th.text if k < 4 else th.sub)

    credits = Scene("出典", [], d_credits, lead=8.0, tail=0.0)

    return [intro, scope, age, student, years, employer, compare, caveat, conclusion, credits]
