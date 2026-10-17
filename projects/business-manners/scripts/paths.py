"""保存先の解決

環境変数で上書きできる
- MANNERS_CACHE_DIR: ダウンロードした資料の保存先
"""
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
DATA = PROJECT / "data"
CACHE = Path(os.environ.get("MANNERS_CACHE_DIR", REPO / "cache" / "business-manners"))
