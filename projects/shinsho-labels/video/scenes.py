"""動画「新書レーベルは何が違う？」の台本と画面（research-v1）

方針（AGENTS.md「ナレーションと映像の役割分担」、DESIGN.md、video/brief-video.md）
- ナレーションは要点・解釈・結論。読み上げる数値は代表値（7割、17点、21枠など）に限る
- 細かな数値・分母・定義・出典は画面のラベルと注記で示す
- 割合は動画全体で整数の % にそろえる。距離は小数2桁
- 書影は利用条件を確認できないため使わない。レーベルは名前だけの模式的な札（実在の表紙に似せない）で示す
- 数値はすべて research/data/ と video/map_layout.json から読む。ナレーションの数値は load_numbers の確認（assert）で
  データと照合し、食い違えば描画しない
"""
import csv
import json
import statistics as stats
import sys
from collections import defaultdict
from pathlib import Path

VIDEO = Path(__file__).resolve().parent
PROJECT = VIDEO.parent
REPO = PROJECT.parents[1]
sys.path.insert(0, str(REPO))

from tools.infographic import svgicons  # noqa: E402
from tools.infographic.canvas import hexrgb, mix, ramp  # noqa: E402
from tools.infographic.video import Line, Scene, Shot  # noqa: E402

DATA = PROJECT / "research" / "data"
W, H, M = 1920, 1080, 120

# 分野のまとまり（日本十進分類法の第1次区分を6つにまとめる。動画内で色の意味を変えない）
GROUPS = [("社会科学", ("3",), hexrgb("2E6BD1")), ("歴史・地理", ("2",), hexrgb("D9A13B")),
          ("自然科学・医学", ("4",), hexrgb("3A9E8F")), ("哲学・宗教", ("1",), hexrgb("8C6BB8")),
          ("芸術・言語・文学", ("7", "8", "9"), hexrgb("D07A6A")), ("その他", ("0", "5", "6"), hexrgb("B8BEC6"))]
NDC_NAMES = {"0": "総記", "1": "哲学・宗教", "2": "歴史・地理", "3": "社会科学", "4": "自然科学", "5": "技術・工学",
             "6": "産業", "7": "芸術・スポーツ", "8": "言語", "9": "文学"}
# レーベルの区分の色（地図・札）。区分は色だけでなく凡例と位置でも示す
CAT_COLOR = {"general": hexrgb("2E6BD1"), "science": hexrgb("3A9E8F"), "specialized": hexrgb("B5533C"),
             "practical": hexrgb("7A8F3A"), "other": hexrgb("8E98A3")}
CAT_NAME = {"general": "一般向け", "science": "科学", "specialized": "分野特化", "practical": "実用",
            "other": "ビジネス・ジュニア・その他"}
NEAR, FAR = hexrgb("2E6BD1"), hexrgb("5B6470")


# 読み上げ用の読み（GPT-SoVITS がレーベル名を読み誤りやすいため、合成する文だけひらがなにする。字幕は元の表記）
# 書き起こし（asr_lines.py）で、漢字のままより読みの差が小さくなることを確かめた（production_log.md）
YOMI = [("中公新書ラクレ", "ちゅうこうしんしょ、らくれ"), ("講談社現代新書", "こうだんしゃげんだいしんしょ"),
        ("岩波ジュニア新書", "いわなみじゅにあしんしょ"), ("ちくまプリマー新書", "ちくまぷりまーしんしょ"),
        ("交通新聞社新書", "こうつうしんぶんしゃしんしょ"), ("PHPビジネス新書", "ぴーえいちぴーびじねすしんしょ"),
        ("日本十進分類法", "にほんじっしんぶんるいほう"), ("岩波新書", "いわなみしんしょ"), ("中公新書", "ちゅうこうしんしょ"),
        ("新潮新書", "しんちょうしんしょ"), ("ちくま新書", "ちくましんしょ"), ("ヨベル新書", "よべるしんしょ"),
        ("SB新書", "えすびーしんしょ"), ("PHP新書", "ぴーえいちぴーしんしょ"), ("ブルーバックス", "ぶるーばっくす"),
        ("講談社", "こうだんしゃ"), ("ラクレ", "らくれ"), ("中公", "ちゅうこう"), ("岩波", "いわなみ")]


def yomi(text):
    for a, b in YOMI:
        text = text.replace(a, b)
    return text


def cat_key(c):
    return c if c in ("general", "science", "specialized", "practical") else "other"


def read(name, delim=","):
    return list(csv.DictReader((DATA / name).open(encoding="utf-8"), delimiter=delim))


