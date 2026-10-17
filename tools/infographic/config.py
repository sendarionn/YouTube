"""保存先とフォントの設定

パスはコードに直接書かず、環境変数で上書きできるようにする
- INFOGRAPHIC_OUTPUT_DIR：完成動画などの出力先（既定：リポジトリの output/）
- INFOGRAPHIC_CACHE_DIR：音声などの一時データ（既定：リポジトリの cache/）
- INFOGRAPHIC_FONT_DIRS：フォントを探すディレクトリ（os.pathsep 区切り）
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTPUT = Path(os.environ.get("INFOGRAPHIC_OUTPUT_DIR", REPO / "output"))
CACHE = Path(os.environ.get("INFOGRAPHIC_CACHE_DIR", REPO / "cache"))

_DEFAULT_FONT_DIRS = [Path.home() / "Library/Fonts", Path("/Library/Fonts"), Path("/usr/share/fonts")]
FONT_DIRS = [Path(p) for p in os.environ.get("INFOGRAPHIC_FONT_DIRS", "").split(os.pathsep) if p] or _DEFAULT_FONT_DIRS


def find_font(filename):
    for d in FONT_DIRS:
        for p in [d / filename, *d.rglob(filename)] if d.exists() else []:
            if p.exists():
                return p
    raise FileNotFoundError(f"フォント {filename} が見つかりません（INFOGRAPHIC_FONT_DIRS を設定してください）")
