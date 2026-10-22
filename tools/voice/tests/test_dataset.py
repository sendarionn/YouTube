"""録音の分割のテスト"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.voice import dataset  # noqa: E402

SR = dataset.SR


def signal(parts, noise_db=-70):
    """parts：(秒, 話すか) の並び"""
    rng = np.random.default_rng(0)
    out = []
    for sec, on in parts:
        n = int(sec * SR)
        t = np.arange(n) / SR
        x = rng.normal(0, 10 ** (noise_db / 20), n)
        if on:
            x = x + 0.1 * np.sin(2 * np.pi * 200 * t)
        out.append(x)
    return np.concatenate(out).astype(np.float32)


def test_utterances_split_at_pauses():
    x = signal([(1, 0), (2, 1), (0.2, 0), (1, 1), (0.5, 0), (1.5, 1), (1, 0)])
    segs = dataset.utterances(x, min_pause=0.3)
    # 0.2秒の息継ぎではつながり、0.5秒の無音で分かれる
    assert len(segs) == 2
    assert abs(segs[0][0] - 1.0) < 0.05 and abs(segs[0][1] - 4.2) < 0.05
    assert abs(segs[1][0] - 4.7) < 0.05


def test_group_respects_lengths_and_breaks():
    segs = [(0, 1.5), (1.8, 3.5), (4.5, 6.0), (6.2, 9.0), (9.1, 12.0), (13.0, 14.0)]
    groups = dataset.group(segs, min_len=3, max_len=10, break_pause=0.6)
    assert groups[0] == (0, 3.5)  # 3秒を超え、次との間が0.6秒以上
    assert all(b - a <= 10 for a, b in groups)
    assert groups[-1][1] == 14.0  # 最後の短い区間は前につなぐ


def test_gain_is_uniform_and_peak_limited():
    x = signal([(1, 0), (3, 1), (1, 0)])
    segs = dataset.utterances(x)
    g = dataset.speech_gain(x, segs, target_db=-20, peak_limit_db=-3)
    assert g <= -3 - dataset.db(np.abs(x).max()) + 1e-9
