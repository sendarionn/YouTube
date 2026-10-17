"""BGM のミキシングのテスト（音源ファイルは使わない）"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.infographic import bgm  # noqa: E402
from tools.infographic.tts import SAMPLE_RATE as SR  # noqa: E402


def tone(sec, amp, f=440):
    t = np.arange(int(sec * SR)) / SR
    return (amp * np.sin(2 * np.pi * f * t)).astype(np.float32)


def db(x):
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)


def test_mix_ducks_music_under_voice():
    voice = np.concatenate([np.zeros(SR * 2, np.float32), tone(3, 0.3), np.zeros(SR * 3, np.float32)])
    music = tone(len(voice) / SR, 0.5, f=220)
    out = bgm.mix(voice, music, music_db=-13, duck_db=-8)
    m = out - voice
    during = m[int(3.0 * SR): int(4.5 * SR)]
    after = m[int(6.5 * SR): int(7.5 * SR)]
    assert len(out) == len(voice)
    assert db(after) - db(during) > 6  # ナレーション中は下がる
    assert np.abs(m).max() <= 10 ** (-13 / 20) + 1e-3


def test_even_reduces_level_differences():
    x = np.concatenate([tone(4, 0.05), tone(4, 0.5)])
    y = bgm.even(x, window=1.0, ratio=0.5, max_db=6)
    before = db(x[-SR * 2:]) - db(x[: SR * 2])
    after = db(y[-SR * 2:]) - db(y[: SR * 2])
    assert after < before


def test_catalog_has_license_fields():
    for t in bgm.catalog().values():
        for k in ("license", "license_url", "credit", "sha1", "download_url", "youtube_monetization"):
            assert t[k] not in (None, ""), (t["id"], k)
