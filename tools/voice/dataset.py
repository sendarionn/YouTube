"""録音を学習用の短い音声に分ける（話の切れ目の無音で区切る）

- 音量の調整は、全体に同じ倍率を掛けるだけにする（雑音除去・圧縮などの加工はしない）
- 区切りは無音の位置だけで決め、話の途中では切らない
- 書き起こしは別に行い、録音原稿と照合して直す（tools/voice/README.md）

使い方：.venv/bin/python -m tools.voice.dataset <録音> <出力ディレクトリ>
出力：clip-001.wav …（48kHz、16ビット、モノラル）と segments.json（元の録音での開始・終了秒、倍率）
"""
import json
import sys
from pathlib import Path

import numpy as np

from tools.infographic.tts import write_wav

from .check_recording import SR, db, decode

HOP = 0.02  # 音量を測る区間（秒）


def utterances(x, min_pause=0.3, margin_db=12.0):
    """話している区間 [(開始秒, 終了秒)]。無音が min_pause 秒以上続く位置で区切る"""
    n = int(SR * HOP)
    frames = x[: len(x) // n * n].reshape(-1, n).astype(np.float64)
    level = np.array([db(v) for v in np.sqrt((frames ** 2).mean(1))])
    on = level > np.percentile(level, 10) + margin_db
    segs, start, last = [], None, 0
    gap = int(round(min_pause / HOP))
    for i, v in enumerate(on):
        if v:
            if start is None:
                start = i
            last = i
        elif start is not None and i - last >= gap:
            segs.append((start * HOP, (last + 1) * HOP))
            start = None
    if start is not None:
        segs.append((start * HOP, (last + 1) * HOP))
    return [(a, b) for a, b in segs if b - a >= 0.1]  # 物音などの極端に短いものは除く


def group(segs, min_len=3.0, max_len=10.0, break_pause=0.6):
    """区間をつないで min_len〜max_len 秒の塊にする。長い無音（break_pause 秒以上）の位置を優先して区切る"""
    out, cur = [], []
    for k, (a, b) in enumerate(segs):
        if cur and b - cur[0][0] > max_len:
            out.append((cur[0][0], cur[-1][1]))
            cur = []
        cur.append((a, b))
        nxt = segs[k + 1][0] if k + 1 < len(segs) else None
        length = cur[-1][1] - cur[0][0]
        if length >= min_len and (nxt is None or nxt - b >= break_pause):
            out.append((cur[0][0], cur[-1][1]))
            cur = []
    if cur:
        if out and cur[-1][1] - out[-1][0] <= max_len:
            out[-1] = (out[-1][0], cur[-1][1])
        else:
            out.append((cur[0][0], cur[-1][1]))
    return out


def speech_gain(x, segs, target_db=-20.0, peak_limit_db=-3.0):
    """話している部分の RMS を target_db にする倍率（dB）。ピークが peak_limit_db を超えない範囲"""
    sp = np.concatenate([x[int(a * SR): int(b * SR)] for a, b in segs]).astype(np.float64)
    rms = db(np.sqrt((sp ** 2).mean()))
    return min(target_db - rms, peak_limit_db - db(np.abs(x).max()))


def export(path, out_dir, pad=0.15):
    x = decode(path)
    segs = utterances(x)
    chunks = group(segs)
    gain = speech_gain(x, segs)
    g = 10 ** (gain / 20)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta = {"source": Path(path).name, "gain_db": round(gain, 2), "sample_rate": SR, "clips": []}
    for k, (a, b) in enumerate(chunks, 1):
        s, e = max(0.0, a - pad), min(len(x) / SR, b + pad)
        name = f"clip-{k:03}.wav"
        write_wav(out / name, x[int(s * SR): int(e * SR)] * g, SR)
        meta["clips"].append({"file": name, "start": round(s, 2), "end": round(e, 2)})
    (out / "segments.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


if __name__ == "__main__":
    m = export(sys.argv[1], sys.argv[2])
    for c in m["clips"]:
        print(c["file"], c["start"], c["end"], round(c["end"] - c["start"], 2))
    print("gain", m["gain_db"], "dB")
