"""Iの部が取得できない企業について、最新の有価証券報告書の転載ページから沿革と役員略歴を取得する

使い方: python fetch_mirror.py キー [キー ...]
取得元: kitaishihon.com（有価証券報告書の「沿革」「役員の状況」を転載）
上場廃止済みの企業はページが存在しない
出力: CACHE/mirror/<key>_story.txt, <key>_board.txt
"""
import re
import subprocess
import sys
import time

from bs4 import BeautifulSoup

from paths import CACHE

PAGES = {"story": "story", "board": "board-of-director"}


def fetch(code, page):
    url = f"https://kitaishihon.com/company/{code}/{page}"
    r = subprocess.run(["curl", "-s", "-m", "60", "-A", "Mozilla/5.0", url], capture_output=True)
    html = r.stdout.decode("utf-8", "ignore")
    text = BeautifulSoup(html, "lxml").get_text("\n", strip=True) if html else ""
    return url, text


def main():
    out = CACHE / "mirror"
    out.mkdir(parents=True, exist_ok=True)
    for key in sys.argv[1:]:
        code = key.split("_")[1]
        for name, page in PAGES.items():
            dest = out / f"{key}_{name}.txt"
            if dest.exists():
                continue
            url, text = fetch(code, page)
            if not text:
                # 空の応答（回数制限など）は保存せず、次回の実行で取り直す
                print(key, name, "empty", flush=True)
                time.sleep(10)
                continue
            src = re.search(r"\d{4}年\d{1,2}月期有価証券報告書より", text)
            dest.write_text(f"URL: {url}\nSOURCE: {src.group(0) if src else ''}\n\n{text}", encoding="utf-8")
            time.sleep(2)
        print(key, "ok", flush=True)


if __name__ == "__main__":
    main()
