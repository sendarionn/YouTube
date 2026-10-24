"""書誌データの取得：候補シリーズごとに、国立国会図書館サーチから全件を集める

使い方：python collect.py [シリーズ名 ...]（省略時は label_candidates.csv の全件）
- 1回の検索で取れるのは500件まで（tools/research/ndl.py）。10年ごとに検索し、500件を超える10年は
  年・月・日に分けて検索する
- 書誌のシリーズ名が series_pattern に合うものだけを残し、NDL書誌ID で重複を除く
- 出力：cache/shinsho-labels/raw/<シリーズ名>.jsonl（取得した書誌、Git 管理外）、data/collect_log.csv（区間ごとの件数）
- 応答は cache/ndl/ に保存され、再実行ではそれを使う（--offline で API に問い合わせない）
"""
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from tools.infographic.config import CACHE  # noqa: E402
from tools.research import ndl  # noqa: E402

DATA = HERE.parent / "data"
RAW = CACHE / "shinsho-labels" / "raw"
FIRST, LAST = 1930, 2026


def collect(c, offline=False):
    pat = re.compile(c["series_pattern"])
    params = {"dpid": "iss-ndl-opac", "title": c["query"]}
    seen, log = {}, []
    # 10年ごとに検索し、500件を超える10年は年（さらに月・日）に分ける（ndl.search_by_date）
    for d in range(FIRST, LAST + 1, 10):
        items, lg = ndl.search_by_date(params, d, min(d + 9, LAST), offline=offline)
        kept = 0
        for r in items:
            if any(pat.search(s) for s in r["series"]):
                bid = (r["ids"].get("NDLBibID") or [r["link"]])[0]
                if bid not in seen:
                    seen[bid] = r
                    kept += 1
        for e in lg:
            log.append({"label": c["label"], **e})
        log.append({"label": c["label"], "from": str(d), "until": str(min(d + 9, LAST)), "records": "",
                    "shortfall": "", "kept_in_series": kept})
    RAW.mkdir(parents=True, exist_ok=True)
    with (RAW / f"{c['label']}.jsonl").open("w", encoding="utf-8") as f:
        for r in seen.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return seen, log


def main():
    offline = "--offline" in sys.argv
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    rows = list(csv.DictReader((DATA / "label_candidates.csv").open(encoding="utf-8")))
    if names:
        rows = [r for r in rows if r["label"] in names]
    log_path = DATA / "collect_log.csv"
    old = [r for r in csv.DictReader(log_path.open(encoding="utf-8"))] if log_path.exists() else []
    old = [r for r in old if r["label"] not in {c["label"] for c in rows}]
    logs = []
    for c in rows:
        seen, log = collect(c, offline)
        logs += log
        short = sum(int(e["shortfall"] or 0) for e in log)
        print(f"{c['label']}：{len(seen)} 件（シリーズ名が一致）、取りこぼしの可能性 {short} 件", flush=True)
    fields = ["label", "from", "until", "records", "shortfall", "kept_in_series"]
    with log_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        w.writerows(old + logs)


if __name__ == "__main__":
    main()
