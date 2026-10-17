"""台本（場面と文）から、音声・字幕・映像を組み立てて MP4 を書き出す

場面ごとに文（Line）を並べ、各文の音声の長さから時刻を決める
描画関数は場面内の時刻と各文の開始時刻（SceneTime）を受け取り、1フレームを描く
"""
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from .canvas import Canvas, Theme
from .tts import SAMPLE_RATE, normalize_peak, speak, speak_group, write_wav


@dataclass
class Line:
    text: str  # 字幕に出す文
    say: str | None = None  # 読み上げ用の文（読み間違いを避けるための言い換え）。省略時は text


@dataclass
class Scene:
    name: str
    lines: list
    draw: Callable
    lead: float = 0.6  # 場面の開始から最初の文までの間
    gap: float = 0.35  # 文と文の間
    tail: float = 1.2  # 最後の文の後、次の場面までの間（数値を読む時間）


@dataclass
class SceneTime:
    t: float  # 場面の開始からの秒
    starts: list  # 各文の開始秒（場面内）
    ends: list  # 各文の終了秒（場面内）
    duration: float

    def at(self, i):
        """i 番目の文の開始秒（負の値は末尾から数える）"""
        return self.starts[i]


@dataclass
class Timeline:
    scenes: list
    audio: np.ndarray
    scene_starts: list = field(default_factory=list)
    scene_times: list = field(default_factory=list)  # 各場面の SceneTime の雛形
    cues: list = field(default_factory=list)  # (開始, 終了, 字幕)

    @property
    def duration(self):
        return len(self.audio) / SAMPLE_RATE


def group_lines(lines):
    """末尾が読点（、）の行は次の行と同じ文として扱い、行番号をまとめる"""
    groups, cur = [], []
    for i, ln in enumerate(lines):
        cur.append(i)
        if not ln.text.rstrip().endswith("、"):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def build_timeline(scenes, backend):
    pieces, cues, starts, sts = [], [], [], []
    cursor = 0.0
    for sc in scenes:
        starts.append(cursor)
        local = sc.lead
        pieces.append(np.zeros(int(sc.lead * SAMPLE_RATE), np.float32))
        ls, le = [], []
        for grp in group_lines(sc.lines):
            texts = [sc.lines[i].say or sc.lines[i].text for i in grp]
            r = speak_group(backend, texts)
            if r is None:
                # 1文での合成に対応しない場合は行ごとに合成し、行間に gap を入れる
                parts = []
                for k, i in enumerate(grp):
                    x = speak(backend, texts[k])
                    if k:
                        parts.append(np.zeros(int(sc.gap * SAMPLE_RATE), np.float32))
                    off = sum(len(p) for p in parts) / SAMPLE_RATE
                    parts.append(x)
                    ls.append(local + off)
                    le.append(local + off + len(x) / SAMPLE_RATE)
                x = np.concatenate(parts)
            else:
                x, spans = r
                for a, b in spans:
                    ls.append(local + a)
                    le.append(local + b)
            pieces.append(x)
            local += len(x) / SAMPLE_RATE
            g = sc.gap if grp[-1] < len(sc.lines) - 1 else sc.tail
            pieces.append(np.zeros(int(g * SAMPLE_RATE), np.float32))
            local += g
        # 端数のずれを防ぐため、場面の長さはサンプル数から決める
        dur = sum(len(p) for p in pieces) / SAMPLE_RATE - cursor
        for s, e, ln in zip(ls, le, sc.lines):
            cues.append((cursor + s, cursor + e, ln.text))
        sts.append(SceneTime(0.0, ls, le, dur))
        cursor += dur
    audio = normalize_peak(np.concatenate(pieces))
    return Timeline(scenes, audio, starts, sts, cues)


def caption_at(tl, t):
    """時刻 t に表示する字幕。次の文が始まるまで直前の字幕を残す（ちらつき防止）"""
    cur = None
    for s, e, txt in tl.cues:
        if s <= t:
            cur = (s, e, txt)
        else:
            break
    if cur is None:
        return ""
    s, e, txt = cur
    return txt if t <= e + 0.8 else ""


def frame_at(tl, theme, t, captions=True):
    i = max(k for k, s in enumerate(tl.scene_starts) if s <= t + 1e-9)
    sc = tl.scenes[i]
    st0 = tl.scene_times[i]
    st = SceneTime(t - tl.scene_starts[i], st0.starts, st0.ends, st0.duration)
    cv = Canvas(theme)
    sc.draw(cv, st)
    if captions:
        cv.caption(caption_at(tl, t))
    return cv.img


def srt(tl):
    def ts(x):
        ms = int(round(x * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    out = []
    for k, (s, e, txt) in enumerate(tl.cues, 1):
        out.append(f"{k}\n{ts(s)} --> {ts(e + 0.3)}\n{txt}\n")
    return "\n".join(out)


def render(tl, theme, out_path, fps=30, ffmpeg=None, captions=True, crf=18, loudness="I=-16:TP=-1.5:LRA=11"):
    """全フレームを描いて ffmpeg に渡し、音声と合わせて MP4 にする"""
    if ffmpeg is None:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wav = out_path.with_suffix(".wav")
    write_wav(wav, tl.audio)
    n = int(np.ceil(tl.duration * fps))
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{theme.width}x{theme.height}", "-r", str(fps), "-i", "-", "-i", str(wav),
           "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
           *(["-af", f"loudnorm={loudness}", "-ar", str(SAMPLE_RATE)] if loudness else []),
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(out_path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(n):
        t = k / fps
        img = frame_at(tl, theme, t, captions)
        b = img.tobytes()
        p.stdin.write(b)
        if k % (fps * 20) == 0:
            print(f"  {t:6.1f}s / {tl.duration:.1f}s", flush=True)
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg が失敗しました")
    return out_path
