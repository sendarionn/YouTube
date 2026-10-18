import pytest

from tools.infographic import svgicons
from tools.infographic.canvas import Canvas, Theme


def test_svg_uses_given_color_and_stroke():
    s = svgicons.svg("book", "#2e6bd1", 1.5)
    assert 'stroke="#2e6bd1"' in s and 'stroke-width="1.5"' in s and "<path" in s


def test_unknown_icon_raises():
    with pytest.raises(KeyError):
        svgicons.svg("no-such-icon-name")


def test_draw_paints_inside_box_and_records_use():
    th = Theme()
    cv = Canvas(th, ss=1)
    svgicons.draw(cv, "user", 100, 100, 80, th.accent)
    img = cv.finish()
    box = img.crop((60, 60, 140, 140))
    assert any(px != th.bg for px in box.getdata())
    assert img.getpixel((300, 300)) == th.bg
    assert ("tabler-outline", "user") in svgicons.used


def test_draw_with_zero_alpha_draws_nothing():
    th = Theme()
    cv = Canvas(th, ss=1)
    svgicons.draw(cv, "book", 100, 100, 80, th.text, alpha=0)
    assert set(cv.finish().crop((60, 60, 140, 140)).getdata()) == {th.bg}
