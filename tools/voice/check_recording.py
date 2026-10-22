"""録音の品質確認（声のモデルを作る前に、ローカルだけで行う。外部には送らない）

使い方：.venv/bin/python -m tools.voice.check_recording <録音ファイル> [...]
WAV、M4A（ボイスメモ）、MP3 などを読める。結果を表示し、問題があれば終了コード1を返す

基準は ElevenLabs の録音の推奨（tools/voice/method-comparison.md）に合わせる
- 長さ：1〜3分（3分を超えても改善は小さい）
- 話している部分の RMS：−23〜−18dB、トゥルーピーク：−3dB 以下
- 雑音：話していない部分の音量（ノイズフロア）が低いこと、音割れ（クリップ）がないこと
"""
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field

import numpy as np

SR = 48000
FRAME = 0.05  # 音量を測る区間（秒）


def _ffmpeg():
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(path):
    """コーデック、サンプリングレート、チャンネル数、ビットレート"""
    err = subprocess.run([_ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Audio: ([^,\s]+).*?, (\d+) Hz, ([^,]+)(?:, [^,]+)?(?:, (\d+) kb/s)?", err)
    if not m:
        raise ValueError(f"音声として読めない：{path}")
    return {"codec": m.group(1), "sample_rate": int(m.group(2)), "channels": m.group(3).strip(),
            "kbps": int(m.group(4)) if m.group(4) else None}


def decode(path):
    out = subprocess.run([_ffmpeg(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32).copy()


def loudness(x):
    """(統合ラウドネス LUFS, トゥルーピーク dBTP)"""
    r = subprocess.run([_ffmpeg(), "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                       input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    d = json.loads(re.search(r"\{[^{}]*\}", r.stderr.decode())[0])
    return float(d["input_i"]), float(d["input_tp"])


def db(v):
    return float(20 * np.log10(max(float(v), 1e-10)))


@dataclass
class Report:
    path: str
    format: dict
    duration_sec: float
    speech_sec: float
    speech_rms_db: float
    noise_floor_db: float
    snr_db: float
    peak_db: float
    true_peak_db: float
    lufs: float
    clipped_samples: int
    longest_pause_sec: float
    ok: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def analyze(x, path="", fmt=None, measure_loudness=True):
    n = int(SR * FRAME)
    frames = x[: len(x) // n * n].reshape(-1, n)
    rms = np.sqrt((frames.astype(np.float64) ** 2).mean(1))
    rms_db = np.array([db(v) for v in rms])
    floor = float(np.percentile(rms_db, 10))
    speech = rms_db > max(floor + 15, -55)
    speech_rms = db(np.sqrt((frames[speech].astype(np.float64) ** 2).mean())) if speech.any() else -100.0
    # 話している区間の中の、最も長い無音
    idx = np.where(speech)[0]
    longest = 0.0
    if len(idx) > 1:
        longest = float(np.diff(idx).max() - 1) * FRAME
    lufs, tp = loudness(x) if measure_loudness else (float("nan"), db(np.abs(x).max()))
    clipped = int((np.abs(x) >= 0.999).sum())
    r = Report(str(path), fmt or {}, round(len(x) / SR, 2), round(float(speech.sum()) * FRAME, 2), round(speech_rms, 1),
               round(floor, 1), round(speech_rms - floor, 1), round(db(np.abs(x).max()), 1), round(tp, 1), round(lufs, 1),
               clipped, round(longest, 2))
    judge(r)
    return r


def judge(r):
    def put(level, msg):
        getattr(r, level).append(msg)

    if r.duration_sec < 60:
        put("warnings", f"短い（{r.duration_sec:.0f}秒）。1分以上を推奨")
    elif r.duration_sec > 180:
        put("warnings", f"長い（{r.duration_sec:.0f}秒）。3分を超えても改善は小さい")
    else:
        put("ok", f"長さ {r.duration_sec:.0f}秒")
    if r.clipped_samples:
        put("errors", f"音割れ（クリップ）が {r.clipped_samples} サンプル。マイクから少し離すか、入力音量を下げて録り直す")
    if r.true_peak_db > -1:
        put("warnings", f"ピークが大きい（{r.true_peak_db} dBTP）。−3dB 以下を推奨")
    if -23 <= r.speech_rms_db <= -18:
        put("ok", f"話している部分の音量 {r.speech_rms_db} dB")
    elif r.speech_rms_db < -30 or r.speech_rms_db > -12:
        put("errors", f"話している部分の音量が推奨（−23〜−18dB）から大きく外れる（{r.speech_rms_db} dB）")
    else:
        put("warnings", f"話している部分の音量が推奨（−23〜−18dB）から外れる（{r.speech_rms_db} dB）")
    if r.noise_floor_db > -50:
        put("errors", f"雑音が大きい（ノイズフロア {r.noise_floor_db} dB）。静かな場所で録り直す")
    elif r.noise_floor_db > -60:
        put("warnings", f"雑音がやや大きい（ノイズフロア {r.noise_floor_db} dB）")
    else:
        put("ok", f"ノイズフロア {r.noise_floor_db} dB")
    if r.longest_pause_sec > 2.5:
        put("warnings", f"話の途中に長い無音（最長 {r.longest_pause_sec} 秒）。言い直しの箇所なら、後で切り取る")
    codec = r.format.get("codec", "")
    if codec in ("aac", "mp3", "opus", "vorbis") and (r.format.get("kbps") or 0) < 128:
        put("warnings", f"圧縮の強い形式（{codec}、{r.format.get('kbps')} kb/s）。ボイスメモは設定で「ロスレス」にする")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    bad = False
    for path in sys.argv[1:]:
        r = analyze(decode(path), path, probe(path))
        print(f"\n{path}")
        for k, v in asdict(r).items():
            if k not in ("path", "ok", "warnings", "errors"):
                print(f"  {k}: {v}")
        for lvl, mark in (("ok", "OK"), ("warnings", "注意"), ("errors", "NG")):
            for msg in getattr(r, lvl):
                print(f"  [{mark}] {msg}")
        bad |= bool(r.errors)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
