"""保存先の解決

環境変数で上書きできる
- FOUNDERS_CACHE_DIR: ダウンロードした資料の保存先
- FOUNDERS_OUTPUT_DIR: グラフなど生成物の保存先
"""
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
DATA = PROJECT / "data"
CACHE = Path(os.environ.get("FOUNDERS_CACHE_DIR", REPO / "cache" / "founders-elite"))
OUTPUT = Path(os.environ.get("FOUNDERS_OUTPUT_DIR", REPO / "output" / "founders-elite"))
