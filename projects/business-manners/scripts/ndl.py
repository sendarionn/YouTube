"""国立国会図書館サーチ OpenSearch API の検索

公式API（https://ndlsearch.ndl.go.jp/help/api/specifications）を使う
応答のXMLは cache/business-manners/ndl/ に保存し、同じ条件の再検索では保存済みを使う

使い方
  python ndl.py search title=ビジネスマナー from=1980 until=1985 [cnt=50]
"""
import hashlib
import ssl
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from paths import CACHE

API = "https://ndlsearch.ndl.go.jp/api/opensearch"
try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()
NS = {"openSearch": "http://a9.com/-/spec/opensearchrss/1.0/"}


def fetch(params):
    query = urllib.parse.urlencode(sorted(params.items()))
    path = CACHE / "ndl" / (hashlib.sha1(query.encode()).hexdigest()[:16] + ".xml")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(5):
            try:
                with urllib.request.urlopen(f"{API}?{query}", timeout=90, context=CTX) as r:
                    body = r.read()
                break
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(10 * (attempt + 1))
        path.write_bytes(body)
        (path.with_suffix(".query")).write_text(query)
        time.sleep(3)
    return ET.parse(path).getroot()


def total(root):
    e = root.find(".//openSearch:totalResults", NS)
    return int(e.text) if e is not None else 0


def items(root):
    for it in root.iter("item"):
        rec = {}
        for e in it:
            tag = e.tag.split("}")[-1]
            rec.setdefault(tag, []).append((e.text or "").strip())
        yield rec


if __name__ == "__main__":
    params = dict(a.split("=", 1) for a in sys.argv[2:])
    params.setdefault("cnt", "50")
    root = fetch(params)
    print("total", total(root))
    for r in items(root):
        print(r.get("issued", [""])[0], "|", r.get("title", [""])[0], "|", "; ".join(r.get("creator", [])), "|", "; ".join(r.get("publisher", [])), "|", r.get("link", [""])[0])
