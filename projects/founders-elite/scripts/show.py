"""1社の沿革と役員一覧を表示する（判定保留の確認用）

使い方: python show.py キー接尾辞 [--hist N] [--off]
例: python show.py 339A --hist 1200 --off
"""
import json
import sys

from paths import CACHE, DATA


def main():
    suffix = sys.argv[1]
    n = int(sys.argv[sys.argv.index("--hist") + 1]) if "--hist" in sys.argv else 900
    for l in open(CACHE / "part1_extract.jsonl", encoding="utf-8"):
        e = json.loads(l)
        if not e["key"].endswith(suffix):
            continue
        print("##", e["key"], "| 沿革p", e.get("history_page"))
        print(e.get("history_intro", "")[:400])
        text = " / ".join(f"{d} {t}" for d, t in e.get("history", []))
        print(text[:n])
        for o in e.get("officers", []):
            if "--off" in sys.argv:
                print(f"  - {o['title'][:20]} {o['name']} {o['birth'][:4]} {'★' if o['founder_flag'] else ''} {o['career'][:250]}")
            else:
                print(f"  - {o['title'][:20]} {o['name']} {o['birth'][:4]} {'★' if o['founder_flag'] else ''}")


if __name__ == "__main__":
    main()
