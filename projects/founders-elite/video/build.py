"""動画の書き出し

使い方（リポジトリ直下の .venv の Python で実行）
  python build.py script   台本（narration.md）、字幕（captions.srt）、読みの確認表を書き出す
  python build.py frames   確認用の静止画を書き出す（各文の開始1.5秒後と場面の最後）
  python build.py render   MP4 を書き出す
出力先：INFOGRAPHIC_OUTPUT_DIR（既定 output/）/founders-elite/video/
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from scenes import build, load_numbers  # noqa: E402
from tools.infographic.canvas import Theme  # noqa: E402
from tools.infographic.config import OUTPUT  # noqa: E402
from tools.infographic.tts import OpenJTalk  # noqa: E402
from tools.infographic.video import build_timeline, frame_at, render, srt  # noqa: E402

OUT = OUTPUT / "founders-elite" / "video"
BACKEND = OpenJTalk(speed=1.1)
NAME = "founders_age_career"


def timeline():
    return build_timeline(build(load_numbers()), BACKEND)


def write_script(tl):
    import pyopenjtalk

    def ts(x):
        return f"{int(x // 60)}:{x % 60:04.1f}"

    md = ["# 最終ナレーション台本", "", f"尺：{ts(tl.duration)}（{tl.duration:.1f}秒）", "",
          "数値は `video/scenes.py` が集計ファイルから読み込んだ値", ""]
    yomi = ["# 読みの確認表（Open JTalk の読み）", ""]
    for sc, s0, st in zip(tl.scenes, tl.scene_starts, tl.scene_times):
        md += [f"## {sc.name}（{ts(s0)}〜{ts(s0 + st.duration)}）", ""]
        for ln, a in zip(sc.lines, st.starts):
            md.append(f"- {ts(s0 + a)} {ln.text}")
            yomi.append(f"- {ln.text}\n  - {pyopenjtalk.g2p(ln.say or ln.text, kana=True)}")
        md.append("")
    (HERE / "narration.md").write_text("\n".join(md), encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "yomi_check.md").write_text("\n".join(yomi), encoding="utf-8")
    (HERE / "captions.srt").write_text(srt(tl), encoding="utf-8")


def write_frames(tl, theme):
    d = OUT / "frames"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.png"):
        old.unlink()
    for k, (sc, s0, st) in enumerate(zip(tl.scenes, tl.scene_starts, tl.scene_times)):
        times = [a + 1.5 for a in st.starts] + [st.duration - 0.05]
        for j, t in enumerate(times):
            t = min(t, st.duration - 0.05)
            frame_at(tl, theme, s0 + t).save(d / f"{k:02}_{j:02}.png")
    print(d)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "script"
    tl = timeline()
    theme = Theme()
    write_script(tl)
    if cmd == "frames":
        write_frames(tl, theme)
    elif cmd == "render":
        out = render(tl, theme, OUT / f"{NAME}.mp4")
        print(out)
    print(f"尺 {tl.duration:.1f}秒")


if __name__ == "__main__":
    main()
