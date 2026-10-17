"""途中で切れたIの部PDFを、Wayback Machineの別時点のコピーから取り直す

使い方: python refetch_bad.py キー [キー ...]
CDXで保存時点の一覧を取り、完全なPDFが得られるまで順に試す
"""
import subprocess
import sys
import time

import pandas as pd
import pymupdf

from fetch_part1 import to_text
from paths import CACHE, DATA

pymupdf.TOOLS.mupdf_display_errors(False)


def ok_pdf(path):
    if not path.exists() or path.stat().st_size == 1048576 or path.read_bytes()[:4] != b"%PDF":
        return False
    try:
        with pymupdf.open(path) as d:
            return len(d) >= 20
    except Exception:
        return False


def captures(url):
    q = f"https://web.archive.org/cdx/search/cdx?url={url}&fl=timestamp,original,length&filter=statuscode:200"
    r = subprocess.run(["curl", "-s", "-m", "120", q], capture_output=True, text=True)
    rows = [l.split() for l in r.stdout.strip().splitlines() if l.strip()]
    # サイズの大きい保存から試す
    return sorted(rows, key=lambda x: -int(x[2]) if len(x) > 2 and x[2].isdigit() else 0)


def main():
    jpx = pd.read_csv(DATA / "jpx_listings.csv", dtype=str)
    jpx["key"] = jpx.listing_date + "_" + jpx.code
    url_of = dict(zip(jpx.key, jpx.part1_pdf))
    for k in sys.argv[1:]:
        pdf = CACHE / "pdf" / f"{k}.pdf"
        tmp = CACHE / "pdf" / f"{k}.tmp"
        done = False
        for ts, orig, *_ in captures(url_of[k].replace("https://", "")):
            subprocess.run(["curl", "-sL", "-m", "300", "-o", str(tmp), f"https://web.archive.org/web/{ts}id_/{orig}"])
            if ok_pdf(tmp):
                tmp.replace(pdf)
                to_text(pdf, CACHE / "text" / f"{k}.txt")
                (CACHE / "status" / f"{k}.txt").write_text(f"ok\t{ts} {orig}")
                done = True
                break
            time.sleep(3)
        tmp.unlink(missing_ok=True)
        if not done:
            (CACHE / "status" / f"{k}.txt").write_text("truncated\t")
        print(k, "ok" if done else "truncated", flush=True)


if __name__ == "__main__":
    main()
