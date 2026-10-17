"""創業者の略歴（Iの部・有価証券報告書）から職歴の変数を作る

出力: data/founders_career.csv
- age_at_founding: 創業年 − 生年
- first_job_year / first_employer: 略歴の最初の勤務先
- pre_employers: 創業前の勤務先（略歴の記載順）
- last_employer: 創業直前の勤務先
- years_before: 創業年 − 最初の勤務年
- serial: 創業前に別会社の設立・創業・開業の記載がある
- student_founder: 創業前の勤務先がなく、創業時25歳以下
- cat_*: 勤務先の分類（一人が複数に該当してよい）
- large_org: 分類辞書に該当する大手組織での勤務経験（定義は methodology.md）
"""
import re

import pandas as pd

from paths import DATA

DATE = re.compile(r"(\d{4})年\s*(\d{1,2})月")
JOIN = re.compile(r"入社|入行|入所|入省|入庁|入職|入局|入団|転籍|出向|参画|勤務|就職|入隊|就任|入所|研究員|講師|助教|教授|医員")
FOUND = re.compile(r"設立|創業|開業|起業|創立|独立")

# 分類辞書：勤務先名に含まれる語で判定する
CATS = {
    "consulting": r"コンサルティング|コンサルタント|マッキンゼー|McKinsey|ボストン・?コンサルティング|ベイン|A\.?T\.?\s?カーニー|Kearney|アクセンチュア|アンダーセン|アーサー|デロイト|トーマツコンサル|アビーム|プライスウォーターハウス|PwC|KPMG|アーンスト|野村総合研究所|野村総研|日本総合研究所|日本総研|三菱総合研究所|ローランド・?ベルガー|モニター|コーポレイトディレクション|ドリームインキュベータ|クニエ|ザカティ|船井総合研究所|日本エル・シー・エー|ベイカレント|ピーシーワークス|フロンティア・マネジメント|グリフィン",
    "finance": r"銀行|証券|信託|生命保険|損害保険|海上火災|火災海上|アセット|投資顧問|投資銀行|キャピタル|ファンド|ゴールドマン|モルガン|メリル|リーマン|UBS|シティ|クレディ|ドイツ証券|JPモルガン|ジャフコ|産業革新機構|産業革新投資機構|インテグラル|ユニゾン|カーライル|ベインキャピタル|ブラックロック|オリックス|リース|クレジット|ジェーシービー|JCB|信販|保険",
    "accounting_legal": r"監査法人|会計事務所|会計士|税理士|法律事務所|弁護士|特許事務所",
    "trading": r"三菱商事|三井物産|伊藤忠|住友商事|丸紅|双日|日商岩井|豊田通商|兼松|トーメン|ニチメン|住金物産",
    "net_megaventure": r"リクルート|ディー・エヌ・エー|DeNA|サイバーエージェント|グリー|楽天|ヤフー|Yahoo|LINE|ミクシィ|ライブドア|GMO|インテリジェンス|パーソル|オプト|セプテーニ|エス・エム・エス|ドリコム|ZOZO|スタートトゥデイ|メルカリ|ガイアックス|マイクロアド|アカツキ|ベクトル|光通信|ネットエイジ",
    "foreign_tech": r"グーグル|Google|アマゾン|Amazon|マイクロソフト|Microsoft|IBM|アイ・ビー・エム|オラクル|Oracle|SAP|Facebook|フェイスブック|アップル|Apple|インテル|Intel|シスコ|Cisco|セールスフォース|Salesforce|ヒューレット|HP|デル|Dell|サン・マイクロ|EMC|アドビ|Adobe|シーベル|コグネックス|テキサス・インスツル",
    "jp_large_maker_infra": r"日立|東芝|ソニー|パナソニック|松下電器|富士通|日本電気|NEC|キヤノン|トヨタ|日産|本田技研|ホンダ|三菱電機|三菱重工|京セラ|NTT|日本電信電話|KDDI|電通|博報堂|シャープ|リコー|富士フイルム|富士ゼロックス|オムロン|キーエンス|ミスミ|武田薬品|エーザイ|アステラス|第一三共|資生堂|花王|ユニクロ|ファーストリテイリング|新日本製鐵|新日鐵|日本製鉄|住友電気|住友スリーエム|日東電工|ブリヂストン|JR|旅客鉄道|全日本空輸|日本航空|大日本印刷|凸版|味の素|サントリー|キリン|アサヒ|イオン|ジャスコ|セブン|大塚商会|SCSK|CSK|NTTデータ|日本ユニシス|野村システム|伊藤忠テクノ|新日鉄ソリューションズ|ソフトバンク|ベネッセ|ベルシステム24|パソナ|大和ハウス|積水|東京電力|関西電力|大成建設|鹿島|清水建設|大林組|竹中工務店|五洋建設|大京|ミサワ|三井不動産|三菱地所|住友不動産|東急|森ビル|森トラスト|オリエンタルランド|日本たばこ|JT",
    "public_academia": r"(?<![株社])(省|庁)(?!.*株式会社)|都庁|県庁|市役所|区役所|独立行政法人|国立研究開発法人|国立がん|大学(?!生)|高等専門学校|JAXA|宇宙航空研究開発機構|産業技術総合研究所|理化学研究所|国際電気通信基礎技術研究所|国連|UNIDO|世界銀行|日本政策投資銀行|日本開発銀行|議員|自衛隊|警視庁|マックスプランク|メイヨー",
    "medical": r"病院|医局|クリニック|医院|診療所|歯科|看護|薬局",
}


