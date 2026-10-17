"""Iの部（上場申請のための有価証券報告書）の取得とテキスト化

2022年以降はJPXから、2021年以前はWayback Machineから取得する
途中で止めても再実行すれば未取得分から再開する
出力: CACHE/pdf/<key>.pdf, CACHE/text/<key>.txt, CACHE/status/<key>.txt
`fetch_part1.py summary` で data/part1_status.csv に集計する
"""
import csv
import subprocess
import sys
import time

import pymupdf as fitz
import pandas as pd

from paths import CACHE, DATA

UA = {"User-Agent": "Mozilla/5.0 (research; founders-elite)"}


def key(row):
    return f"{row.listing_date}_{row.code}"


def candidates(row):
    url = row.part1_pdf
    if row.listing_year >= 2022:
        return [url, f"https://web.archive.org/web/2026id_/{url}"]
    # 削除後の404が保存されている場合があるため、上場年に近い時点から順に試す
    y = row.listing_year
    return [f"https://web.archive.org/web/{t}id_/{url}" for t in (y, y + 1, y + 3)]


def download(urls, dest):
    """取得できたURLを返す 404は"" 一時的な失敗は None
    Wayback Machineはrequestsだと応答しないことがあるためcurlを使う
    """
    transient = False
    for url in urls:
        for attempt in range(4):
            r = subprocess.run(["curl", "-sL", "-m", "180", "-o", str(dest), "-w", "%{http_code}", url],
                               capture_output=True, text=True)
            code = r.stdout.strip()
            if code == "200" and dest.exists() and dest.read_bytes()[:4] == b"%PDF":
                return url
            dest.unlink(missing_ok=True)
            if code == "404":
                transient = False
                break
            transient = True
            time.sleep(20 * (attempt + 1))
    return None if transient else ""


def to_text(pdf, txt):
    with fitz.open(pdf) as doc:
        pages = [f"\n=====PAGE {i + 1}=====\n" + p.get_text() for i, p in enumerate(doc)]
    txt.write_text("".join(pages), encoding="utf-8")
    return len(pages)


def main():
    rows = pd.read_csv(DATA / "jpx_listings.csv", dtype=str)
    rows["listing_year"] = rows.listing_year.astype(int)
    rows = rows[(rows.technical_listing == "0") & rows.part1_pdf.notna()]
    years = [int(y) for y in sys.argv[1:]]
    if years:
        rows = rows[rows.listing_year.isin(years)]
    for d in ("pdf", "text", "status"):
        (CACHE / d).mkdir(parents=True, exist_ok=True)
    for n, row in enumerate(rows.itertuples(), 1):
        k = key(row)
        txt = CACHE / "text" / f"{k}.txt"
        st = CACHE / "status" / f"{k}.txt"
        if txt.exists() or st.exists():
            continue
        pdf = CACHE / "pdf" / f"{k}.pdf"
        got = "cached" if pdf.exists() else download(candidates(row), pdf)
        if got is None:
            print(n, k, "retry-later", flush=True)
            continue
        if got:
            try:
                to_text(pdf, txt)
                st.write_text(f"ok\t{got}")
            except Exception as e:  # 壊れたPDF
                st.write_text(f"error\t{e}")
        else:
            st.write_text("missing\t")
        print(n, k, st.read_text().split("\t")[0], flush=True)
        time.sleep(3 if row.listing_year < 2022 else 1)


def summarize():
    """status/ をまとめて data/part1_status.csv に書き出す"""
    with open(DATA / "part1_status.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["key", "status", "url"])
        for p in sorted((CACHE / "status").glob("*.txt")):
            w.writerow([p.stem] + (p.read_text().split("\t", 1) + [""])[:2])


if __name__ == "__main__":
    if sys.argv[1:] == ["summary"]:
        summarize()
    else:
        main()
