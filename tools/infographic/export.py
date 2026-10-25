"""Final Cut Pro で後編集できる形の書き出し（AGENTS.md「Final Cut Pro 用の出力」）

out_dir/
  final.mp4  project.fcpxml  subtitles.srt  manifest.json
  scenes/scene-001.mov …（音声なし）
  audio/narration.wav  audio/bgm.wav  audio/effects.wav（使う場合のみ）

シーン i の映像は、場面転換の後半（新しい場面の描画が始まる時点）から、次の場面転換の前半（背景へのフェード）の終わりまで
こうすると各クリップの全フレームがそのシーンだけから描かれ、並べ替えや差し替えをしても前後のシーンが混ざらない
final.mp4 はシーン映像をそのままつないだもので、FCPXML のタイムラインと同じフレームになる
音声はナレーションと BGM を別のファイルにし、2本を足した音のラウドネスが目標値になる共通の倍率を掛ける
"""
import hashlib
import json
import math
import multiprocessing
import re
import subprocess
from datetime import date
from pathlib import Path

import numpy as np

from .. import fcpxml
from . import svgicons
from .tts import SAMPLE_RATE, write_wav
from .video import TRANSITION, frame_at, srt


def _ffmpeg():
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def scene_bounds(tl, fps):
    """各シーンの映像の境界（フレーム番号）。長さはシーン数 + 1"""
    n = int(math.ceil(tl.duration * fps - 1e-9))
    b = [0] + [int(math.ceil((s + TRANSITION / 2) * fps - 1e-9)) for s in tl.scene_starts[1:]] + [n]
    if any(x >= y for x, y in zip(b, b[1:])):
        raise ValueError("シーンの尺が場面転換より短い")
    return b


def check_audio_bounds(tl, bounds, fps):
    """ナレーションの文がシーンの境界をまたがないことを確かめる（またぐ場合はその文の一覧）"""
    bad = []
    for i, (s0, st) in enumerate(zip(tl.scene_starts, tl.scene_times)):
        a, b = bounds[i] / fps, bounds[i + 1] / fps
        for s, e in zip(st.starts, st.ends):
            if s0 + s < a or s0 + e > b:
                bad.append((i, s0 + s, s0 + e))
    return bad


def _fit(x, n):
    x = np.asarray(x, np.float32)[:n]
    return np.concatenate([x, np.zeros(n - len(x), np.float32)]) if len(x) < n else x


def measure_loudness(x, ffmpeg=None):
    """EBU R128 の統合ラウドネス（LUFS）とトゥルーピーク（dBTP）"""
    cmd = [ffmpeg or _ffmpeg(), "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(SAMPLE_RATE), "-ac", "1",
           "-i", "-", "-af", "loudnorm=print_format=json", "-f", "null", "-"]
    r = subprocess.run(cmd, input=np.asarray(x, np.float32).tobytes(), capture_output=True, check=True)
    d = json.loads(re.search(r"\{[^{}]*\}", r.stderr.decode())[0])
    return float(d["input_i"]), float(d["input_tp"])


def stem_gain(mixed, target_lufs=-16.0, true_peak=-1.5):
    """各音声に共通で掛ける倍率（dB）。足した音のラウドネスを目標値に、トゥルーピークを上限以下にする"""
    i, tp = measure_loudness(mixed)
    return min(target_lufs - i, true_peak - tp), {"input_lufs": i, "input_true_peak": tp}


def limit(x, ceiling_db, ffmpeg=None):
    """ピークを ceiling_db（dBFS）以下に抑える（先読みリミッター。遅延は補正し、長さは変えない）"""
    lim = max(0.0625, 10 ** (ceiling_db / 20))
    cmd = [ffmpeg or _ffmpeg(), "-v", "error", "-f", "f32le", "-ar", str(SAMPLE_RATE), "-ac", "1", "-i", "-",
           "-af", f"alimiter=limit={lim}:attack=5:release=80:level=false:latency=true",
           "-f", "f32le", "-ar", str(SAMPLE_RATE), "-ac", "1", "-"]
    r = subprocess.run(cmd, input=np.asarray(x, np.float32).tobytes(), capture_output=True, check=True)
    return _fit(np.frombuffer(r.stdout, np.float32), len(x))


