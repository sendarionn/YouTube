"""複数の出典を一括で原文確認する

標準入力: 1行に「founder_id|URL|キーワード1,キーワード2」
各行について、キーワードを含む最初の箇所を前後付きで表示する
"""
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from quote import page_text


def check(line):
    fid, url, keys = line.strip().split("|", 2)
    try:
        flat = page_text(url).replace("\n", " ")
    except Exception as e:
        return f"{fid} FETCH_ERROR {str(e)[:80]}"
    for k in keys.split(","):
        m = re.search(re.escape(k), flat)
        if m:
            return f"{fid} [{k}] …{flat[max(0, m.start() - 90):m.end() + 110]}…"
    return f"{fid} NO_MATCH"


def main():
    lines = [l for l in sys.stdin if l.strip()]
    with ThreadPoolExecutor(6) as ex:
        for out in ex.map(check, lines):
            print(out, flush=True)


if __name__ == "__main__":
    main()
