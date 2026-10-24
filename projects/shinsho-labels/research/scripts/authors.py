"""著者属性：最初の著者を Wikidata（CC0）で照合し、職業から区分を決める

入力：data/titles.csv（first_creator, first_creator_birth）
出力：data/authors.csv（著者ごとの照合結果と区分）、cache/wikidata/（応答）
照合の規則
- Wikidata の人物（P31=Q5）で、日本語のラベルまたは別名が NDL の著者名（姓名をつなげたもの）と一致するもの
- NDL に生年がある場合は、Wikidata の生年（P569）が一致するものだけ。生年がない場合は、候補が1人のときだけ採用
- 一致する人物がいない・複数いて決められない場合は「照合できず」とし、推測で補わない
区分の規則（CLASSES。上から順に最初に当てはまるものを主な区分にする）
- 研究者・大学教員 → ジャーナリスト → 実務家・経営者 → 作家・評論家 → その他
- 職業（P106）だけで判定する。所属（P108）は記録するが区分には使わない（大学の非常勤など職業と一致しない場合があるため）
- 職業が「著作家」「翻訳家」だけの場合は「作家・評論家」に入れない（区分できないとして「その他」に入れる）
- 時点：Wikidata の現在の記述。執筆当時の職業とは限らない
"""
import csv
import hashlib
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from tools.infographic.config import CACHE  # noqa: E402

DATA = HERE.parent / "data"
WD_CACHE = CACHE / "wikidata"
ENDPOINT = "https://query.wikidata.org/sparql"
UA = "shinsho-labels-research/0.1 (non-commercial research script; https://github.com/sendarionn/YouTube)"

CLASSES = [
    ("研究者・大学教員", r"学者|研究者|大学教員|教授|准教授|科学者|研究員|物理学者|数学者|歴史家|考古学者|哲学者|人類学者|天文学者|化学者|生物学者|医学者"),
    ("ジャーナリスト", r"ジャーナリスト|記者|ノンフィクション作家|ルポライター|報道"),
    ("実務家・経営者", r"実業家|経営者|起業家|コンサルタント|投資家|弁護士|医師|精神科医|官僚|政治家|公務員|会計士|税理士|銀行家|外交官|裁判官|検察官|技術者|エンジニア|プログラマー|経済評論家|軍人|自衛官|教師|教員"),
    ("作家・評論家", r"小説家|作家|評論家|詩人|エッセイスト|随筆家|批評家|歌人|俳人|脚本家|コラムニスト|漫画家"),
]
OTHER = "その他"
WEAK = {"著作家", "翻訳家", "編集者"}

try:
    import certifi

    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()


def query(names):
    """日本語のラベル・別名が names のいずれかに一致する人物（生年、職業、所属）"""
    values = " ".join(json.dumps(n, ensure_ascii=False) + "@ja" for n in names)
    q = f"""SELECT ?name ?p ?birth (GROUP_CONCAT(DISTINCT ?occL;separator="|") AS ?occs)
 (GROUP_CONCAT(DISTINCT ?empL;separator="|") AS ?emps) WHERE {{
 VALUES ?name {{ {values} }}
 {{ ?p rdfs:label ?name }} UNION {{ ?p skos:altLabel ?name }}
 ?p wdt:P31 wd:Q5.
 OPTIONAL {{ ?p wdt:P569 ?birth }}
 OPTIONAL {{ ?p wdt:P106 ?occ. ?occ rdfs:label ?occL FILTER(lang(?occL)="ja") }}
 OPTIONAL {{ ?p wdt:P108 ?emp. ?emp rdfs:label ?empL FILTER(lang(?empL)="ja") }}
}} GROUP BY ?name ?p ?birth"""
    key = hashlib.sha1(q.encode()).hexdigest()[:16]
    path = WD_CACHE / f"{key}.json"
    if not path.exists():
        url = ENDPOINT + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        for attempt in range(5):
            try:
                body = urllib.request.urlopen(req, context=CTX, timeout=120).read()
                break
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(20 * (attempt + 1))
        WD_CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        time.sleep(1.5)
    return json.loads(path.read_text(encoding="utf-8"))["results"]["bindings"]


def classify(occs):
    occs = [o for o in occs if o]
    for name, pat in CLASSES:
        if any(re.search(pat, o) for o in occs if o not in WEAK):
            return name
    return OTHER if occs else ""


def main(batch=80):
    # 横断比較（2016〜2025年）の点の最初の著者だけを照合する
    titles = [t for t in csv.DictReader((DATA / "titles.csv").open(encoding="utf-8"))
              if t["year"] and 2016 <= int(t["year"]) <= 2025]
    people = sorted({(t["first_creator"], t["first_creator_birth"]) for t in titles if t["first_creator"]})
    names = sorted({n for n, _ in people})
    found = {}
    for i in range(0, len(names), batch):
        for b in query(names[i:i + batch]):
            found.setdefault(b["name"]["value"], []).append({
                "qid": b["p"]["value"].rsplit("/", 1)[-1],
                "birth": b.get("birth", {}).get("value", "")[:4],
                "occs": [o for o in b.get("occs", {}).get("value", "").split("|") if o],
                "emps": [e for e in b.get("emps", {}).get("value", "").split("|") if e]})
        print(f"  {min(i + batch, len(names))}/{len(names)}", flush=True)
    out = []
    for name, birth in people:
        cands = found.get(name, [])
        if birth:
            cands = [c for c in cands if c["birth"] == birth]
        status = "照合" if len(cands) == 1 else ("照合できず（候補なし）" if not cands else "照合できず（候補が複数）")
        c = cands[0] if len(cands) == 1 else None
        out.append({"name": name, "birth": birth, "status": status, "qid": c["qid"] if c else "",
                    "occupations": "|".join(c["occs"]) if c else "", "employers": "|".join(c["emps"]) if c else "",
                    "class": classify(c["occs"]) if c else ""})
    with (DATA / "authors.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(out[0]))
        w.writeheader()
        w.writerows(out)
    ok = sum(o["status"] == "照合" for o in out)
    print(f"著者 {len(out)} 人、照合 {ok} 人（{ok / len(out):.1%}）")


if __name__ == "__main__":
    main()