def load_numbers():
    cands = [c for c in read("label_candidates.csv") if c["decision"] != "除外"]
    titles = read("titles.csv")
    S = {r["label"]: r for r in read("summary_labels.csv")}
    stats_rows = {(r["scope"], r["level"]): r for r in read("ndc_stats.csv")}
    spec = defaultdict(dict)
    for r in read("ndc_specialization.csv"):
        spec[r["label"]][r["class"]] = r
    spec2 = defaultdict(dict)
    for r in read("ndc2_specialization.csv"):
        spec2[r["label"]][r["division"]] = r
    by_label = defaultdict(dict)
    for r in read("ndc_by_label.csv"):
        by_label[r["label"]][r["ndc_class"]] = int(r["titles"])
    authors = {r["label"]: r for r in read("author_shares.csv")}
    best = {r["label"]: int(r["appearances_top10_2016_2025"]) for r in read("bestseller_counts.csv")}
    dist = read("ndc_distance.csv")
    vdec = read("ndc_v_by_decade.csv")
    images = read("image_summary.csv")
    layout = json.loads((VIDEO / "map_layout.json").read_text(encoding="utf-8"))
    N = {"S": S}

    # 規模
    N["n_labels"] = len(cands)
    N["n_titles"] = len(titles)
    N["n_records"] = sum(int(r["count"]) for r in read("normalize_report.csv") if r["rule"] == "書誌レコード")
    N["cross_titles"] = sum(int(r["titles"]) for r in S.values())
    N["cross_labels"] = len(S)
    assert N["n_labels"] == 137 and N["cross_labels"] == 76
    assert round(N["n_titles"] / 1000) == 57 and round(N["cross_titles"] / 1000) == 14  # 「およそ5万7千点」「約1万4千点」

    # 分野の割合（6つのまとまり）
    def groups(label):
        c = by_label[label]
        n = sum(c.values())
        return [sum(c.get(k, 0) for k in ks) / n for _, ks, _ in GROUPS]
    N["groups"] = groups

    # 地図
    N["map"] = [(l, x, y, cat_key(S[l]["category"]), float(S[l]["titles_per_year"]))
                for l, (x, y) in zip(layout["labels"], layout["xy"])]
    N["map_distortion"] = layout["distortion"]

    # 違いの分解（相互情報量）
    mi_all = float(stats_rows[("all", "class")]["mutual_info_bits"])
    mi_between = float(stats_rows[("between_categories", "class")]["mutual_info_bits"])
    w_general = int(stats_rows[("category:general", "class")]["titles"])  # 分類の分かる点数（分母を相互情報量とそろえる）
    mi_general = float(stats_rows[("category:general", "class")]["mutual_info_bits"])
    total = int(stats_rows[("all", "class")]["titles"])
    N["decomp"] = [mi_between / mi_all, (w_general / total) * mi_general / mi_all]
    N["decomp"].append(1 - sum(N["decomp"]))
    N["general_share"] = sum(int(r["titles"]) for r in S.values() if r["category"] == "general") / N["cross_titles"]
    assert round(N["decomp"][0], 1) == 0.4 and round(N["general_share"], 1) == 0.8  # 「約4割」「約8割」

    # 一般向けの主なシリーズ（2016〜2025年の点数の多い順10）
    gen = sorted([r for r in S.values() if r["category"] == "general"], key=lambda r: -int(r["titles"]))[:10]
    N["general_top"] = [r["label"] for r in gen]
    assert all(max(range(6), key=lambda k: groups(l)[k]) == 0 for l in N["general_top"] if l != "中公新書")
    pair = next(d for d in dist if {d["label_a"], d["label_b"]} == {"講談社現代新書", "ちくま新書"})
    N["gendai_chikuma"] = float(pair["jsd"])
    assert N["gendai_chikuma"] == min(float(d["jsd"]) for d in dist)

    # 時代の変化（一般向け）
    N["v_decade"] = [(int(r["decade"]), float(r["cramers_v"]), int(r["labels"])) for r in vdec
                     if r["scope"] == "category:general" and int(r["decade"]) >= 1950]
    v = dict((d, x) for d, x, _ in N["v_decade"])
    assert max(v, key=v.get) == 1970 and v[2000] < v[1970] / 2  # 「1970年代は今よりずっと大きい」

    # 分野特化（綱で確かめる）
    def share2(label, divs):
        rows = spec2[label]
        n = sum(int(r["titles"]) for r in rows.values())
        return sum(int(rows[d]["titles"]) for d in divs if d in rows) / n, n
    bb_nat, n_bb = share2("ブルーバックス", [str(d) for d in range(40, 49)])
    bb_med, _ = share2("ブルーバックス", ["49"])
    N["special"] = [
        ("交通新聞社新書", "運輸（鉄道など）", [share2("交通新聞社新書", ["68"])[0]], "train"),
        ("ヨベル新書", "キリスト教", [share2("ヨベル新書", ["19"])[0]], "building-church"),
        ("ブルーバックス", "自然科学（医学を除く） {} ＋ 医学 {}", [bb_nat, bb_med], "atom"),
        ("健康人新書", "医学", [share2("健康人新書", ["49"])[0]], "heart-rate-monitor"),
        ("歴史新書y", "歴史・地理", [float(spec["歴史新書y"]["2"]["share"])], "hourglass"),
        ("ヤマケイ新書", "スポーツ・体育（登山など）", [share2("ヤマケイ新書", ["78"])[0]], "mountain"),
    ]
    assert round(N["special"][0][2][0], 1) == 0.7 and N["special"][1][2][0] > 0.8 and round(bb_nat, 1) == 0.6

    # 歴史：割合と点数
    hist = [(l, float(spec[l]["2"]["share"]), float(spec[l]["2"]["titles_per_year"]), cat_key(S[l]["category"]))
            for l in S if int(S[l]["titles"]) >= 20]
    N["hist"] = hist
    top_n = max(hist, key=lambda h: h[2])
    big_general = [h for h in hist if S[h[0]]["category"] == "general" and int(S[h[0]]["titles"]) >= 100]
    assert top_n[0] == "中公新書" and round(top_n[2]) == 17  # 「年に17点ほど」
    assert max(big_general, key=lambda h: h[1])[0] == "中公新書"
    assert max(hist, key=lambda h: h[1])[0] != "中公新書"

    # 著者
    au_labels = ["中公新書", "岩波新書", "ちくま新書", "講談社現代新書", "文春新書", "新潮新書", "SB新書"]
    N["authors"] = [(l, float(authors[l]["研究者・大学教員_share_matched"]), float(authors[l]["researcher_lower"]),
                     float(authors[l]["researcher_upper"]), float(authors[l]["matched_share"])) for l in au_labels]
    N["author_match_all"] = 0.474  # authors.py の出力（著者 7,192人中 3,407人）。下で authors.csv と照合
    au = read("authors.csv")
    assert round(sum(a["status"] == "照合" for a in au) / len(au), 3) == N["author_match_all"]
    r = {l: s for l, s, *_ in N["authors"]}
    assert all(0.7 <= r[l] < 0.85 for l in ("中公新書", "岩波新書", "ちくま新書"))  # 「7割から8割」
    assert all(0.25 <= r[l] < 0.35 for l in ("新潮新書", "SB新書"))  # 「3割ほど」

    # ベストセラー
    N["best"] = best
    assert best.get("新潮新書") == 21 and best.get("中公新書") == 10 and best.get("岩波新書", 0) == 0
    assert sum(best.values()) == 100

    # 同じ出版社のシリーズ
    pairs = [("ちくま新書", "ちくまプリマー新書"), ("岩波新書", "岩波ジュニア新書"), ("講談社現代新書", "講談社+α新書"),
             ("中公新書", "中公新書ラクレ"), ("PHP新書", "PHPビジネス新書"), ("SB新書", "サイエンス・アイ新書"),
             ("講談社現代新書", "ブルーバックス")]
    dd = {frozenset((d["label_a"], d["label_b"])): float(d["jsd"]) for d in dist}
    N["pairs"] = [(a, b, dd[frozenset((a, b))]) for a, b in pairs]
    N["dist_median"] = stats.median(float(d["jsd"]) for d in dist)
    assert N["pairs"][-1][2] == max(float(d["jsd"]) for d in dist if d["same_publisher"] == "1" and
                                    "健康人新書" not in (d["label_a"], d["label_b"]))
    nk = float(spec["中公新書ラクレ"]["2"]["share"])
    assert nk < float(spec["中公新書"]["2"]["share"]) / 2 and S["中公新書ラクレ"]["top_ndc"] == "3"

    # イメージの情報源の数
    img = defaultdict(dict)
    for r in images:
        img[r["label"]][r["category"]] = int(r["sources"])
    N["img"] = img
    N["n_image_sources"] = len({r["source_id"] for r in read("image_claims.tsv", "\t")})
    assert N["n_image_sources"] == 11
    return N


def pct(x):
    """整数の % に四捨五入する（Python の round は 0.5 を偶数側に丸めるため使わない。34.5% → 35%）"""
    return f"{int(x * 100 + 0.5)}%"


def short(label):
    return label.replace("新書", "") if len(label) > 7 else label


def token(cv, cx, cy, label, color, alpha, w=104, h=470, size=40):
    """レーベルの札（名前だけの模式図。実在の表紙・背表紙のデザインには似せない）"""
    if alpha <= 0:
        return
    th = cv.th
    cv.rect((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), (255, 255, 255), alpha, radius=10)
    cv.rect((cx - w / 2, cy - h / 2, cx + w / 2, cy - h / 2 + 18), color, alpha, radius=6)
    chars = list(label)
    step = min(size + 4, (h - 60) / max(len(chars), 1))
    s = int(min(size, step - 2))
    y0 = cy - step * len(chars) / 2 + 12
    for k, ch in enumerate(chars):
        cv.text((cx, y0 + k * step + step / 2), ch, s, bold=True, alpha=alpha, anchor="mm")


