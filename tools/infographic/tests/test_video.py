"""共通ツールのテスト（音声合成はダミーに差し替える）"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.infographic import tts  # noqa: E402
from tools.infographic.canvas import Canvas, Theme, ramp  # noqa: E402
from tools.infographic.video import Line, Scene, build_timeline, caption_at, srt  # noqa: E402


class Dummy:
    """文字数×0.1秒の音を返す"""

    def key(self):
        return {"backend": "dummy"}

    def synthesize(self, text):
        n = int(len(text) * 0.1 * tts.SAMPLE_RATE)
        return (np.sin(np.arange(n) / 10) * 2.0).astype(np.float32), tts.SAMPLE_RATE


def test_timeline_and_captions(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "CACHE", tmp_path)
    sc = [Scene("a", [Line("あいうえお"), Line("かきくけこさしす")], lambda cv, st: None, lead=1.0, gap=0.5, tail=1.0),
          Scene("b", [], lambda cv, st: None, lead=2.0, tail=0.0)]
    tl = build_timeline(sc, Dummy())
    st = tl.scene_times[0]
    assert abs(st.starts[0] - 1.0) < 0.01
    assert abs(st.starts[1] - (st.ends[0] + 0.5)) < 0.01
    assert abs(tl.scene_starts[1] - st.duration) < 1e-6
    assert abs(tl.duration - (st.duration + 2.0)) < 0.01
    # 音量はクリップしない（-1dBFS）
    assert np.abs(tl.audio).max() <= 10 ** (-1 / 20) + 1e-6
    assert caption_at(tl, 0.5) == ""
    assert caption_at(tl, st.starts[1] + 0.1) == "かきくけこさしす"
    assert "00:00:01,000 -->" in srt(tl)


def test_ramp():
    assert ramp(0.0, 1.0) == 0.0
    assert ramp(2.0, 1.0, 0.5) == 1.0
    assert 0 < ramp(1.2, 1.0, 0.5) < 1


def test_caption_too_long_raises():
    cv = Canvas(Theme())
    try:
        cv.caption("あ" * 200)
    except ValueError:
        return
    raise AssertionError("3行以上の字幕でエラーにならない")


class Marked(Dummy):
    """1文で合成し、各行の時刻を返すバックエンドのダミー"""

    def key(self):
        return {"backend": "marked"}

    def synthesize_marked(self, texts):
        x, sr = self.synthesize("".join(texts))
        spans, t = [], 0.0
        for s in texts:
            d = len(s) * 0.1
            spans.append((t, t + d - 0.05))
            t += d
        return x, sr, spans


def test_group_lines():
    from tools.infographic.video import group_lines

    ls = [Line("あ、"), Line("い。"), Line("う"), Line("え、"), Line("お、")]
    assert group_lines(ls) == [[0, 1], [2], [3, 4]]


def test_grouped_sentence_has_no_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "CACHE", tmp_path)
    sc = [Scene("a", [Line("あいう、"), Line("えおか。"), Line("きく")], lambda cv, st: None, lead=1.0, gap=0.5, tail=1.0)]
    tl = build_timeline(sc, Marked())
    st = tl.scene_times[0]
    # 1文目の2行はつながって合成され、間に gap は入らない
    assert abs(st.starts[1] - (1.0 + 0.4)) < 0.01
    # 次の文は gap の後
    assert abs(st.starts[2] - (1.0 + 0.8 + 0.5)) < 0.01
    # キャッシュから読んでも同じ
    tl2 = build_timeline(sc, Marked())
    assert tl2.scene_times[0].starts == st.starts


def test_supersampled_canvas_outputs_target_size():
    from tools.infographic.canvas import _scale

    assert _scale([(1, 2), (3, 4)], 3) == [(3, 6), (9, 12)]
    assert _scale((1, 2, 3, 4), 2) == (2, 4, 6, 8)
    cv = Canvas(Theme(), ss=3)
    cv.rect((10, 10, 100, 100), (0, 0, 0))
    img = cv.finish()
    assert img.size == (1920, 1080)
    assert img.getpixel((50, 50)) == (0, 0, 0)
    # 縁は中間色になる（アンチエイリアス）
    cv2 = Canvas(Theme(), ss=3)
    cv2.d.ellipse((100.3, 100.3, 300.3, 300.3), fill=(0, 0, 0))
    edge = [cv2.finish().getpixel((x, 130))[0] for x in range(100, 140)]  # 曲線の部分
    assert any(0 < v < 240 for v in edge)


def test_normalize_numbers_ja():
    from tools.infographic.tts import normalize_numbers_ja as n

    assert n("回答者は1,435人で、そのうち74%") == "回答者は1435人で、そのうち74パーセント"
    assert n("平均値は33.6歳") == "平均値は33点ロク歳"
    assert n("0.62％") == "レイ点ロクニパーセント"
    assert n("1,234,567円") == "1234567円"
    assert n("2008年に99点") == "2008年に99点"
