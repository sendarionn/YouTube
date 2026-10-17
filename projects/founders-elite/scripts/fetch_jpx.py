"""JPX新規上場会社一覧の取得と解析

2022年以降はJPXの現行ページ、2016〜2021年はWayback Machineに保存されたJPXのページを使う
出力: data/jpx_listings.csv（解析結果、除外判定前の全件）
"""
import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from paths import CACHE, DATA

JPX = "https://www.jpx.co.jp"
LIVE = {
    2025: f"{JPX}/listing/stocks/new/00-archives-01.html",
    2024: f"{JPX}/listing/stocks/new/00-archives-02.html",
    2023: f"{JPX}/listing/stocks/new/00-archives-03.html",
    2022: f"{JPX}/listing/stocks/new/00-archives-04.html",
}
# 年: (スナップショット時刻, アーカイブ番号) 取得時に選択中の年を検証する
WAYBACK = {
    2016: ("20170608051542", "01"),
    2017: ("20191115072111", "02"),
    2018: ("20190812144014", "01"),
    2019: ("20210923114500", "02"),
    2020: ("20240801005046", "04"),
    2021: ("20240614122807", "03"),
}
UA = {"User-Agent": "Mozilla/5.0 (research; founders-elite)"}


def wayback_url(ts, num):
    return f"https://web.archive.org/web/{ts}id_/{JPX}/listing/stocks/new/00-archives-{num}.html"


def fetch(url, dest: Path):
    if dest.exists():
        return dest.read_bytes()
    for attempt in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    time.sleep(1)
    return r.content


def selected_year(soup):
    opt = soup.select_one("select.backnumber option[selected]")
    return int(re.sub(r"\D", "", opt.text)) if opt else None


def norm_url(href):
    if not href:
        return ""
    href = re.sub(r"^https?://web\.archive\.org/web/\d+(id_)?/", "", href)
    if href.startswith("/"):
        href = JPX + href
    return href


def parse(html, year, source_url):
    soup = BeautifulSoup(html, "lxml")
    got = selected_year(soup)
    if got != year:
        raise ValueError(f"{source_url}: 選択年 {got} != {year}")
    rows = []
    trs = max(soup.find_all("table"), key=lambda t: len(t.find_all("tr"))).find_all("tr")
    i = 0
    while i < len(trs):
        tds = trs[i].find_all("td", recursive=False)
        first = tds[0].get_text(" ", strip=True) if tds else ""
        m = re.match(r"(\d{4}/\d{2}/\d{2})", first)
        if not m:
            i += 1
            continue
        nxt = trs[i + 1].find_all("td", recursive=False) if i + 1 < len(trs) else []
        name_td = tds[1]
        a = name_td.find("a")
        cell = name_td.get_text(" ", strip=True).replace("代表者インタビュー", "").strip()
        technical = bool(re.search(r"[*＊]", cell))
        name = re.sub(r"[*＊]|（注\d+）", "", (a.get_text(strip=True) if a else cell)).strip()
        new_shares = tds[6].get_text(" ", strip=True) if len(tds) > 6 else ""
        price = nxt[3].get_text(" ", strip=True) if len(nxt) > 3 else ""
        code = tds[2].get_text(" ", strip=True) if len(tds) > 2 else ""
        market = nxt[0].get_text(" ", strip=True) if nxt else ""
        links = {}
        for td in tds[3:] + nxt[1:]:
            for la in td.find_all("a"):
                h = norm_url(la.get("href"))
                if h.lower().endswith(".pdf"):
                    stem = Path(h).stem
                    if stem.lower().endswith(("-1s", "1s")) and "1ts" not in stem.lower():
                        links["part1_pdf"] = h
                    elif "outline" in stem.lower():
                        links["outline_pdf"] = h
        approval = re.search(r"（(\d{4}/\d{2}/\d{2})）", first)
        rows.append({
            "listing_year": year,
            "listing_date": m.group(1).replace("/", "-"),
            "approval_date": approval.group(1).replace("/", "-") if approval else "",
            "company_name": re.sub(r"\s+", " ", name),
            "code": code,
            "market": market,
            "technical_listing": int(technical),
            "new_shares_k": new_shares,
            "offer_price": price,
            "website": norm_url(a.get("href")) if a else "",
            "part1_pdf": links.get("part1_pdf", ""),
            "outline_pdf": links.get("outline_pdf", ""),
            "source_url": source_url,
        })
        i += 2 if nxt else 1
    return rows


def main():
    out = []
    for year, url in LIVE.items():
        html = fetch(url, CACHE / "jpx" / f"{year}.html")
        out += parse(html, year, url)
    for year, (ts, num) in WAYBACK.items():
        url = wayback_url(ts, num)
        html = fetch(url, CACHE / "wayback" / f"{year}_{ts}_{num}.html")
        out += parse(html, year, url)
    out.sort(key=lambda r: (r["listing_date"], r["code"]))
    DATA.mkdir(exist_ok=True)
    with open(DATA / "jpx_listings.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    by_year = {}
    for r in out:
        by_year[r["listing_year"]] = by_year.get(r["listing_year"], 0) + 1
    print(len(out), by_year)


if __name__ == "__main__":
    main()
