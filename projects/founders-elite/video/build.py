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
from tools.infographic.tts import Voicevox  # noqa: E402
from tools.infographic.video import build_timeline, frame_at, group_lines, render, srt  # noqa: E402

OUT = OUTPUT / "founders-elite" / "video"
# VOICEVOX ENGINE を起動しておく（既定 http://127.0.0.1:50021、環境変数 VOICEVOX_URL で変更）
# 春日部つむぎ ノーマル（style id 8）。/speakers で確認済み
BACKEND = Voicevox(
    speaker=8, credit_name="春日部つむぎ",
    speed=1.1, intonation=1.1, pre=0.1, post=0.15,
    # 読みの修正：(表記, 読み, アクセント核の位置)。アクセントは辞書にない場合のエンジンの推定（語末）に合わせた
    words=[("東京証券取引所", "トウキョウショウケントリヒキジョ", 13)],
)
NAME = "founders_age_career"


def timeline():
    return build_timeline(build(load_numbers(), BACKEND.credit), BACKEND)


def write_script(tl):
    def ts(x):
        return f"{int(x // 60)}:{x % 60:04.1f}"

    md = ["# 最終ナレーション台本", "", f"尺：{ts(tl.duration)}（{tl.duration:.1f}秒）", "",
          "数値は `video/scenes.py` が集計ファイルから読み込んだ値", ""]
    yomi = [f"# 読みの確認表（{BACKEND.credit} の読み。' はアクセント核、/ はアクセント句、_ は無声化）", ""]
    for sc, s0, st in zip(tl.scenes, tl.scene_starts, tl.scene_times):
        md += [f"## {sc.name}（{ts(s0)}〜{ts(s0 + st.duration)}）", ""]
        for ln, a in zip(sc.lines, st.starts):
            md.append(f"- {ts(s0 + a)} {ln.text}")
        for g in group_lines(sc.lines):
            text = "".join(sc.lines[i].say or sc.lines[i].text for i in g)
            yomi.append(f"- {text}\n  - {BACKEND.reading(text)}")
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
