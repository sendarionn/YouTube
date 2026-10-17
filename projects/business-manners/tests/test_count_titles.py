import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import count_titles  # noqa: E402
from ndl import items, total  # noqa: E402

RSS = """<rss xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:openSearch="http://a9.com/-/spec/opensearchrss/1.0/"><channel>
<openSearch:totalResults>3</openSearch:totalResults>
<item><title>恥をかかないビジネス・マナー</title><link>L1</link><dcterms:issued>1982.3</dcterms:issued></item>
<item><title>ビジネスマナー常識集</title><link>L2</link><dcterms:issued>1984.1</dcterms:issued></item>
<item><title>ビジネス文書の書き方</title><link>L3</link><dcterms:issued>1983</dcterms:issued></item>
<item><title>ビジネスマナーの基本</title><link>L4</link><dcterms:issued>[199-]</dcterms:issued></item>
</channel></rss>"""


def test_normalize_removes_nakaguro_and_spaces():
    assert count_titles.normalize("恥をかかないビジネス・マナー") == "恥をかかないビジネスマナー"
    assert count_titles.normalize("ビジネス マナー") == "ビジネスマナー"


def test_count_range_counts_dotted_titles_and_skips_uncertain_years(monkeypatch):
    root = ET.fromstring(RSS)
    monkeypatch.setattr(count_titles, "fetch", lambda params: root)
    c = count_titles.count_range("ビジネスマナー", 1980, 1984)
    assert dict(c) == {1982: 1, 1984: 1}


def test_total_and_items_parse_rss():
    root = ET.fromstring(RSS)
    assert total(root) == 3
    assert [r["link"][0] for r in items(root)] == ["L1", "L2", "L3", "L4"]
