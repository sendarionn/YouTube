"""使い方（リポジトリ直下で実行。バックアップ先は PRIVATE_BACKUP_DIR）

  .venv/bin/python -m tools.backup create [private|voices]  private/（既定）または voices/ をバックアップし、検証する
  .venv/bin/python -m tools.backup list                   バックアップの一覧と検証結果
  .venv/bin/python -m tools.backup verify <tar.gz>        1つのバックアップを検証する
  .venv/bin/python -m tools.backup restore <tar.gz> <空のディレクトリ>
                                                          指定した空のディレクトリに復元する（作業中のファイルは上書きしない）
"""
import sys

from . import SOURCES, BackupError, create, restore, snapshots, verify


def main():
    args = sys.argv[1:]
    try:
        if args[:1] == ["create"] and len(args) <= 2 and (len(args) == 1 or args[1] in SOURCES):
            archive, rec = create(SOURCES[args[1] if len(args) == 2 else "private"])
            print(f"{archive}（{len(rec['files'])} ファイル、検証済み）")
        elif args[:1] == ["list"]:
            for a in snapshots():
                problems = verify(a)
                print(("OK  " if not problems else "NG  ") + str(a) + ("" if not problems else "：" + "；".join(problems)))
        elif args[:1] == ["verify"] and len(args) == 2:
            problems = verify(args[1])
            print("\n".join(problems) or "OK")
            sys.exit(1 if problems else 0)
        elif args[:1] == ["restore"] and len(args) == 3:
            files = restore(args[1], args[2])
            print(f"{len(files)} ファイルを {args[2]} に復元し、記録と照合した")
        else:
            print(__doc__)
            sys.exit(2)
    except BackupError as e:
        print("エラー：", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
