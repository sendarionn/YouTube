"""完成動画の自動検証（AGENTS.md「品質確認」）

使い方：python qa.py [MP4のパス]
- 形式：コーデック、解像度、フレームレート、尺
- 音声：ラウドネス（EBU R128）、長い無音区間
- 映像：連続するフレームの差分。場面転換以外の急な変化（飛び・ちらつき）を検出する
結果は標準出力と qa_report.json（出力先の動画と同じ場所）に書く
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from tools.infographic.config import OUTPUT  # noqa: E402

W, H = 192, 108  # 差分は縮小して計算する


def ffmpeg():
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(path):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    info = r.stderr
    v = re.search(r"Video: (\w+).*?, (\d+)x(\d+).*?, ([\d.]+) fps", info)
    a = re.search(r"Audio: (\w+).*?, (\d+) Hz", info)
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    dur = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3))
    return {"video_codec": v.group(1), "width": int(v.group(2)), "height": int(v.group(3)), "fps": float(v.group(4)),
            "audio_codec": a.group(1), "sample_rate": int(a.group(2)), "duration_sec": round(dur, 2)}


def loudness(path):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = r.stderr[r.stderr.rfind("Summary:"):]
    get = lambda k: float(re.search(rf"{k}:\s+(-?[\d.]+)", s).group(1))  # noqa: E731
    return {"integrated_lufs": get("I"), "lra": get("LRA"), "true_peak_dbfs": get("Peak")}


def silences(path, noise_db=-45, min_sec=2.5):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af",
                        f"silencedetect=noise={noise_db}dB:d={min_sec}", "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return [(round(a, 2), round(b, 2)) for a, b in zip(starts, ends)]


def frame_diffs(path, fps):
    cmd = [ffmpeg(), "-v", "error", "-i", str(path), "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    prev, diffs = None, []
    n = W * H
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        f = np.frombuffer(b, np.uint8).astype(np.int16)
        if prev is not None:
            diffs.append(float(np.abs(f - prev).mean()))
        prev = f
    p.wait()
    return np.array(diffs)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT / "business-manners" / "video" / "business_manners.mp4"
    rep = {"file": str(path), "format": probe(path)}
    rep["loudness"] = loudness(path)
    rep["silences_over_2_5s"] = silences(path)
    d = frame_diffs(path, rep["format"]["fps"])
    fps = rep["format"]["fps"]
    # 1フレームで画面の平均輝度が大きく変わる箇所（クロスフェードは数フレームに分散するので小さい）
    thr = 6.0
    jumps = [(round((i + 1) / fps, 3), round(v, 2)) for i, v in enumerate(d) if v > thr]
    rep["frames"] = len(d) + 1
    rep["frame_diff"] = {"mean": round(float(d.mean()), 3), "p99": round(float(np.percentile(d, 99)), 3),
                         "max": round(float(d.max()), 3), "threshold": thr, "jumps": jumps}
    out = path.with_name("qa_report.json")
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
