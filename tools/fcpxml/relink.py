"""FCPXML の素材パスを、project.fcpxml のある場所に合わせて書き換える

使い方：python -m tools.fcpxml.relink <出力ディレクトリ>/project.fcpxml
同じディレクトリの manifest.json にある files の相対パスを使う
"""
import json
import sys
from pathlib import Path

from . import relink, validate


def main():
    project = Path(sys.argv[1]).resolve()
    base = project.parent
    files = json.loads((base / "manifest.json").read_text(encoding="utf-8"))["files"]
    n = relink(project, base, list(files))
    print(f"{n} 件のパスを書き換えた")
    problems = validate(project)
    for p in problems:
        print(p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
