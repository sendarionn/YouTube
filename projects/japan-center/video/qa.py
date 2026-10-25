"""書き出し結果の品質確認（AGENTS.md「品質確認」の自動化できる項目）

- export.verify：final.mp4 とシーン映像のフレーム一致、尺、音声の長さ、FCPXML の DTD と素材
- 動き：final.mp4 を縮小して全フレームの差分を測り、急な変化（場面転換以外の跳び）と、動いている区間での停止（同じフレームの連続）を数える
- 音量：final.mp4 の統合ラウドネスとトゥルーピーク、ナレーション中と無音部の BGM との差
- 字幕：subtitles.srt の文が台本（scenes.py の Line.text）と同じ順で一致するか、FCPXML の字幕クリップの数
出力：output/japan-center/video/qa.json
"""
import json
import re
import subprocess
import sys
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from tools.infographic import export  # noqa: E402
from tools.infographic.config import OUTPUT  # noqa: E402

OUT = OUTPUT / "japan-center" / "video"


def frames_gray(path, w=192, h=108, fps=60):
    ff = export._ffmpeg()
    r = subprocess.run([ff, "-v", "error", "-i", str(path), "-vf", f"scale={w}:{h},format=gray", "-r", str(fps),
                        "-f", "rawvideo", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w).astype(np.float32)


def read_wav(p):
    with wave.open(str(p)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768, w.getframerate()


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


def main():
    m = json.loads((OUT / "manifest.json").read_text())
    rep = {"verify": export.verify(OUT)}

    # 動き
    f = frames_gray(OUT / "final.mp4", fps=m["fps"])
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    cuts = {s["start_frame"] for s in m["scenes"]}
    near_cut = np.zeros(len(d), bool)
    for c in cuts:
        near_cut[max(0, c - 40):c + 40] = True
    jumps = [(int(i + 1), round(float(v), 2)) for i, v in enumerate(d) if v > 6 and not near_cut[i]]
    # 動いている区間（前後のフレームが変化している）の中に、変化 0 のフレームが挟まる＝カクつき
    stutter = [int(i + 1) for i in range(1, len(d) - 1) if d[i] < 0.01 and d[i - 1] > 0.3 and d[i + 1] > 0.3]
    rep["motion"] = {"frames": int(len(f)), "max_diff_outside_cuts": round(float(d[~near_cut].max()), 2),
                     "jumps_over_6": jumps[:20], "n_jumps": len(jumps), "stutter_frames": stutter[:20],
                     "n_stutter": len(stutter), "moving_share": round(float((d > 0.05).mean()), 3)}

    # 音量
    ff = export._ffmpeg()
    r = subprocess.run([ff, "-hide_banner", "-nostats", "-i", str(OUT / "final.mp4"), "-af", "loudnorm=print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    ln = json.loads(re.search(r"\{[^{}]*\}", r.stderr)[0])
    rep["loudness"] = {"integrated_lufs": float(ln["input_i"]), "true_peak_dbtp": float(ln["input_tp"]), "lra": float(ln["input_lra"])}
    v, sr = read_wav(OUT / "audio" / "narration.wav")
    b, _ = read_wav(OUT / "audio" / "bgm.wav")
    win = sr // 10
    n = len(v) // win
    ve = np.sqrt((v[:n * win].reshape(n, win) ** 2).mean(1))
    be = np.sqrt((b[:n * win].reshape(n, win) ** 2).mean(1))
    speech = ve > 0.02
    silent = ve < 0.002
    rep["mix"] = {"speech_minus_bgm_db": round(float(rms_db(v[:n * win].reshape(n, win)[speech]) - rms_db(b[:n * win].reshape(n, win)[speech])), 1),
                  "bgm_in_silence_vs_speech_db": round(float(rms_db(b[:n * win].reshape(n, win)[silent]) - rms_db(v[:n * win].reshape(n, win)[speech])), 1),
                  "bgm_level_jump_max_db": round(float(np.abs(np.diff(20 * np.log10(be + 1e-6)))[be[1:] > 0.003].max()), 1)}

    # 字幕と台本
    sys.path.insert(0, str(HERE))
    srt = (OUT / "subtitles.srt").read_text(encoding="utf-8")
    cues = [blk.split("\n", 2)[2].strip() for blk in srt.strip().split("\n\n")]
    lines = [l["text"] for l in json.loads((OUT / "lines.json").read_text())]
    caps = ET.parse(OUT / "project.fcpxml").getroot().iter("caption")
    cap_text = [c.find("text/text-style").text for c in caps]
    rep["captions"] = {"srt_equals_script": cues == lines, "n": len(cues), "fcpxml_captions": len(cap_text),
                       "fcpxml_equals_srt": cap_text == cues}
    rep["ok"] = (rep["verify"]["ok"] and rep["motion"]["n_jumps"] == 0 and rep["captions"]["srt_equals_script"]
                 and rep["captions"]["fcpxml_equals_srt"])
    (OUT / "qa.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