def tag(cv, xy, s, size, color, alpha=1.0, anchor="lm", leader=None, bold=True):
    """点に添えるラベル。背景色の下地を敷いて点や線と重なっても読めるようにする。leader は点の座標（引き出し線）"""
    if alpha <= 0:
        return
    th = cv.th
    x, y = xy
    w = cv.text_width(s, size, bold)
    left = x - w if anchor[0] == "r" else (x - w / 2 if anchor[0] == "m" else x)
    if leader:
        cv.line([leader, (left if leader[0] < left else left + w, y)], th.sub, 2, alpha)
    cv.rect((left - 8, y - size * 0.62, left + w + 8, y + size * 0.62), th.bg, 1.0 if alpha >= 1 else alpha, radius=6)
    cv.text((x, y), s, size, bold=bold, color=color, alpha=alpha, anchor=anchor)


def stacked(cv, x0, y, x1, h, shares, alpha=1.0, progress=1.0):
    acc = x0
    for (name, _, col), s in zip(GROUPS, shares):
        w = (x1 - x0) * s * progress
        cv.rect((acc, y, acc + w, y + h), col, alpha)
        acc += w


def legend(cv, items, y, alpha, size=None):
    """凡例を横一列に、全体を中央にそろえて並べる。items は (名前, 色)"""
    th = cv.th
    s = size or th.size_note
    widths = [28 + 10 + cv.text_width(n, s) for n, _ in items]
    gap = 36
    x = (W - sum(widths) - gap * (len(items) - 1)) / 2
    for (n, col), w in zip(items, widths):
        cv.rect((x, y - 12, x + 28, y + 12), col, alpha, radius=4)
        cv.text((x + 38, y), n, s, color=th.sub, alpha=alpha, anchor="lm")
        x += w + gap


