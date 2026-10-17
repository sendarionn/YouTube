"""音声合成

バックエンドを差し替えられるよう、synthesize(text) -> (np.ndarray[float32, -1..1], sample_rate) の形にそろえる
合成結果はテキストと設定のハッシュで cache に保存し、同じ文は再合成しない
"""
import hashlib
import json
import wave

import numpy as np

from .config import CACHE

SAMPLE_RATE = 48000


class OpenJTalk:
    """Open JTalk（pyopenjtalk）と HTS 音声 Mei（CC BY 3.0）"""

    credit = "音声合成：Open JTalk（HTS Voice \"Mei\" © Nagoya Institute of Technology, CC BY 3.0）"

    def __init__(self, speed=1.0, half_tone=0.0, gain=0.7):
        self.speed = speed
        self.half_tone = half_tone
        # pyopenjtalk の出力は16ビットの範囲を超えることがある（実測で最大約1.3倍）ため、合成直後に下げる
        self.gain = gain

    def key(self):
        return {"backend": "openjtalk-mei", "speed": self.speed, "half_tone": self.half_tone, "gain": self.gain}

    def synthesize(self, text):
        import pyopenjtalk

        x, sr = pyopenjtalk.tts(text, speed=self.speed, half_tone=self.half_tone)
        return (x / 32768.0 * self.gain).astype(np.float32), sr


def read_wav(path):
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32767
    return x, sr


def write_wav(path, x, sr=SAMPLE_RATE):
    y = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(y.tobytes())


def normalize_peak(x, peak_db=-1.0):
    """最大振幅を peak_db（dBFS）にそろえる"""
    m = float(np.abs(x).max()) if len(x) else 0.0
    return x if m == 0 else (x * (10 ** (peak_db / 20) / m)).astype(np.float32)


def trim_silence(x, threshold=0.004, keep=0.04, sr=SAMPLE_RATE):
    """前後の無音を詰める（前後に keep 秒だけ残す）"""
    idx = np.where(np.abs(x) > threshold)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(keep * sr))
    b = min(len(x), idx[-1] + int(keep * sr))
    return x[a:b]


def speak(backend, text):
    """キャッシュ付きで合成し、SAMPLE_RATE の float32 配列を返す"""
    h = hashlib.sha1(json.dumps([backend.key(), text], ensure_ascii=False).encode()).hexdigest()[:16]
    path = CACHE / "tts" / f"{h}.wav"
    if path.exists():
        return read_wav(path)[0]
    x, sr = backend.synthesize(text)
    if sr != SAMPLE_RATE:
        n = int(len(x) * SAMPLE_RATE / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    x = trim_silence(x)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_wav(path, x)
    return x
