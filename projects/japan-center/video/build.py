"""動画「日本の中心はどこ？」の書き出し（research-v1）

使い方（リポジトリ直下の .venv の Python で実行。VOICEVOX ENGINE を起動しておく：models/voicevox/engine_ditto/run）
  python build.py script   台本（narration.md）、字幕（captions.srt）、撮影リスト（shot-list.md）、読みの確認用の一覧を書き出す
  python build.py frames   確認用の静止画を書き出す（各文の開始1.5秒後と場面の最後）
  python build.py export [--only 3,5]
                           Final Cut Pro 用の一式（final.mp4、project.fcpxml、シーン映像、分離した音声、字幕、manifest.json）
出力先：INFOGRAPHIC_OUTPUT_DIR（既定 output/）/japan-center/video/
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE))

from scenes import build, load_numbers  # noqa: E402
from tools.infographic import bgm, export  # noqa: E402
from tools.infographic.canvas import SUPERSAMPLING, Theme  # noqa: E402
from tools.infographic.config import OUTPUT  # noqa: E402
from tools.infographic.tts import _cache_path  # noqa: E402
from tools.infographic.video import build_timeline, frame_at, srt  # noqa: E402
from tools.infographic.voices import narration  # noqa: E402

OUT = OUTPUT / "japan-center" / "video"
NAME = "japan_center_v1"
TITLE = "日本の中心はどこ？ あらゆる「中心」を集めてみた"
# 声：制作指示書（video/brief-video.md 8章）により VOICEVOX（春日部つむぎ）。progress.md「制作方針」
VOICE = os.environ.get("NARRATION_VOICE", "voicevox")
BACKEND = narration(VOICE)
# BGM（library/bgm/catalog.json）。静かなピアノの組曲を順に流す（動画が曲の合計より長い場合は1曲目に戻る）
MUSIC = ["macleod-gymnopedie-1", "macleod-gymnopedie-2", "macleod-gymnopedie-3"]
MUSIC_CREDIT = "Gymnopedie No. 1〜3（Erik Satie 作曲）Kevin MacLeod (incompetech.com) CC BY 3.0"
# ミックス：新書レーベル比較（shinsho-labels）で実測して決めた値（発話中約21dB・無音部約16dB 差）
MIX = {"music_db": -6.0, "duck_db": -10.0, "crossfade": 4.0, "fade_in": 2.0, "fade_out": 5.0}
CAPTIONS_ON_SCREEN = False
FPS = 60
RESEARCH_VERSION = "research-v1（2026-10-25。コミット f573f01 ＋ 追加検証。progress.md「研究版」）"
WORKERS = max(1, int(os.environ.get("WORKERS", (os.cpu_count() or 2) - 2)))


def timeline():
    return build_timeline(build(load_numbers(), BACKEND.credit, MUSIC_CREDIT), BACKEND)


def music_bed(tl):
    return bgm.even(bgm.bed(MUSIC, tl.duration, MIX["crossfade"], MIX["fade_in"], MIX["fade_out"]))


def write_build_info(tl):
    """再生成に必要な設定とバージョンを記録する（AGENTS.md「動画の再現性と生成物の管理」）"""
    import importlib.metadata as md
    import platform

    cat = bgm.catalog()
    info = {
        "duration_sec": round(tl.duration, 2),
        "research_version": RESEARCH_VERSION,
        "voice": BACKEND.info() if hasattr(BACKEND, "info") else {"engine": type(BACKEND).__name__,
                                                                  "version": BACKEND.version(), "speaker": BACKEND.speaker},
        "voice_name": VOICE,
        "voice_credit": BACKEND.credit,
        "music": [{"id": t, "title": cat[t]["title"], "sha1": cat[t]["sha1"], "license": cat[t]["license"]} for t in MUSIC],
        "mix": MIX,
        "captions_on_screen": CAPTIONS_ON_SCREEN,
        "fps": FPS,
        "supersampling": SUPERSAMPLING,
        "map_geometry": "cache/japan-center/video/geom.pkl（mapdraw.build_geometry で再生成）",
        "python": platform.python_version(),
        "packages": {p: md.version(p) for p in ("numpy", "pillow", "imageio-ffmpeg", "requests", "shapely", "pyproj")},
    }
    text = json.dumps(info, ensure_ascii=False, indent=1).replace(str(HERE.parents[2]) + "/", "")
    (HERE / "build_info.json").write_text(text, encoding="utf-8")


def write_script(tl):
    def ts(x):
        return f"{int(x // 60)}:{x % 60:04.1f}"

    md = ["# 最終ナレーション台本", "", f"尺：{ts(tl.duration)}（{tl.duration:.1f}秒）", "",
          f"研究版：{RESEARCH_VERSION}", "", f"声：{BACKEND.credit}（{VOICE}）", "",
          "数値は `video/scenes.py` が research/data/ から読み込んだ値。読み上げ用の言い換え（say）は括弧で示す", ""]
    lines = []
    for k, (sc, s0, st) in enumerate(zip(tl.scenes, tl.scene_starts, tl.scene_times), 1):
        md += [f"## {k}. {sc.name}（{ts(s0)}〜{ts(s0 + st.duration)}）", ""]
        for ln, a in zip(sc.lines, st.starts):
            md.append(f"- {ts(s0 + a)} {ln.text}")
            say = ln.say or ln.text
            lines.append({"scene": k, "start": round(s0 + a, 2), "text": ln.text, "say": say,
                          "reading": BACKEND.reading(say) if hasattr(BACKEND, "reading") else None,
                          "wav": str(_cache_path(BACKEND, say, "wav"))})
        md.append("")
    (HERE / "narration.md").write_text("\n".join(md), encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lines.json").write_text(json.dumps(lines, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "captions.srt").write_text(srt(tl), encoding="utf-8")
    (HERE / "shot-list.md").write_text(export.shot_list(tl, FPS, TITLE), encoding="utf-8")


def write_frames(tl, theme, only=None):
    d = OUT / "frames"
    d.mkdir(parents=True, exist_ok=True)
    for k, (sc, s0, st) in enumerate(zip(tl.scenes, tl.scene_starts, tl.scene_times)):
        if only and (k + 1) not in only:
            continue
        for old in d.glob(f"{k:02}_*.png"):
            old.unlink()
        times = [a + 1.5 for a in st.starts] + [st.duration - 0.05]
        for j, t in enumerate(times):
            t = min(t, st.duration - 0.05)
            frame_at(tl, theme, s0 + t, captions=CAPTIONS_ON_SCREEN).save(d / f"{k:02}_{j:02}.png")
    print(d)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "script"
    only = None
    if "--only" in sys.argv:
        only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
    tl = timeline()
    theme = Theme()
    write_script(tl)
    if cmd == "frames":
        write_frames(tl, theme, only)
    elif cmd == "export":
        music = bgm.ducked(tl.audio, music_bed(tl), MIX["music_db"], MIX["duck_db"])
        manifest, problems = export.export(
            tl, theme, OUT, "japan-center", music=music, fps=FPS, captions=CAPTIONS_ON_SCREEN, only=only,
            workers=WORKERS, fcpxml_captions=True, info={"title": TITLE, "research_version": RESEARCH_VERSION, "voice": BACKEND.credit,
                                   "build_info": "projects/japan-center/video/build_info.json"})
        write_build_info(tl)
        print(OUT / "project.fcpxml")
        if problems:
            sys.exit(1)
    print(f"尺 {tl.duration:.1f}秒")


if __name__ == "__main__":
    main()