VIDEO_ARGS = ["-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
              "-vf", "scale=out_color_matrix=bt709:out_range=tv",
              "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]


def render_clip(tl, theme, path, a, b, fps, crf=18, captions=False):
    """フレーム a〜b-1 を音声なしの動画にする"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".part" + path.suffix)
    cmd = [_ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{theme.width}x{theme.height}", "-r", str(fps), "-i", "-", *VIDEO_ARGS, "-crf", str(crf),
           "-movflags", "+faststart", str(tmp)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(a, b):
        p.stdin.write(frame_at(tl, theme, k / fps, captions).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg が失敗しました：{path}")
    tmp.rename(path)
    return path


_JOB = {}


def _render_job(args):
    i, path, a, b = args
    j = _JOB
    render_clip(j["tl"], j["theme"], Path(path), a, b, j["fps"], j["crf"], j["captions"])
    print(f"  {Path(path).name}（{(b - a) / j['fps']:.1f}秒）", flush=True)
    return i, set(svgicons.used)  # 子プロセスで描いた場合に、使ったアイコンの記録を親へ戻す


def _sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def shot_markers(tl, bounds, fps, i):
    """シーン i の実写候補の (クリップ内のフレーム, Shot)"""
    sc, s0, st = tl.scenes[i], tl.scene_starts[i], tl.scene_times[i]
    out = []
    for shot in sc.shots:
        t = s0 + (st.starts[shot.line] if st.starts else 0.0)
        out.append((max(0, int(round(t * fps)) - bounds[i]), shot))
    return out


def shot_list(tl, fps, title):
    """撮影リスト（shot-list.md）の本文"""
    bounds = scene_bounds(tl, fps)

    def ts(f):
        x = f / fps
        return f"{int(x // 60)}:{x % 60:04.1f}"

    md = [f"# 撮影リスト：{title}", "",
          "`video/scenes.py` の Shot から自動生成。撮影・挿入の状況は scenes.py の status を更新して再生成する",
          "挿入位置は FCPXML の To Do マーカー（実写：…）と同じ。撮影前は「仮素材」の図解で成立させる", ""]
    rows = []
    for i in range(len(tl.scenes)):
        for k, (f, shot) in enumerate(shot_markers(tl, bounds, fps, i), 1):
            sid = f"S{i + 1:03}"
            rows.append(f"| {sid}-{k} | {sid} {tl.scenes[i].name} | {ts(bounds[i] + f)} | {shot.seconds:g}秒 | "
                        f"{shot.subject} | {shot.purpose} | {shot.angle} | {shot.notes} | {shot.placeholder} | {shot.status} |")
    if not rows:
        return "\n".join(md + ["撮影候補なし", ""])
    md += ["| ID | シーン | 挿入位置 | 尺 | 撮影対象 | 目的 | アングル・構図 | 注意点 | 仮素材 | 状況 |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |", *rows, ""]
    return "\n".join(md)


def export(tl, theme, out_dir, name, music=None, effects=None, fps=60, crf=18, captions=False, only=None,
           workers=1, target_lufs=-16.0, true_peak=-1.5, info=None, fcpxml_captions=False):
    """シーン映像、分離した音声、final.mp4、FCPXML、字幕、manifest.json を書き出す

    music：ダッキング済みの BGM（bgm.ducked の結果）。effects：効果音（ナレーションと同じ時間軸）
    only：映像を描き直すシーン番号（1始まり）の集合。None なら全シーン。尺の変わったシーンと、ファイルのないシーンは常に描き直す
    info：manifest.json に加える情報（使った研究版、音声・BGM の設定など）
    fcpxml_captions：True でナレーションの字幕を FCPXML に字幕クリップ（SRT ロール）として入れる（subtitles.srt と同じ時刻）
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    bounds = scene_bounds(tl, fps)
    bad = check_audio_bounds(tl, bounds, fps)
    if bad:
        raise ValueError(f"ナレーションがシーンの境界をまたいでいる：{bad}")
    n_samples = bounds[-1] * SAMPLE_RATE // fps

    # 音声
    voice = _fit(tl.audio, n_samples)
    stems = {"narration": voice, "bgm": _fit(music, n_samples) if music is not None else None,
             "effects": _fit(effects, n_samples) if effects is not None else None}
    # ナレーションの瞬間的なピークで全体の音量が下がらないよう、目標のラウドネスに上げた後のナレーションだけを
    # リミッターで抑え、そのうえで共通の倍率を決める（各ファイルを足した音が final.mp4 の音声になる）
    total = sum(x for x in stems.values() if x is not None)
    up = 10 ** ((target_lufs - measure_loudness(total)[0]) / 20)
    stems = {k: (None if x is None else x * up) for k, x in stems.items()}
    stems["narration"] = limit(stems["narration"], true_peak - 1.0)
    total = sum(x for x in stems.values() if x is not None)
    gain_db, measured = stem_gain(total, target_lufs, true_peak)
    measured["pre_gain_db"] = round(20 * math.log10(up), 2)
    g = 10 ** (gain_db / 20)
    audio_paths = {}
    for kind, x in stems.items():
        if x is None:
            continue
        p = out / "audio" / f"{kind}.wav"
        p.parent.mkdir(exist_ok=True)
        write_wav(p, x * g)
        audio_paths[kind] = p
    mix_path = out / "audio" / ".mix.wav"
    write_wav(mix_path, total * g)

    # シーン映像
    prev = {}
    if (out / "manifest.json").exists():
        prev = {s["id"]: s for s in json.loads((out / "manifest.json").read_text(encoding="utf-8"))["scenes"]}
    jobs, scenes = [], []
    for i in range(len(tl.scenes)):
        sid = f"S{i + 1:03}"
        path = out / "scenes" / f"scene-{i + 1:03}.mov"
        a, b = bounds[i], bounds[i + 1]
        same = sid in prev and prev[sid]["start_frame"] == a and prev[sid]["frames"] == b - a
        if only is None or (i + 1) in only or not path.exists() or not same:
            jobs.append((i, str(path), a, b))
        markers = [fcpxml.Marker(0, f"{sid} {tl.scenes[i].name}")]
        for k, (f, shot) in enumerate(shot_markers(tl, bounds, fps, i), 1):
            markers.append(fcpxml.Marker(f, f"実写 {sid}-{k}：{shot.subject}", note=f"{shot.purpose}（{shot.seconds:g}秒）",
                                         todo=True, done=shot.status == "挿入済み"))
        scenes.append(fcpxml.SceneClip(sid, tl.scenes[i].name, path, b - a, markers))
    print(f"シーン映像 {len(jobs)}/{len(scenes)} 本を描く", flush=True)
    _JOB.update(tl=tl, theme=theme, fps=fps, crf=crf, captions=captions)
    if workers > 1 and len(jobs) > 1:
        # 描画関数はクロージャのため、fork で子プロセスに引き継ぐ
        with multiprocessing.get_context("fork").Pool(min(workers, len(jobs))) as pool:
            for _, used in pool.imap_unordered(_render_job, sorted(jobs, key=lambda j: j[2] - j[3])):
                svgicons.used.update(used)
    else:
        for j in jobs:
            _render_job(j)

    # final.mp4（シーン映像をそのままつなぐ）
    concat = out / "scenes" / ".concat.txt"
    concat.write_text("".join(f"file '{s.path.resolve()}'\n" for s in scenes), encoding="utf-8")
    final = out / "final.mp4"
    subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-i", str(mix_path), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(final)], check=True)
    concat.unlink()
    mix_path.unlink()

    (out / "subtitles.srt").write_text(srt(tl), encoding="utf-8")
    project = out / "project.fcpxml"
    caps = None
    if fcpxml_captions:
        # subtitles.srt と同じ時刻（終了は文の終わりの 0.3 秒後）。フレームに丸め、次の字幕と重ならないようにする
        caps = []
        cues = tl.cues
        for i, (s0, e0, txt) in enumerate(cues):
            a = int(round(s0 * fps))
            b = int(round((e0 + 0.3) * fps))
            if i + 1 < len(cues):
                b = min(b, int(round(cues[i + 1][0] * fps)))
            caps.append((a, min(b, bounds[-1]), txt))
    project.write_text(fcpxml.build(name, scenes, audio_paths, fps, theme.width, theme.height, SAMPLE_RATE, captions=caps),
                       encoding="utf-8")

    files = [final, project, out / "subtitles.srt", *(s.path for s in scenes), *audio_paths.values()]
    manifest = {
        "name": name,
        "exported": date.today().isoformat(),
        "fps": fps, "width": theme.width, "height": theme.height, "sample_rate": SAMPLE_RATE,
        "frames": bounds[-1], "duration_sec": round(bounds[-1] / fps, 3),
        "audio": {"stems": sorted(audio_paths), "gain_db": round(gain_db, 2), "target_lufs": target_lufs,
                  "true_peak_limit": true_peak, "measured_before_gain": measured,
                  "roles": {k: fcpxml.ROLES[k] for k in audio_paths}},
        "captions_on_screen": captions,
        "scenes": [{"id": s.id, "name": s.name, "file": s.path.relative_to(out).as_posix(),
                    "start_frame": bounds[i], "frames": s.frames,
                    "start_sec": round(bounds[i] / fps, 3), "duration_sec": round(s.frames / fps, 3),
                    "shots": [m.value for m in s.markers if m.todo]}
                   for i, s in enumerate(scenes)],
        "rendered_scenes": sorted(j[0] + 1 for j in jobs),
        "files": {p.relative_to(out).as_posix(): {"sha1": _sha1(p), "bytes": p.stat().st_size} for p in files},
        **(info or {}),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    problems = fcpxml.validate(project)
    for p in problems:
        print("  FCPXML:", p)
    return manifest, problems


def _framemd5(args):
    """映像ストリームのフレームごとの MD5 の一覧"""
    r = subprocess.run([_ffmpeg(), "-v", "error", *args, "-map", "0:v", "-f", "framemd5", "-"],
                       capture_output=True, text=True, check=True)
    return [line.rsplit(",", 1)[1].strip() for line in r.stdout.splitlines() if line and not line.startswith("#")]


def verify(out_dir):
    """書き出し結果の検証：final.mp4 とシーン映像をつないだものがフレーム単位で一致するか、尺、音声、FCPXML"""
    out = Path(out_dir)
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    report = {"fcpxml": fcpxml.validate(out / "project.fcpxml")}
    final = _framemd5(["-i", str(out / "final.mp4")])
    scenes = []
    for s in m["scenes"]:
        h = _framemd5(["-i", str(out / s["file"])])
        report.setdefault("scene_frames_mismatch", [])
        if len(h) != s["frames"]:
            report["scene_frames_mismatch"].append((s["id"], len(h), s["frames"]))
        scenes += h
    report["final_frames"] = len(final)
    report["expected_frames"] = m["frames"]
    report["final_equals_scenes"] = final == scenes
    report["missing_files"] = [f for f in m["files"] if not (out / f).exists()]
    for kind in m["audio"]["stems"]:
        with __import__("wave").open(str(out / "audio" / f"{kind}.wav")) as w:
            report[f"{kind}_samples_ok"] = w.getnframes() == m["frames"] * m["sample_rate"] // m["fps"]
    report["ok"] = (not report["fcpxml"] and not report["scene_frames_mismatch"] and report["final_equals_scenes"]
                    and report["final_frames"] == m["frames"] and not report["missing_files"]
                    and all(report[f"{k}_samples_ok"] for k in m["audio"]["stems"]))
    return report