def split_entries(career):
    """略歴を「年月」と「記載」の組に分ける（年月と記載が別列の形式にも対応）"""
    text = career.replace("/", " ")
    # 改行由来の空白で「設 立」のように語が割れるのを直す
    text = re.sub(r"(?<=[^\x00-\x7F])\s+(?=[^\x00-\x7F\d])", "", text)
    dates = [(int(y), int(m)) for y, m in DATE.findall(text)]
    parts = [p.strip() for p in DATE.split(text)]
    # DATE.split は [前文, 年, 月, 記載, 年, 月, 記載, ...] を返す
    entries = [parts[i] for i in range(3, len(parts), 3)]
    if dates and sum(1 for e in entries if len(e) < 2) >= max(2, len(entries) // 2):
        # 年月が先に並び、記載が最後にまとめて出る形式：記載を「入社」等の語で区切る
        tail = entries[-1] if entries else ""
        chunks = re.split(r"(?<=入社|入行|入所|設立|就任|転籍|出向|退任|現任|入局|入職|入省|開業|創業|参画|修了|卒業)\s*", tail)
        entries = [c for c in chunks if c.strip()]
    return dates, entries


def org_of(entry):
    e = DATE.sub("", entry)
    e = re.sub(r"(入社|入行|入所|入省|入庁|入職|入局|転籍|出向|参画|就任|設立|代表取締役.*|取締役.*|（現任）|\(現任\)).*$", "", e)
    return re.sub(r"\s+", "", e)[:40]


def classify(row):
    career = row.career_p1 or ""
    out = {"founder_id": row.founder_id}
    by = int(row.birth[:4]) if row.birth else None
    oy = int(row.origin_ym[:4]) if row.origin_ym else None
    out["birth_year"] = by
    out["age_at_founding"] = oy - by if by and oy else None
    if not career:
        return out
    dates, entries = split_entries(career)
    company_kw = re.compile(r"当社|現当社|現 当社|現・当社")
    aligned = len(entries) == len(dates)
    pre = []
    for i, e in enumerate(entries):
        if company_kw.search(e):
            break
        # 個人事業などが起点の場合、創業年より後の経歴は創業前に含めない
        if aligned and oy and dates[i][0] > oy:
            break
        pre.append(e)
    pre_jobs = [e for e in pre if JOIN.search(e) and not FOUND.search(e)]
    pre_found = []
    for i, e in enumerate(pre):
        if not FOUND.search(e):
            continue
        if aligned and oy and dates[i][0] >= oy:
            continue  # 現在の事業の起点（個人事業・前身会社の開業）
        if not aligned and "個人事業" in e:
            continue
        pre_found.append(e)
    out["n_pre_entries"] = len(pre)
    out["first_employer"] = org_of(pre_jobs[0]) if pre_jobs else ""
    out["last_employer"] = org_of(pre_jobs[-1]) if pre_jobs else ""
    out["pre_employers"] = " | ".join(org_of(e) for e in pre_jobs)
    if pre_jobs and aligned:
        k = pre.index(pre_jobs[0])
        # 記載が空の行があると、年月と記載が1行ずれている。ずれの始まりの年月を使う
        empty = [j for j in range(k + 1) if len(pre[j]) < 2]
        out["first_job_year"] = dates[empty[0] if empty else k][0]
    else:
        out["first_job_year"] = dates[0][0] if dates and pre_jobs else None
    out["years_before"] = (oy - out["first_job_year"]) if oy and out["first_job_year"] else None
    out["serial"] = "Y" if pre_found else "N"
    out["student_founder"] = "Y" if (not pre_jobs and not pre_found and out["age_at_founding"] is not None and out["age_at_founding"] <= 25) else "N"
    # 学歴の行（卒業・修了など）は勤務先の分類から除く
    pre_text = " ".join(e for e in pre if not re.search(r"卒業|修了|入学|在学|中退|博士課程|学位", e))
    hit = []
    for c, pat in CATS.items():
        v = bool(re.search(pat, pre_text))
        out[f"cat_{c}"] = "Y" if v else "N"
        if v:
            hit.append(c)
    big = {"consulting", "finance", "trading", "net_megaventure", "foreign_tech", "jp_large_maker_infra"}
    out["large_org"] = "Y" if set(hit) & big else ("N" if pre_jobs else "")
    out["no_prior_job"] = "Y" if not pre_jobs else "N"
    return out


def main():
    f = pd.read_csv(DATA / "founders_base.csv", dtype=str).fillna("")
    rows = [classify(r) for r in f.itertuples()]
    out = pd.DataFrame(rows)
    out.to_csv(DATA / "founders_career.csv", index=False)
    print(len(out), "人", (out.get("first_employer", pd.Series(dtype=str)).fillna("") != "").sum(), "初職判明")


if __name__ == "__main__":
    main()
