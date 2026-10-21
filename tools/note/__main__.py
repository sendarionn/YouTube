"""使い方（リポジトリ直下で実行）

  .venv/bin/python -m tools.note <slug> article   記事と図表だけを出力し直す（原稿を直した場合）
  .venv/bin/python -m tools.note <slug> package   配布資料と ZIP だけを作り直す
  .venv/bin/python -m tools.note <slug> check     品質確認と公開前チェックリスト
  .venv/bin/python -m tools.note <slug> all       上の3つを順に実行する

出力：INFOGRAPHIC_OUTPUT_DIR（既定 output/）/<slug>/note/
原稿：NOTE_PRIVATE_DIR（既定 private/）/<slug>/note/
動画の書き出しは実行しない
"""
import sys

from . import NoteError, load, run_article, run_check, run_package


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in ("article", "package", "check", "all"):
        print(__doc__)
        sys.exit(2)
    slug, cmd = sys.argv[1], sys.argv[2]
    try:
        p = load(slug)
        if cmd in ("article", "all"):
            run_article(p)
        if cmd in ("package", "all"):
            run_package(p)
        if cmd in ("check", "all"):
            results = run_check(p)
            for r in results:
                print(("OK  " if r["ok"] else "NG  ") + r["item"] + (f"：{r['detail']}" if not r["ok"] and r["detail"] else ""))
            print(p.out_dir / "publication-checklist.md")
            if not all(r["ok"] for r in results):
                sys.exit(1)
    except NoteError as e:
        print("エラー：", e)
        sys.exit(1)
    print(p.out_dir)


if __name__ == "__main__":
    main()
