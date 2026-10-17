"""BGM の取得とミキシング

台帳（library/bgm/catalog.json）にある音源を取得し、ナレーションの下に敷く
- fetch：配布元（Wikimedia Commons など、自動取得が許可された場所）から取得し sha1 を照合する
- bed：複数の曲をクロスフェードでつなぎ、動画の長さに合わせる（足りなければ最初から繰り返す）
- duck：ナレーションの出ている間だけ BGM を下げる
"""
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from .config import REPO
from .tts import SAMPLE_RATE

LIBRARY = REPO / "library" / "bgm"


def catalog():
    return {t["id"]: t for t in json.loads((LIBRARY / "catalog.json").read_text(encoding="utf-8"))["tracks"]}


def fetch(track_id):
    t = catalog()[track_id]
    path = LIBRARY / t["file"]
    if path.exists() and hashlib.sha1(path.read_bytes()).hexdigest() == t["sha1"]:
        return path
    # Wikimedia は python-requests の既定の User-Agent を受け付けないため curl を使う
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    subprocess.run(["curl", "-sfL", "--retry", "3", "--retry-delay", "30", "-o", str(tmp), t["download_url"]], check=True)
    if hashlib.sha1(tmp.read_bytes()).hexdigest() != t["sha1"]:
        tmp.unlink()
        raise RuntimeError(f"{track_id}: sha1 が台帳と一致しません")
    tmp.rename(path)
    return path


def decode(path, ffmpeg=None):
    if ffmpeg is None:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def _trim(x, threshold=0.002):
    idx = np.where(np.abs(x) > threshold)[0]
    return x[idx[0]: idx[-1] + 1] if len(idx) else x


def bed(track_ids, duration, crossfade=4.0, fade_in=2.0, fade_out=5.0):
    """曲をつないで duration 秒の BGM を作る（曲間はクロスフェード、冒頭と末尾はフェード）"""
    n = int(duration * SAMPLE_RATE)
    cf = int(crossfade * SAMPLE_RATE)
    clips = [_trim(decode(fetch(t))) for t in track_ids]
    out = np.zeros(0, np.float32)
    k = 0
    while len(out) < n:
        c = clips[k % len(clips)].copy()
        if len(out) == 0:
            out = c
        else:
            ramp = np.linspace(0, 1, cf, dtype=np.float32)
            head = out[:-cf]
            mid = out[-cf:] * (1 - ramp) + c[:cf] * ramp
            out = np.concatenate([head, mid, c[cf:]])
        k += 1
    out = out[:n]
    fi, fo = int(fade_in * SAMPLE_RATE), int(fade_out * SAMPLE_RATE)
    out[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
    out[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)
    return out


def envelope(x, window=0.05, attack=0.08, release=0.6):
    """ナレーションの有無（0〜1）を滑らかに求める"""
    w = int(window * SAMPLE_RATE)
    frames = len(x) // w
    rms = np.sqrt((x[: frames * w].reshape(frames, w) ** 2).mean(1))
    on = (rms > 0.01).astype(np.float32)
    env = np.zeros_like(on)
    a, r = window / attack, window / release
    for i in range(1, len(on)):
        k = a if on[i] > env[i - 1] else r
        env[i] = env[i - 1] + (on[i] - env[i - 1]) * min(1.0, k)
    return np.repeat(env, w)[: len(x)] if len(env) else np.zeros_like(x)


def mix(voice, music, music_db=-22.0, duck_db=-8.0):
    """ナレーションに BGM を重ねる

    music_db：BGM のピークをこの値（dBFS）にそろえる。duck_db：ナレーション中にさらに下げる量
    """
    m = music[: len(voice)]
    if len(m) < len(voice):
        m = np.concatenate([m, np.zeros(len(voice) - len(m), np.float32)])
    peak = float(np.abs(m).max()) or 1.0
    m = m / peak * 10 ** (music_db / 20)
    env = envelope(voice)
    env = np.concatenate([env, np.full(len(voice) - len(env), env[-1] if len(env) else 0, np.float32)])
    gain = 10 ** ((duck_db * env) / 20)
    return (voice + m * gain).astype(np.float32)


def even(x, window=1.5, ratio=0.5, max_db=6.0):
    """曲の強弱の差を穏やかに縮める（長い窓の RMS に対して、中央値との差の ratio 分だけ補正。補正は ±max_db まで）"""
    f = int(0.05 * SAMPLE_RATE)
    n = len(x) // f
    if n < 2:
        return x
    rms = np.sqrt((x[: n * f].reshape(n, f) ** 2).mean(1)) + 1e-6
    k = max(1, int(window / 0.05))
    smooth = np.convolve(rms, np.ones(k) / k, mode="same")
    level = 20 * np.log10(smooth)
    target = np.median(level[level > level.max() - 40])
    gain_db = np.clip((target - level) * ratio, -max_db, max_db)
    g = 10 ** (np.interp(np.arange(len(x)), np.arange(n) * f + f / 2, gain_db) / 20)
    return (x * g).astype(np.float32)
