"""出典ページの原文から該当箇所を抜き出す

使い方: python quote.py URL キーワード [キーワード...]
ページを取得してテキスト化し、キーワードを含む前後の文を表示する
取得したページは CACHE/web/ に保存し、根拠の再確認に使う
"""
import hashlib
import re
import sys
import time

import pymupdf
import requests
from bs4 import BeautifulSoup

from paths import CACHE

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}


def page_text(url):
    d = CACHE / "web"
    d.mkdir(parents=True, exist_ok=True)
    f = d / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".txt")
    if f.exists():
        return f.read_text(encoding="utf-8")
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    if r.content[:4] == b"%PDF":
        with pymupdf.open(stream=r.content, filetype="pdf") as doc:
            raw = "\n".join(p.get_text() for p in doc)
    else:
        r.encoding = r.apparent_encoding if r.encoding in (None, "ISO-8859-1") else r.encoding
        soup = BeautifulSoup(r.text, "lxml")
        for t in soup(["script", "style", "noscript"]):
            t.decompose()
        raw = soup.get_text("\n")
    text = re.sub(r"[ \t　]+", " ", raw)
    text = re.sub(r"\n\s*\n+", "\n", text)
    f.write_text(f"URL: {url}\nFETCHED: {time.strftime('%Y-%m-%d')}\n\n{text}", encoding="utf-8")
    return f.read_text(encoding="utf-8")


def main():
    url, *keys = sys.argv[1:]
    try:
        text = page_text(url)
    except Exception as e:
        print("FETCH_ERROR", e)
        return
    flat = text.replace("\n", " ")
    hits = 0
    for k in keys:
        for m in re.finditer(re.escape(k), flat):
            print(f"[{k}] …{flat[max(0, m.start() - 120):m.end() + 120]}…")
            hits += 1
            if hits >= 8:
                return
    if not hits:
        print("NO_MATCH", len(flat))


if __name__ == "__main__":
    main()
