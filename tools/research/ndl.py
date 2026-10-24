"""国立国会図書館サーチ OpenSearch API（https://ndlsearch.ndl.go.jp/help/api/specifications）

- 応答の XML は INFOGRAPHIC_CACHE_DIR（既定 cache/）/ndl/ に保存し、同じ条件の再検索では保存済みを使う
- 問い合わせの間隔を空け、失敗したら待って再試行する（短時間に問い合わせると HTTP 429 になる）
- 利用条件：国立国会図書館作成の書誌データは利用目的を問わず自由に利用できる（CC BY 互換）。API を使ったことを明記する
"""
import hashlib
import ssl
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from tools.infographic.config import CACHE

API = "https://ndlsearch.ndl.go.jp/api/opensearch"
SRU = "https://ndlsearch.ndl.go.jp/api/sru"
CACHE_DIR = CACHE / "ndl"
INTERVAL = 3.0  # 問い合わせの間隔（秒）
NS = {"dc": "http://purl.org/dc/elements/1.1/", "dcndl": "http://ndl.go.jp/dcndl/terms/",
      "dcterms": "http://purl.org/dc/terms/", "openSearch": "http://a9.com/-/spec/opensearchrss/1.0/",
      "xsi": "http://www.w3.org/2001/XMLSchema-instance"}
XSI = "{http://www.w3.org/2001/XMLSchema-instance}type"

try:
    import certifi

    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()

_last = [0.0]


def cache_path(params):
    query = urllib.parse.urlencode(sorted(params.items()))
    return CACHE_DIR / (hashlib.sha1(query.encode()).hexdigest()[:16] + ".xml"), query


def fetch(params, offline=False, api=API):
    """検索結果の XML（ルート要素）。offline=True ではキャッシュだけを使い、なければ例外"""
    path, query = cache_path(params if api == API else {**params, "_api": "sru"})
    if api != API:
        query = urllib.parse.urlencode(sorted(params.items()))
    if not path.exists():
        if offline:
            raise FileNotFoundError(f"キャッシュにない：{query}")
        path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(6):
            wait = INTERVAL - (time.time() - _last[0])
            if wait > 0:
                time.sleep(wait)
            try:
                with urllib.request.urlopen(f"{api}?{query}", timeout=120, context=CTX) as r:
                    body = r.read()
                _last[0] = time.time()
                break
            except OSError:
                _last[0] = time.time()
                if attempt == 5:
                    raise
                time.sleep(15 * (attempt + 1))
        path.write_bytes(body)
        path.with_suffix(".query").write_text(query, encoding="utf-8")
    return ET.parse(path).getroot()


def total(root):
    e = root.find(".//openSearch:totalResults", NS)
    return int(e.text) if e is not None else 0


def parse_item(it):
    """1件の書誌を辞書にする（同じ要素が複数ある項目はリスト）"""
    def all_(tag):
        return [(e.text or "").strip() for e in it.findall(tag, NS)]

    ids, subjects = {}, {}
    for e in it.findall("dc:identifier", NS):
        ids.setdefault((e.get(XSI) or "").replace("dcndl:", ""), []).append((e.text or "").strip())
    for e in it.findall("dc:subject", NS):
        subjects.setdefault((e.get(XSI) or "").replace("dcndl:", "") or "keyword", []).append((e.text or "").strip())
    return {
        "link": (it.findtext("link") or "").strip(),
        "title": all_("dc:title"),
        "title_kana": all_("dcndl:titleTranscription"),
        "creator": all_("dc:creator"),
        "author": (it.findtext("author") or "").strip(),
        "series": all_("dcndl:seriesTitle"),
        "publisher": all_("dc:publisher"),
        "issued": all_("dcterms:issued"),
        "date": all_("dc:date"),
        "price": all_("dcndl:price"),
        "extent": all_("dc:extent"),
        "edition": all_("dcndl:edition"),
        "language": all_("dc:language"),
        "original_language": all_("dcndl:originalLanguage"),
        "description": all_("dc:description"),
        "category": [(e.text or "").strip() for e in it.findall("category")],
        "ids": ids,
        "subjects": subjects,
    }


LIMIT = 500  # 1回の検索で取得できる上限（501件目以降は idx を指定しても取得できない。仕様書 第1.5版）


class TooMany(Exception):
    pass


def search(params, offline=False):
    """条件に合う書誌をすべて返す。500件を超える場合は取りこぼすため TooMany を出す"""
    root = fetch({**params, "cnt": str(LIMIT)}, offline=offline)
    n = total(root)
    if n > LIMIT:
        raise TooMany(f"{n} 件（上限 {LIMIT}）：{params}")
    return [parse_item(it) for it in root.iter("item")]


def _days(y, m):
    import calendar

    return calendar.monthrange(y, m)[1]


def search_by_date(params, year_from, year_to, offline=False):
    """出版年で区切って検索し、500件を超える区間は年・月・日に分けて取りこぼしを防ぐ

    from・until は必ず年月日で指定する（until を「YYYY」だけにすると、その年の1月1日までと解釈される。
    例：岩波新書の from=2005&until=2005 は6件、from=2005-01-01&until=2005-12-31 は60件）
    戻り値：(書誌の一覧, 区間ごとの件数の記録)
    """
    out, log = [], []

    def count(fr, un):
        return total(fetch({**params, "from": fr, "until": un, "cnt": "1"}, offline=offline))

    def run(fr, un):
        try:
            items = search({**params, "from": fr, "until": un}, offline=offline)
        except TooMany:
            return False
        out.extend(items)
        log.append({"from": fr, "until": un, "records": len(items), "shortfall": 0})
        return True

    # まず区間全体で検索し、500件を超える場合だけ年に分ける
    if run(f"{year_from}-01-01", f"{year_to}-12-31"):
        return out, log
    for y in range(year_from, year_to + 1):
        if year_from == year_to or not run(f"{y}-01-01", f"{y}-12-31"):
            # 月に分ける。出版年だけで月のない書誌が月の検索に出ない場合に備え、年の件数との差を記録する
            n_year, before = count(f"{y}-01-01", f"{y}-12-31"), len(out)
            for m in range(1, 13):
                if run(f"{y}-{m:02}-01", f"{y}-{m:02}-{_days(y, m):02}"):
                    continue
                for d in range(1, _days(y, m) + 1):
                    if not run(f"{y}-{m:02}-{d:02}", f"{y}-{m:02}-{d:02}"):
                        raise TooMany(f"1日で500件を超える：{params} {y}-{m:02}-{d:02}")
            log.append({"from": str(y), "until": str(y), "records": len(out) - before,
                        "shortfall": max(0, n_year - (len(out) - before))})
    return out, log


def sru_extents(cql, n=50, offline=False):
    """SRU（DC-NDL 形式）で検索し、各書誌の (シリーズ名, 大きさの記述) を返す。OpenSearch の応答には大きさ（cm）がない"""
    root = fetch({"operation": "searchRetrieve", "version": "1.2", "recordSchema": "dcndl", "recordPacking": "xml",
                  "maximumRecords": str(n), "query": cql}, offline=offline, api=SRU)
    out = []
    for rec in root.iter("{http://www.loc.gov/zing/srw/}recordData"):
        series = [" ".join(t.strip() for t in e.itertext() if t.strip())
                  for e in rec.iter("{http://ndl.go.jp/dcndl/terms/}seriesTitle")]
        ext = [(e.text or "").strip() for e in rec.iter("{http://purl.org/dc/terms/}extent")]
        out.append((series, ext))
    return out
