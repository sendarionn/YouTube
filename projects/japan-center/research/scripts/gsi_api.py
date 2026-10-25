"""国土地理院の住所検索・逆ジオコーダーの API（応答は cache/japan-center/gsi/ に保存）

- 住所検索：https://msearch.gsi.go.jp/address-search/AddressSearch?q=<住所>
  住所（町丁目・町名）の代表点を返す。建物や標石そのものの位置ではない
- 逆ジオコーダー：https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress?lat=&lon=
  市区町村コードと町字名を返す。海上など該当しない地点は空
"""
import hashlib
import json
import time

import requests

from geo import CACHE

DIR = CACHE / "gsi"


def _get(url, params):
    key = hashlib.sha1((url + json.dumps(params, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()
    path = DIR / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    DIR.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    d = r.json() if r.text.strip() else {}
    path.write_text(json.dumps(d, ensure_ascii=False))
    time.sleep(0.5)
    return d


def geocode(address):
    """住所の代表点（経度, 緯度, 一致した住所）。完全一致がなければ先頭の候補"""
    d = _get("https://msearch.gsi.go.jp/address-search/AddressSearch", {"q": address})
    if not d:
        return None
    exact = [f for f in d if f["properties"]["title"] == address]
    f = (exact or d)[0]
    lon, lat = f["geometry"]["coordinates"]
    return lon, lat, f["properties"]["title"]


def reverse(lon, lat):
    """(市区町村コード, 町字名)。該当しなければ (None, None)"""
    d = _get("https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress",
             {"lat": f"{lat:.6f}", "lon": f"{lon:.6f}"})
    res = d.get("results") if isinstance(d, dict) else None
    if not res:
        return None, None
    return res.get("muniCd"), res.get("lv01Nm")
