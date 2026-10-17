"""転載ページ（有価証券報告書）から判定用ダイジェストを出力する

使い方: python mirror_digest.py キー [キー ...]
"""
import re
import sys

from extract_part1 import ZEN, officers, seireki
from paths import CACHE


def short(s, n):
    s = re.sub(r"\s+", " ", s or "")
    return s if len(s) <= n else s[:n] + "…"


def main():
    for key in sys.argv[1:]:
        story = (CACHE / "mirror" / f"{key}_story.txt")
        board = (CACHE / "mirror" / f"{key}_board.txt")
        print(f"## {key}")
        if not story.exists():
            print("  (未取得)")
            continue
        st = seireki(story.read_text(encoding="utf-8").translate(ZEN))
        src = re.search(r"SOURCE: (.*)", st).group(1)
        body = st.split("【沿革】", 1)[1] if "【沿革】" in st else ""
        if not body:
            print("  (ページなし：上場廃止の可能性)")
            continue
        print(f"  出典: {src}")
        print("  沿革:", short(body.replace("\n", " "), 380))
        bt = seireki(board.read_text(encoding="utf-8").translate(ZEN)) if board.exists() else ""
        bt = bt.split("【役員の状況】", 1)[1] if "【役員の状況】" in bt else ""
        offs, _ = officers([bt])
        for o in offs:
            if o["founder_flag"] or "代表" in o["title"]:
                flag = "★" if o["founder_flag"] else ""
                print(f"  {flag}{short(o['title'], 20)} {o['name']} ({o['birth'][:4]}) {short(o['career'].replace('/', ' '), 200)}")


if __name__ == "__main__":
    main()
