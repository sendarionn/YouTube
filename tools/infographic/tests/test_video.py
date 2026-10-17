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
