"""録音の品質確認のテスト（合成した信号で行う）"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.infographic.tts import write_wav  # noqa: E402
from tools.voice import check_recording as cr  # noqa: E402

SR = cr.SR


def speech_like(sec, rms_db, noise_db, seed=0):
    """1秒話して0.3秒休む、を繰り返す信号（話している部分の RMS と雑音の大きさを指定する）"""
    rng = np.random.default_rng(seed)
    t = np.arange(int(sec * SR)) / SR
    on = (t % 1.3) < 1.0
    tone = np.sin(2 * np.pi * 180 * t) + 0.5 * np.sin(2 * np.pi * 360 * t)
    tone = tone / np.sqrt((tone ** 2).mean()) * 10 ** (rms_db / 20)
    noise = rng.normal(0, 10 ** (noise_db / 20), len(t))
    return (tone * on + noise).astype(np.float32)


def test_good_recording_passes(tmp_path):
    x = speech_like(90, -20, -70)
    p = tmp_path / "take.wav"
    write_wav(p, x)
    r = cr.analyze(cr.decode(p), p, cr.probe(p))
    assert not r.errors and not r.warnings, (r.errors, r.warnings)
    assert abs(r.speech_rms_db + 20) < 1.5
    assert r.noise_floor_db < -60 and r.format["sample_rate"] == SR


def test_short_noisy_quiet_recording_is_flagged():
    r = cr.analyze(speech_like(30, -32, -45), measure_loudness=False)
    text = " ".join(r.errors + r.warnings)
    assert "短い" in text and "雑音" in text and "音量" in text
    assert r.errors


def test_clipping_and_long_pause_are_flagged():
    x = speech_like(70, -20, -70)
    x[SR * 10: SR * 10 + 50] = 1.0
    x[SR * 30: SR * 34] = np.random.default_rng(1).normal(0, 10 ** (-70 / 20), SR * 4)
    r = cr.analyze(x, measure_loudness=False)
    assert any("音割れ" in e for e in r.errors)
    assert any("長い無音" in w for w in r.warnings)


def test_lossy_low_bitrate_is_warned():
    r = cr.analyze(speech_like(90, -20, -70), fmt={"codec": "aac", "kbps": 64}, measure_loudness=False)
    assert any("ロスレス" in w for w in r.warnings)