def build(N, voice_credit, music_credit=""):
    th_accent = CAT_COLOR["general"]
    S = N["S"]

    # 1 導入
    intro_labels = [("岩波新書", "general"), ("中公新書", "general"), ("新潮新書", "general"),
                    ("講談社現代新書", "general"), ("ブルーバックス", "science")]
    xs = [W / 2 + (k - 2) * 230 for k in range(5)]

    def d_intro(cv, st):
        for k, ((l, c), x) in enumerate(zip(intro_labels, xs)):
            token(cv, x, 470, l, CAT_COLOR[c], ramp(st.t, st.at(1) + 0.35 * k, 0.6))
        a = ramp(st.t, st.at(0), 0.8)
        for k in range(9):
            cv.rect((W / 2 - 560 + k * 128, 760, W / 2 - 560 + k * 128 + 96, 770), cv.th.muted, a)

    intro = Scene("導入", [
        Line("書店の新書の売り場には、同じ大きさの本がずらりと並んでいます。"),
        Line("岩波新書、中公新書、新潮新書、講談社現代新書、ブルーバックス。"),
        Line("新書には出版社ごとのレーベルがあり、それぞれに違ったイメージが語られています。"),
    ], d_intro, lead=0.8, shots=[
        Shot("書店の新書の売り場（棚の全景）", "新書が同じ判型で並ぶ様子を見せる", line=0, seconds=4.0,
             angle="棚の正面から引き、背表紙の色の帯が分かる構図", notes="書店の撮影許可を得る。客の顔を写さない",
             placeholder="棚の模式図（灰色の帯）"),
        Shot("主なレーベルの背表紙を並べたもの", "取り上げるレーベルを実物で示す", line=1, seconds=4.0,
             angle="真上または正面、5冊を等間隔", notes="自分で購入・所有した本を使う。書影の公開の可否は別に確認",
             placeholder="レーベル名の札"),
    ])

    # 2 イメージ
    tags = [("岩波新書", "学術的", "学術的・専門的"), ("中公新書", "歴史に強い", "歴史に強い"),
            ("新潮新書", "大衆向け", "大衆向け・時事的"), ("講談社現代新書", "分野が幅広い", "分野が幅広い")]

    def d_image(cv, st):
        th = cv.th
        for k, ((l, c), x) in enumerate(zip(intro_labels, xs)):
            token(cv, x, 400, l, CAT_COLOR[c], 1.0, h=400, size=34)
        for k, (l, tag, key) in enumerate(tags):
            a = ramp(st.t, st.at(0) + 0.9 * k, 0.6)
            x = xs[[i for i, (n, _) in enumerate(intro_labels) if n == l][0]]
            n = N["img"][l].get(key, 0)
            cv.rect((x - 100, 640, x + 100, 700), (255, 255, 255), a, radius=30)
            cv.text((x, 670), f"「{tag}」", th.size_note + 2, bold=True, color=th.accent, alpha=a, anchor="mm")
            cv.text((x, 730), f"{n}件の情報源", th.size_note - 2, color=th.sub, alpha=a, anchor="ma")
        q = ramp(st.t, st.at(2), 0.6)
        svgicons.draw(cv, "help-circle", W / 2, 830, 72, th.text, q)
        cv.note(f"ネット上の個人の記述（Q&A・ブログ・note など{N['n_image_sources']}の情報源、2014〜2025年）。世間全体の意見ではない",
                ramp(st.t, st.at(1), 0.6))

    image = Scene("語られるイメージ", [
        Line("たとえば、中公新書は歴史に強い、岩波新書は学術的、新潮新書は大衆向け、といったものです。"),
        Line("ブログや質問サイトでは、こうした印象がよく語られます。"),
        Line("では、こうしたイメージは、実際の出版の記録にも表れているのでしょうか。"),
        Line("そもそも、レーベルの違いは、どこに表れるのでしょうか。"),
    ], d_image)

    # 3 データ
    def d_data(cv, st):
        th = cv.th
        cv.title("集めたデータ", ramp(st.t, 0, 0.4))
        cols = [(W / 2 - 580, "database", f"{N['n_labels']}", "シリーズ", "国立国会図書館の書誌", st.at(0)),
                (W / 2, "books", f"{N['n_titles']:,}", "点", "1タイトル＝1点（重版をまとめる）", st.at(1)),
                (W / 2 + 580, "chart-bar", f"{N['cross_titles']:,}", "点", f"2016〜2025年・{N['cross_labels']}シリーズ",
                 st.at(2))]
        for x, icon, num, unit, sub, t0 in cols:
            a = ramp(st.t, t0, 0.6)
            svgicons.draw(cv, icon, x, 300, 110, th.text, a)
            ns = th.size_number - 24
            nw = cv.text_width(num, ns, True)
            uw = cv.text_width(unit, th.size_body, True)
            left = x - (nw + 8 + uw) / 2
            cv.text((left, 520), num, ns, bold=True, alpha=a, anchor="ls")
            cv.text((left + nw + 8, 520), unit, th.size_body, bold=True, alpha=a, anchor="ls")
            cv.text((x, 560), sub, th.size_note, color=th.sub, alpha=a, anchor="ma")
        b = ramp(st.t, st.at(3), 0.6)
        items = [("category", "分野"), ("user", "著者"), ("trophy", "売れ方"), ("hourglass", "時代の変化")]
        for k, (icon, lab) in enumerate(items):
            x = W / 2 + (k - 1.5) * 260
            svgicons.draw(cv, icon, x, 700, 64, th.accent, ramp(st.t, st.at(3) + 0.25 * k, 0.5))
            cv.text((x, 750), lab, th.size_note + 4, alpha=ramp(st.t, st.at(3) + 0.25 * k, 0.5), anchor="ma")
        cv.note(f"国立国会図書館サーチ（API）の書誌 {N['n_records']:,}件から。対象は主要な新書シリーズで、日本の新書のすべてではない",
                ramp(st.t, st.at(1), 0.6))

    data = Scene("データ", [
        Line("国立国会図書館の書誌データから、主な新書137シリーズ、およそ5万7千点を集めました。"),
        Line("重版などはまとめて、1つのタイトルを1点と数えています。"),
        Line("比べる中心は、2016年から2025年の10年間に出た、76シリーズ、約1万4千点です。"),
        Line("分野、著者、本の売れ方、そして時代による変化を見ていきます。"),
    ], d_data, tail=1.4)

    # 4 分野の測り方
    def d_ndc(cv, st):
        th = cv.th
        cv.title("分野の測り方", ramp(st.t, 0, 0.4))
        g = ramp(st.t, st.at(3) - 0.2, 0.8)
        for k in range(10):
            a = ramp(st.t, st.at(1) + 0.12 * k, 0.5)
            col = next(c for _, ks, c in GROUPS if str(k) in ks)
            x = W / 2 + (k - 4.5) * 168
            fill = mix(col, (255, 255, 255), g)
            cv.rect((x - 76, 230, x + 76, 380), fill, a, radius=12)
            tc = mix((255, 255, 255), th.text, g)
            cv.text((x, 270), str(k), th.size_body, bold=True, color=tc, alpha=a, anchor="mm")
            cv.text((x, 330), NDC_NAMES[str(k)].split("・")[0], th.size_note - 2, color=tc, alpha=a, anchor="mm")
        b = ramp(st.t, st.at(3), 0.6)
        x0, x1 = M + 220, W - M - 220
        cv.text((x0 - 20, 560), "岩波新書", th.size_body, bold=True, alpha=b, anchor="rm")
        stacked(cv, x0, 520, x1, 80, N["groups"]("岩波新書"), b, ramp(st.t, st.at(3) + 0.3, 1.2))
        legend(cv, [(n, c) for n, _, c in GROUPS], 680, b)
        cv.note("日本十進分類法（NDC）の第1次区分。国立国会図書館が1冊ごとに付けた分類。6つの色にまとめて示す",
                ramp(st.t, st.at(2), 0.6))

    ndc = Scene("分野の測り方", [
        Line("まず、分野です。"),
        Line("図書館の本には、日本十進分類法という分類の番号がついています。"),
        Line("社会科学、歴史、自然科学など、10の大きな区分です。"),
        Line("レーベルごとに、どの区分の本をどれだけ出しているかを、割合で比べました。"),
    ], d_ndc, tail=1.4)

    # 5 レーベルの地図
    pts = N["map"]
    mxs = [p[1] for p in pts]
    mys = [p[2] for p in pts]
    box = (M + 140, 170, W - M - 140, 830)

    def MX(x):
        return box[0] + (x - min(mxs)) / (max(mxs) - min(mxs)) * (box[2] - box[0])

    def MY(y):
        return box[1] + (y - min(mys)) / (max(mys) - min(mys)) * (box[3] - box[1])

    # 名前を出すシリーズ：(配置, 引き出し線の先のずれ)。塊の中のシリーズは塊の外へ引き出す
    named = {"交通新聞社新書": ("rm", None), "ヨベル新書": ("rm", None), "ブルーバックス": ("rm", (-70, -110)),
             "健康人新書": ("rm", None), "歴史新書y": ("rm", None), "ヤマケイ新書": ("rm", None),
             "ニュートン超図解新書": ("mm", (0, 56)), "日経文庫": ("rm", None), "新典社新書": ("lm", None),
             "中公新書": ("rm", (-240, -150)), "WAC BUNKO": ("rm", None)}

    def d_map(cv, st):
        th = cv.th
        cv.title("レーベルの地図", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0) + 0.6, 1.2)
        size = ramp(st.t, st.at(1), 0.8)
        gen = ramp(st.t, st.at(2), 0.8)
        oth = ramp(st.t, st.at(3), 0.8)
        for l, x, y, c, tpy in sorted(pts, key=lambda p: -p[4]):
            r = 7 + 2.2 * tpy ** 0.5 * size
            col = th.muted
            if c == "general":
                col = mix(CAT_COLOR[c], th.muted, gen)
            else:
                col = mix(CAT_COLOR[c], th.muted, oth)
            cx, cy = MX(x), MY(y)
            cv.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=mix(col, th.bg, a * 0.85),
                         outline=mix((255, 255, 255), th.bg, a), width=2)
        for l, x, y, c, tpy in pts:
            if l not in named:
                continue
            al = gen if c == "general" else oth
            cx, cy = MX(x), MY(y)
            r = 7 + 2.2 * tpy ** 0.5
            anchor, off = named[l]
            if off:
                tag(cv, (cx + off[0], cy + off[1]), l, th.size_note + 2, CAT_COLOR[c], al, anchor, leader=(cx, cy))
            else:
                dx = -(r + 10) if anchor == "rm" else r + 10
                tag(cv, (cx + dx, cy), l, th.size_note + 2, CAT_COLOR[c], al, anchor)
        legend(cv, [(CAT_NAME[k], CAT_COLOR[k]) for k in CAT_COLOR], 862, ramp(st.t, st.at(2), 0.6))
        dsp = N["map_distortion"]
        cv.note(f"2016〜2025年に20点以上の{dsp['n_labels']}シリーズ。分野の割合の距離を2次元で近似（順位相関 {dsp['spearman']:.2f}）。"
                "点の大きさ＝年平均点数", ramp(st.t, st.at(4), 0.6), y=920)

    lmap = Scene("レーベルの地図", [
        Line("分野の割合が似ているレーベルほど近くに、違うほど遠くに置いて、一枚の地図にしました。"),
        Line("点の大きさは、1年あたりに出した本の数です。"),
        Line("真ん中には、一般向けのレーベルが集まって、大きな塊をつくっています。"),
        Line("その周りに、科学や健康、鉄道、宗教、歴史といった、分野を絞ったレーベルが離れて並びます。"),
        Line("二次元に置き直しているので、地図の上の距離はおおよその目安です。"),
    ], d_map, tail=2.0)

    # 6 違いの大きさ
    def d_size(cv, st):
        th = cv.th
        cv.title("分野の違いはどこから来るか", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(1), 0.6)
        x0, x1, y = M + 160, W - M - 160, 300
        parts = [("レーベルの種類の違い", N["decomp"][0], th.accent),
                 ("一般向けどうしの違い", N["decomp"][1], hexrgb("8E98A3")),
                 ("実用・専門などの中の違い", N["decomp"][2], th.muted)]
        cv.text((W / 2, 240), "レーベルによる分野の違い（全体＝100%）", th.size_note + 2, color=th.sub, alpha=a, anchor="ma")
        acc = x0
        p = ramp(st.t, st.at(1) + 0.3, 1.2)
        for k, (lab, s, col) in enumerate(parts):
            w = (x1 - x0) * s * p
            cv.rect((acc, y, acc + w, y + 90), col, a)
            if p > 0.9:
                cv.text((acc + w / 2, y + 45), pct(s), th.size_body, bold=True,
                        color=(255, 255, 255) if k < 2 else th.text, alpha=a, anchor="mm")
                cv.text((acc + w / 2, y + 120), lab, th.size_note, color=th.sub, alpha=a, anchor="ma")
            acc += w
        b = ramp(st.t, st.at(3), 0.6)
        gx = W / 2 - 340
        cv.text((W / 2, 520), "2016〜2025年の刊行点数（100マス）", th.size_note + 2, color=th.sub, alpha=b, anchor="ma")
        n_on = round(N["general_share"] * 100)
        cell = 34
        for k in range(100):
            r_, c_ = divmod(k, 20)
            col = th.accent if k < n_on * ramp(st.t, st.at(3) + 0.2, 1.2) else th.muted
            cv.rect((gx + c_ * cell, 570 + r_ * cell, gx + c_ * cell + cell - 6, 570 + r_ * cell + cell - 6), col, b, radius=4)
        cv.text((gx + 20 * cell + 30, 640), pct(N["general_share"]), th.size_number, bold=True, color=th.accent,
                alpha=ramp(st.t, st.at(3) + 1.2, 0.6), anchor="lm")
        cv.text((gx + 20 * cell + 34, 730), "一般向け", th.size_body, alpha=ramp(st.t, st.at(3) + 1.2, 0.6), anchor="lm")
        cv.note("上：相互情報量の分解（四捨五入のため合計は100%にならない）。下：刊行点数の割合で、書店の棚や在庫の割合ではない",
                ramp(st.t, st.at(1), 0.6))

    size_sc = Scene("違いの大きさ", [
        Line("全体で見ると、レーベルによって分野は確かに違います。"),
        Line("ただ、その違いの約4割は、一般向け、科学、専門といった、レーベルの種類の違いで説明できます。"),
        Line("科学のレーベルが科学の本を出すのは当然なので、それだけでは発見とは言えません。"),
        Line("また、この10年に出た本のうち、約8割は一般向けのレーベルのものです。"),
    ], d_size, tail=1.6)

    # 7 一般向けは似ているか
    top = N["general_top"]

    def d_general(cv, st):
        th = cv.th
        cv.title("一般向けのレーベルの分野", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(1) - 0.4, 0.6)
        x0, x1 = M + 330, W - M - 40
        hl = ramp(st.t, st.at(2), 0.6)
        legend(cv, [(n, c) for n, _, c in GROUPS], 180, a)
        for k, l in enumerate(top):
            y = 230 + k * 62
            p = ramp(st.t, st.at(1) - 0.2 + 0.12 * k, 0.9)
            focus = l in ("講談社現代新書", "ちくま新書")
            col = th.text if not hl or focus else mix(th.text, th.muted, 1 - 0.6 * hl)
            cv.text((x0 - 24, y + 23), l, th.size_note + 4, bold=focus, color=col, alpha=a, anchor="rm")
            stacked(cv, x0, y, x1, 46, N["groups"](l), a if not hl or focus else a * (1 - 0.55 * hl), p)
            if focus and hl > 0:
                cv.line([(x0 - 6, y - 6), (x1 + 6, y - 6), (x1 + 6, y + 52), (x0 - 6, y + 52), (x0 - 6, y - 6)],
                        th.text, 3, hl)
        cv.note(f"2016〜2025年の点数上位の一般向け10シリーズ。NDC 第1次区分。講談社現代とちくまの距離 {N['gendai_chikuma']:.2f}（最小）",
                ramp(st.t, st.at(2), 0.6))

    general = Scene("一般向けは似ているか", [
        Line("では、一般向けのレーベルどうしは、どれくらい違うのでしょうか。"),
        Line("主な一般向けのレーベルは、どれも社会科学がいちばん多く、分野の割合はよく似ています。"),
        Line("なかでも、講談社現代新書とちくま新書は、ほとんど同じ割合でした。"),
        Line("ただし、これは分類の比較です。本の中身や考え方まで同じという意味ではありません。"),
    ], d_general, tail=1.6, shots=[
        Shot("一般向けの主なレーベルの本を並べた比較", "似たレーベルでも本の見た目は違うことを示す", line=1, seconds=4.0,
             angle="平置きで俯瞰", notes="自分で所有する本を使う", placeholder="分野の積み上げ棒グラフ"),
    ])

    # 8 時代の変化
    vd = N["v_decade"]

    def d_time(cv, st):
        th = cv.th
        cv.title("一般向けのレーベルの違いの大きさ", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0), 0.6)
        x0, x1, y0, y1 = M + 260, W - M - 260, 230, 760
        vmax = 0.4

        def X(d):
            return x0 + (d - 1950) / 70 * (x1 - x0)

        def Y(v):
            return y1 - v / vmax * (y1 - y0)
        for v in (0, 0.1, 0.2, 0.3, 0.4):
            cv.line([(x0, Y(v)), (x1, Y(v))], th.grid, 2, a)
            cv.text((x0 - 20, Y(v)), f"{v:.1f}", th.size_note, color=th.sub, alpha=a, anchor="rm")
        for d, _, _ in vd:
            cv.text((X(d), y1 + 20), f"{d}年代", th.size_note, color=th.sub, alpha=a, anchor="ma")
        p = ramp(st.t, st.at(0) + 0.6, 2.5)
        k_show = p * (len(vd) - 1)
        ptsv = [(X(d), Y(v)) for d, v, _ in vd]
        for i in range(len(ptsv) - 1):
            f = min(max(k_show - i, 0), 1)
            if f <= 0:
                continue
            (ax, ay), (bx, by) = ptsv[i], ptsv[i + 1]
            cv.line([(ax, ay), (ax + (bx - ax) * f, ay + (by - ay) * f)], th.accent, 6, 1)
        for i, (x, y) in enumerate(ptsv):
            if i <= k_show + 1e-6:
                cv.d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=th.accent)
        h1 = ramp(st.t, st.at(1), 0.6)
        d70 = next(v for d, v, _ in vd if d == 1970)
        cv.text((X(1970), Y(d70) - 30), f"{d70:.2f}", th.size_body, bold=True, color=th.accent, alpha=h1, anchor="md")
        h2 = ramp(st.t, st.at(2), 0.6)
        d10 = next(v for d, v, _ in vd if d == 2010)
        cv.text((X(2010), Y(d10) - 30), f"{d10:.2f}", th.size_body, bold=True, color=th.accent, alpha=h2, anchor="md")
        cv.note("縦軸＝レーベルと分野の関連の強さ（クラメールの V、0〜1）。10年ごとに30点以上の一般向けシリーズで計算。シリーズの数は年代で異なる",
                ramp(st.t, st.at(0) + 0.6, 0.6))

    time_sc = Scene("時代の変化", [
        Line("実は、一般向けのレーベルが似てきたのは、比較的最近のことです。"),
        Line("1970年代には、レーベルごとの分野の違いが、今よりずっと大きくありました。"),
        Line("2000年代に新しいレーベルが次々と生まれるなかで、違いは小さくなっています。"),
    ], d_time, tail=1.8, shots=[
        Shot("岩波新書の赤版・青版・黄版・新赤版の装丁の変遷", "時代による変化を実物で示す", line=1, seconds=4.0,
             angle="時代順に左から並べる", notes="古書の入手・図書館での撮影許可を確認", placeholder="折れ線グラフ"),
    ])

    # 9 分野を絞ったレーベル
    sp = N["special"]

    def d_special(cv, st):
        th = cv.th
        cv.title("分野を絞ったレーベル", ramp(st.t, 0, 0.4))
        for k, (l, field_name, shares, icon) in enumerate(sp):
            r_, c_ = divmod(k, 3)
            cx = W / 2 + (c_ - 1) * 560
            cy = 300 + r_ * 300
            a = ramp(st.t, st.at(0) + 0.4 + 0.25 * k, 0.6)
            c = cat_key(S[l]["category"])
            svgicons.draw(cv, icon, cx - 190, cy, 64, CAT_COLOR[c], a)
            cv.text((cx - 140, cy - 26), l, th.size_body - 4, bold=True, alpha=a, anchor="lm")
            yrs = f"{S[l]['titles']}点" + ("（2019年まで）" if S[l]["status"] == "ended" else "")
            cv.text((cx - 140, cy + 18), yrs, th.size_note - 2, color=th.sub, alpha=a, anchor="lm")
            bx0, bx1, by = cx - 230, cx + 230, cy + 70
            cv.rect((bx0, by, bx1, by + 26), th.muted, a, radius=4)
            p = ramp(st.t, st.at(0) + 0.8 + 0.25 * k, 1.0)
            acc = bx0
            for j, s in enumerate(shares):
                w = (bx1 - bx0) * s * p
                cv.rect((acc, by, acc + w, by + 26), mix(CAT_COLOR[c], (255, 255, 255), 1.0 if j == 0 else 0.55), a)
                acc += w
            label = field_name.format(*map(pct, shares)) if "{}" in field_name else f"{field_name} {pct(shares[0])}"
            cv.text((cx, by + 40), label, th.size_note - 2, alpha=a * min(1.0, p * 1.5), anchor="ma")
        cv.note("2016〜2025年の各シリーズの点数に占める割合。日本十進分類法の上2桁で判定（医学＝49、運輸＝68、キリスト教＝19 など）",
                ramp(st.t, st.at(3), 0.6))

    special = Scene("分野を絞ったレーベル", [
        Line("一方、分野を絞ったレーベルは、はっきり際立っています。"),
        Line("交通新聞社新書は、本の7割が鉄道などの運輸。ヨベル新書は、8割以上がキリスト教です。"),
        Line("ブルーバックスは自然科学が中心で、医学を除いても6割を占めます。"),
        Line("自然科学の区分には医学も入るため、ここでは細かい分類で中身を確かめました。"),
    ], d_special, tail=1.8, shots=[
        Shot("ブルーバックス・交通新聞社新書など分野特化のレーベルの実物", "専門のレーベルを実物で示す", line=1,
             seconds=4.0, angle="正面、表紙の文字が読める距離", notes="自分で所有する本を使う。書影の公開の可否は別に確認",
             placeholder="アイコンと割合の棒"),
    ])

    # 10 歴史：割合と点数
    hist = N["hist"]
    hl_hist = {"中公新書", "歴史新書y", "ちくま新書", "文春新書", "じっぴコンパクト新書", "潮新書"}

    def d_hist(cv, st):
        th = cv.th
        cv.title("歴史の本：割合と点数", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0), 0.6)
        x0, x1, y0, y1 = M + 200, W - M - 140, 190, 780

        def X(s):
            return x0 + s / 0.8 * (x1 - x0)

        def Y(n):
            return y1 - n / 20 * (y1 - y0)
        for s in (0, 0.2, 0.4, 0.6, 0.8):
            cv.line([(X(s), y1), (X(s), y1 + 10)], th.grid, 2, a)
            cv.text((X(s), y1 + 18), pct(s), th.size_note, color=th.sub, alpha=a, anchor="ma")
        for n in (0, 5, 10, 15, 20):
            cv.line([(x0, Y(n)), (x1, Y(n))], th.grid, 2, a)
            cv.text((x0 - 16, Y(n)), f"{n}", th.size_note, color=th.sub, alpha=a, anchor="rm")
        cv.text((W / 2, y1 + 56), "歴史・地理の本の割合", th.size_note + 2, color=th.sub, alpha=a, anchor="ma")
        cv.text((x0 - 16, y0 - 34), "年平均の点数", th.size_note + 2, color=th.sub, alpha=a, anchor="lm")
        h1 = ramp(st.t, st.at(1), 0.6)
        h2 = ramp(st.t, st.at(2), 0.6)
        for l, s, n, c in hist:
            x, y = X(s), Y(n)
            col = th.muted
            if l == "中公新書":
                col = mix(th.accent, th.muted, h2)
            elif s > 0.35:
                col = mix(CAT_COLOR[c], th.muted, h1)
            cv.d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=mix(col, th.bg, a))
        for l, s, n, c in hist:
            if l not in hl_hist:
                continue
            al = h2 if l == "中公新書" or s <= 0.35 else h1
            x, y = X(s), Y(n)
            cv.text((x + 18, y - 4), l, th.size_note, bold=l == "中公新書",
                    color=th.accent if l == "中公新書" else th.text, alpha=al, anchor="lm")
        cv.note("2016〜2025年に20点以上の67シリーズ。歴史・地理＝日本十進分類法の2類", ramp(st.t, st.at(0) + 0.5, 0.6))

    history = Scene("歴史：割合と点数", [
        Line("では、「中公新書は歴史に強い」は本当でしょうか。"),
        Line("歴史の本の割合だけなら、歴史を専門にしたレーベルなどが、中公新書を上回ります。"),
        Line("けれども、歴史の本をいちばん多く出しているのは中公新書で、年に17点ほどです。"),
        Line("一般向けの大きなレーベルの中では割合もいちばん高く、このイメージは数字で裏付けられました。"),
    ], d_hist, tail=1.8)

    # 11 著者
    def d_authors(cv, st):
        th = cv.th
        cv.title("研究者・大学教員の著者の割合", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(1), 0.6)
        x0, x1 = M + 360, W - M - 200
        for v in (0, 0.25, 0.5, 0.75, 1.0):
            x = x0 + (x1 - x0) * v
            cv.line([(x, 200), (x, 720)], th.grid, 2, a)
            cv.text((x, 730), pct(v), th.size_note, color=th.sub, alpha=a, anchor="ma")
        rng = ramp(st.t, st.at(4), 0.8)
        for k, (l, s, lo, hi, m) in enumerate(N["authors"]):
            y = 230 + k * 70
            p = ramp(st.t, st.at(2) + 0.15 * k, 0.9)
            cv.text((x0 - 24, y + 20), l, th.size_note + 4, alpha=a, anchor="rm")
            if rng > 0:
                cv.rect((x0 + (x1 - x0) * lo, y + 4, x0 + (x1 - x0) * hi, y + 36), mix(th.accent, th.bg, 0.25), rng, radius=4)
            cv.rect((x0, y + 10, x0 + (x1 - x0) * s * p, y + 30), th.accent, a)
            cv.text((x0 + (x1 - x0) * s * p + 14, y + 20), pct(s), th.size_note + 4, bold=True, alpha=a * min(1, p * 1.5),
                    anchor="lm")
            cv.text((x1 + 150, y + 20), f"照合 {pct(m)}", th.size_note - 2, color=th.sub, alpha=rng, anchor="rm")
        cv.note(f"最初の著者を Wikidata で照合（照合率 {pct(N['author_match_all'])}）。棒＝照合できた中の割合、帯＝未照合が全員研究者／全員それ以外の範囲",
                ramp(st.t, st.at(1), 0.6))

    authors = Scene("著者", [
        Line("分野が似ている一般向けのレーベルでも、書き手には違いがあります。"),
        Line("最初の著者の職業を、ウィキデータという公開のデータベースで調べました。"),
        Line("職業が分かった著者のうち、研究者や大学教員は、中公新書、岩波新書、ちくま新書で7割から8割。"),
        Line("新潮新書やSB新書では、3割ほどでした。"),
        Line("ただし、職業が分かったのは著者の半分ほどなので、幅をもって見る必要があります。"),
    ], d_authors, tail=1.8)

    # 12 ベストセラー
    best = N["best"]
    others_top = [l for l, n in sorted(best.items(), key=lambda x: -x[1])
                  if n >= 8 and l not in ("新潮新書", "中公新書")]
    groups_b = [("新潮新書", best["新潮新書"], th_accent, True),
                ("中公新書", best["中公新書"], hexrgb("1F2328"), True),
                ("・".join(l.replace("新書", "") for l in others_top), sum(best[l] for l in others_top),
                 hexrgb("8E98A3"), False)]
    rest = 100 - sum(n for _, n, _, _ in groups_b)

    def d_best(cv, st):
        th = cv.th
        cv.title("年間ベストセラー上位10点への登場", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(1), 0.6)
        seq = []
        for _, n, col, _ in groups_b:
            seq += [col] * n
        cell = 50
        gx = W / 2 - 640
        p = ramp(st.t, st.at(2) - 0.3, 2.0)
        for k in range(100):
            r_, c_ = divmod(k, 10)
            col = seq[k] if k < len(seq) and k < p * len(seq) else th.muted
            cv.rect((gx + c_ * cell, 210 + r_ * cell, gx + c_ * cell + cell - 8, 210 + r_ * cell + cell - 8), col, a, radius=5)
        lx = gx + 10 * cell + 80
        items = [(lab, n, col, big) for lab, n, col, big in groups_b] + [("その他のレーベル", rest, th.muted, False)]
        for k, (lab, n, col, big) in enumerate(items):
            y = 250 + k * 100
            al = ramp(st.t, st.at(2) + 0.4 * k, 0.5)
            cv.rect((lx, y - 16, lx + 32, y + 16), col, al, radius=4)
            cv.text((lx + 50, y), lab, th.size_body if big else th.size_note + 2, bold=big, alpha=al, anchor="lm")
            cv.text((lx + 760, y), f"{n}枠", th.size_body, bold=True, alpha=al, anchor="rm")
        al = ramp(st.t, st.at(2) + 1.8, 0.5)
        cv.text((lx + 50, 250 + 4 * 100), "岩波新書", th.size_body, bold=True, alpha=al, anchor="lm")
        cv.text((lx + 760, 250 + 4 * 100), f"{best.get('岩波新書', 0)}枠", th.size_body, bold=True, alpha=al, anchor="rm")
        cv.note("トーハン調べ 年間ベストセラー 新書ノンフィクション 2016〜2025年の上位10点（100枠）。1マス＝1枠。販売部数ではない",
                ramp(st.t, st.at(1), 0.6))

    bests = Scene("売れ方", [
        Line("売れ方にも違いがあります。"),
        Line("トーハンの年間ベストセラーのうち、新書ノンフィクション部門の上位10点を、10年分数えました。"),
        Line("100枠のうち、新潮新書が21枠といちばん多く、中公新書が10枠。岩波新書は0でした。"),
        Line("ただし、これは上位10点に入った回数で、売り上げの全体を表すものではありません。"),
    ], d_best, tail=1.8)

    # 13 同じ出版社のレーベル
    pairs = N["pairs"]

    def d_pairs(cv, st):
        th = cv.th
        cv.title("同じ出版社のレーベルどうしの距離", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0), 0.6)
        x0, x1 = M + 640, W - M - 60
        vmax = 0.8

        def X(v):
            return x0 + v / vmax * (x1 - x0)
        y_top, y_bot = 200, 200 + len(pairs) * 82
        for v in (0, 0.2, 0.4, 0.6, 0.8):
            cv.text((X(v), y_bot + 14), f"{v:.1f}", th.size_note, color=th.sub, alpha=a, anchor="ma")
        cv.text((X(0), y_bot + 56), "近い（分野の割合が似ている）", th.size_note, color=th.sub, alpha=a, anchor="la")
        cv.text((X(vmax), y_bot + 56), "遠い", th.size_note, color=th.sub, alpha=a, anchor="ra")
        med = N["dist_median"]
        cv.line([(X(med), y_top - 10), (X(med), y_bot)], th.compare, 3, a)
        cv.text((X(med), y_top - 18), f"全組み合わせの中央値 {med:.2f}", th.size_note - 2, color=th.sub, alpha=a, anchor="md")
        steps = [st.at(1), st.at(1), st.at(1) + 0.4, st.at(2), st.at(3) - 0.6, st.at(3) - 0.4, st.at(3)]
        for k, ((pa, pb, d), t0) in enumerate(zip(pairs, steps)):
            y = y_top + 20 + k * 82
            al = ramp(st.t, t0 + 0.12 * k, 0.6)
            col = NEAR if d < med else FAR
            cv.text((x0 - 40, y + 16), f"{pa} − {pb}", th.size_note + 2, alpha=al, anchor="rm")
            cv.line([(X(0), y + 16), (X(d), y + 16)], th.grid, 4, al)
            cv.d.ellipse((X(d) - 13, y + 3, X(d) + 13, y + 29), fill=mix(col, th.bg, al))
            tag(cv, (X(d) + 24, y + 16), f"{d:.2f}", th.size_note, col, al, "lm")
        cv.note("分野（日本十進分類法の第1次区分）の割合の距離（ジェンセン・シャノン距離、0＝同じ）。2016〜2025年",
                ramp(st.t, st.at(1), 0.6))

    pubs = Scene("出版社の使い分け", [
        Line("同じ出版社が、複数のレーベルをどう使い分けているかも見えてきます。"),
        Line("ちくま新書とちくまプリマー新書、それに、岩波新書と岩波ジュニア新書は、分野の割合が近く、おもに読者の年齢で分けています。",
             say="ちくましんしょとちくまぷりまーしんしょ、それに、イワナミシンショとイワナミジュニアシンショは、分野の割合が近く、"
                 "おもに読者の年齢で分けています。"),
        Line("中公新書と、同じ出版社の中公新書ラクレも比較的近いのですが、ラクレのほうは歴史の本が少なく、社会科学の本が中心です。",
             say="ちゅうこうしんしょと、同じ出版社のちゅうこうしんしょラクレも比較的近いのですが、ラクレのほうは歴史の本が少なく、"
                 "社会科学の本が中心です。"),
        Line("一方、講談社現代新書とブルーバックスは、同じ出版社の中でも分野がはっきり違います。"),
    ], d_pairs, tail=1.8)

    # 14 イメージの照合
    rows = [("中公新書", "歴史に強い", "歴史の本が最も多い（年17点）", "check"),
            ("中公・岩波・ちくま", "学術的", "研究者の著者が7〜8割（照合できた中）", "check"),
            ("新潮新書", "大衆向け", "ベストセラー上位に最多の21枠", "check"),
            ("岩波・講談社現代", "分野が幅広い", "一般向けに共通（際立たない）", "alert-triangle"),
            ("PHP新書", "ビジネス", "ビジネスは PHPビジネス新書", "x"),
            ("各レーベル", "政治色・読みやすさ", "出版の記録では確かめられない", "question-mark")]
    marks = {"check": th_accent, "alert-triangle": hexrgb("8E98A3"), "x": hexrgb("5B6470"), "question-mark": hexrgb("8E98A3")}
    mark_name = {"check": "一致", "alert-triangle": "際立たない", "x": "一致しない", "question-mark": "未検証"}

    def d_check(cv, st):
        th = cv.th
        cv.title("イメージとデータ", ramp(st.t, 0, 0.4))
        a = ramp(st.t, st.at(0), 0.6)
        cx = [M + 40, M + 460, M + 860, W - M - 60]
        for x, h in zip(cx[:3], ["レーベル", "イメージ", "データ"]):
            cv.text((x, 190), h, th.size_note, color=th.sub, alpha=a)
        cv.text((cx[3], 190), "判定", th.size_note, color=th.sub, alpha=a, anchor="ra")
        steps = [st.at(1), st.at(1) + 0.8, st.at(1) + 1.6, st.at(2), st.at(3), st.at(4)]
        for k, ((l, img, dat, mk), t0) in enumerate(zip(rows, steps)):
            y = 260 + k * 100
            al = ramp(st.t, t0, 0.6)
            cv.line([(M + 20, y - 26), (W - M - 20, y - 26)], th.grid, 2, a)
            cv.text((cx[0], y + 10), l, th.size_note + 4, bold=True, alpha=al, anchor="lm")
            cv.text((cx[1], y + 10), f"「{img}」", th.size_note + 4, alpha=al, anchor="lm")
            cv.text((cx[2], y + 10), dat, th.size_note + 2, color=th.sub, alpha=al, anchor="lm")
            svgicons.draw(cv, mk, cx[3] - 200, y + 10, 44, marks[mk], al, stroke=2.2)
            cv.text((cx[3], y + 10), mark_name[mk], th.size_note + 2, bold=True, color=marks[mk], alpha=al, anchor="rm")
        cv.note("イメージ＝ネット上の個人の記述。「学術的」は著者の職業という代理の指標で確かめた", ramp(st.t, st.at(1), 0.6))

    check = Scene("イメージの照合", [
        Line("最初に挙げたイメージを、データと照らし合わせます。"),
        Line("中公新書の歴史。中公新書、岩波新書、ちくま新書の学術的。新潮新書の大衆向け。これらは、データと一致しました。"),
        Line("岩波新書や講談社現代新書は分野が幅広いと言われますが、幅広さは一般向けのレーベルに共通していて、際立った特徴ではありません。"),
        Line("PHP新書のビジネスのイメージは、実際には別のレーベル、PHPビジネス新書の特徴でした。"),
        Line("政治的な傾向や読みやすさは、出版の記録からは確かめられません。"),
    ], d_check, tail=2.0)

    # 15 結論
    panels = [("category", "分野", "一般向けどうしは似ている\n分野を絞ったレーベルは際立つ"),
              ("user", "書き手", "研究者の割合に\nはっきりした差"),
              ("trophy", "売れ方", "ベストセラーは\n一部のレーベルに集中")]

    def d_end(cv, st):
        th = cv.th
        cv.title("レーベルの違いはどこに表れるか", ramp(st.t, 0, 0.4))
        steps = [st.at(1), st.at(1) + 1.5, st.at(1) + 3.0]
        for k, ((icon, head, body), t0) in enumerate(zip(panels, steps)):
            x = W / 2 + (k - 1) * 520
            a = ramp(st.t, t0, 0.6)
            cv.rect((x - 230, 220, x + 230, 640), (255, 255, 255), a, radius=16)
            svgicons.draw(cv, icon, x, 320, 96, th.accent, a)
            cv.text((x, 420), head, th.size_title, bold=True, alpha=a, anchor="ma")
            for j, ln in enumerate(body.split("\n")):
                cv.text((x, 520 + j * 44), ln, th.size_note + 4, color=th.sub, alpha=a, anchor="ma")
        b = ramp(st.t, st.at(3), 0.6)
        svgicons.draw(cv, "circle-check", W / 2 - 330, 760, 56, th.accent, b, stroke=2.0)
        cv.text((W / 2 - 290, 760), "語られるイメージ：確かめられる範囲では多くが一致", th.size_body, bold=True, alpha=b, anchor="lm")

    end = Scene("結論", [
        Line("まとめます。"),
        Line("一般向けのレーベルは、扱う分野ではよく似ています。違いが表れるのは、書き手と売れ方です。"),
        Line("分野ではっきり違うのは、科学や鉄道、宗教など、分野を絞った専門のレーベルでした。"),
        Line("そして、よく語られるイメージは、データで確かめられる範囲では、多くが当たっていました。"),
    ], d_end, tail=2.2)

    # 16 限界とクレジット
    credits = [("データ", "国立国会図書館サーチ（API を利用）、Wikidata（CC0）、トーハン調べ 年間ベストセラー"),
               ("音声", voice_credit), ("音楽", music_credit)]

    def d_close(cv, st):
        th = cv.th
        a = ramp(st.t, st.at(0), 0.6)
        svgicons.draw(cv, "books", W / 2, 230, 96, th.text, a)
        cv.text((W / 2, 320), f"主な新書 {N['n_labels']}シリーズ・{N['n_titles']:,}点の集計", th.size_body, bold=True,
                alpha=a, anchor="ma")
        b = ramp(st.t, st.at(1), 0.6)
        cv.text((W / 2, 410), "本の中身・紙面・読みやすさは、実物を調べていないため扱っていない", th.size_note + 4,
                color=th.sub, alpha=b, anchor="ma")
        c = ramp(st.t, st.at(2), 0.6)
        for k, (h, body) in enumerate(credits):
            y = 560 + k * 64
            cv.text((W / 2 - 700, y), h, th.size_note + 2, bold=True, alpha=c)
            cv.text((W / 2 - 540, y), body, th.size_note + 2, color=th.sub, alpha=c)

    close = Scene("限界とクレジット", [
        Line("この調査は、国立国会図書館の書誌をもとにした、主な137シリーズの集計です。"),
        Line("本の中身や紙面の読みやすさは、実物を調べていないため扱っていません。"),
        Line("データと方法の詳細は、概要欄にまとめています。"),
    ], d_close, tail=3.0, shots=[
        Shot("判型・厚さ・紙面の比較、参考文献・索引・奥付", "研究で扱っていない紙面・造本を実物で示す（今後の調査）",
             line=1, seconds=5.0, angle="見開きを真上から、定規を添える", notes="本文の長い引用にならないよう映す範囲を限る",
             placeholder="アイコンと文"),
    ])

    scenes = [intro, image, data, ndc, lmap, size_sc, general, time_sc, special, history, authors, bests, pubs, check,
              end, close]
    for sc in scenes:
        for ln in sc.lines:
            if ln.say is None and yomi(ln.text) != ln.text:
                ln.say = yomi(ln.text)
    return scenes
