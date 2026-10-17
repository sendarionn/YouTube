"""CiNii Research OpenSearch API で論文を検索する（https://support.nii.ac.jp/ja/cir/r_opensearch）

使い方: python cinii.py "検索語" [件数]
応答のJSONは cache/business-manners/cinii/ に保存する
"""
import hashlib
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request

import certifi

from paths import CACHE

CTX = ssl.create_default_context(cafile=certifi.where())


def search(q, count=30):
    query = urllib.parse.urlencode({"q": q, "count": count, "format": "json"})
    path = CACHE / "cinii" / (hashlib.sha1(query.encode()).hexdigest()[:16] + ".json")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"https://cir.nii.ac.jp/opensearch/all?{query}", timeout=60, context=CTX) as r:
            path.write_bytes(r.read())
        time.sleep(1)
    return json.loads(path.read_text())


if __name__ == "__main__":
    d = search(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 30)
    print("total", d.get("opensearch:totalResults"))
    for it in d.get("items", []):
        creators = "; ".join(c if isinstance(c, str) else str(c) for c in it.get("dc:creator", [])[:3])
        pub = it.get("prism:publicationName", "")
        print(it.get("prism:publicationDate", ""), "|", it.get("title"), "|", creators, "|", pub, "|", it.get("@id"))
