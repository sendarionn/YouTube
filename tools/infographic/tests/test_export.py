"""Final Cut Pro 用の書き出しのテスト（音声合成はダミー、小さい画面で描く）"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools import fcpxml  # noqa: E402
from tools.infographic import export, tts  # noqa: E402
from tools.infographic.canvas import Theme  # noqa: E402
from tools.infographic.video import Line, Scene, Shot, build_timeline, frame_at  # noqa: E402
from tools.infographic.tests.test_video import Dummy  # noqa: E402

FPS = 30
COLORS = [(200, 30, 30), (30, 160, 60), (40, 60, 200)]


def painter(color):
    def draw(cv, st):
        cv.rect((40, 40, 280, 140), color)
    return draw


def timeline(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "CACHE", tmp_path / "cache")
    scenes = [Scene(f"場面{i}", [Line("あいうえお"), Line("かきくけ")], painter(c), lead=0.6, gap=0.3, tail=0.8)
              for i, c in enumerate(COLORS)]
    scenes[1].shots.append(Shot("本の実物", "書影の質感を見せる", line=1, seconds=2.5, placeholder="書影の図"))
    return build_timeline(scenes, Dummy())


def test_bounds_are_scene_only(tmp_path, monkeypatch):
    """各シーンの映像のフレームが、そのシーンだけから描かれる（前後のシーンの色が混ざらない）"""
    tl = timeline(tmp_path, monkeypatch)
    th = Theme(width=320, height=180)
    b = export.scene_bounds(tl, FPS)
    assert b[0] == 0 and b[-1] == int(np.ceil(tl.duration * FPS - 1e-9))
    assert not export.check_audio_bounds(tl, b, FPS)
    for i in range(3):
        for k in (b[i], b[i + 1] - 1):
            px = np.asarray(frame_at(tl, th, k / FPS, captions=False))[90, 160]
            others = [c for j, c in enumerate(COLORS) if j != i]
            # 別のシーンの色の成分が出ていない（背景色とそのシーンの色の間にある）
            for c in others:
                assert not np.allclose(px, c, atol=40)


def test_fcpxml_structure_and_dtd(tmp_path):
    for n in ("a.mov", "b.mov", "n.wav", "m.wav"):
        (tmp_path / n).write_bytes(b"")
    scenes = [fcpxml.SceneClip("S001", "冒頭", tmp_path / "a.mov", 90, [fcpxml.Marker(0, "S001 冒頭")]),
              fcpxml.SceneClip("S002", "本 & 棚", tmp_path / "b.mov", 45,
                               [fcpxml.Marker(10, "実写", note="書影", todo=True)])]
    text = fcpxml.build("テスト", scenes, {"narration": tmp_path / "n.wav", "bgm": tmp_path / "m.wav"}, fps=30)
    p = tmp_path / "project.fcpxml"
    p.write_text(text, encoding="utf-8")
    root = ET.parse(p).getroot()
    spine = root.find("./event/project/sequence/spine")
    clips = spine.findall("asset-clip")
    assert [c.get("offset") for c in clips] == ["0s", "3s"]
    assert clips[1].get("duration") == "3/2s"
    narr = clips[1].find("asset-clip")
    assert narr.get("start") == "3s" and narr.get("lane") == "-1" and narr.get("audioRole") == "dialogue.Narration"
    assert clips[0].findall("asset-clip")[1].get("audioRole") == "music.BGM"
    assert clips[1].find("marker").get("completed") == "0"
    assert root.find("./event/project/sequence").get("duration") == "9/2s"
    problems = fcpxml.validate(p)
    assert not [x for x in problems if "失敗" in x or "見つからない" in x], problems


def test_relink(tmp_path):
    a = tmp_path / "old" / "scenes" / "scene-001.mov"
    a.parent.mkdir(parents=True)
    a.write_bytes(b"")
    text = fcpxml.build("x", [fcpxml.SceneClip("S001", "a", a, 30)], {}, fps=30)
    p = tmp_path / "project.fcpxml"
    p.write_text(text, encoding="utf-8")
    new = tmp_path / "new"
    assert fcpxml.relink(p, new, ["scenes/scene-001.mov"]) == 1
    src = ET.parse(p).getroot().find(".//media-rep").get("src")
    assert fcpxml.url_path(src) == (new / "scenes" / "scene-001.mov").resolve()


def test_export_package(tmp_path, monkeypatch):
    tl = timeline(tmp_path, monkeypatch)
    th = Theme(width=320, height=180)
    music = (0.2 * np.sin(np.arange(len(tl.audio)) / 30)).astype(np.float32)
    out = tmp_path / "out"
    m, problems = export.export(tl, th, out, "テスト", music=music, fps=FPS, info={"research_version": "research-v1"})
    assert not [x for x in problems if "失敗" in x or "見つからない" in x], problems
    assert m["research_version"] == "research-v1"
    assert [s["file"] for s in m["scenes"]] == [f"scenes/scene-00{i}.mov" for i in (1, 2, 3)]
    assert m["scenes"][1]["shots"] and "本の実物" in m["scenes"][1]["shots"][0]
    r = export.verify(out)
    assert r["ok"], r
    # 音声は2本を足して目標のラウドネス付近（トゥルーピークの上限を優先する）
    n, _ = tts.read_wav(out / "audio" / "narration.wav")
    b, _ = tts.read_wav(out / "audio" / "bgm.wav")
    lufs, tp = export.measure_loudness(n + b)
    assert tp <= -1.0 and abs(lufs + 16) < 1.0
    # リミッターでナレーションの時刻がずれない（元の音声との相互相関の最大が遅れ0）
    ref = tl.audio[: len(n)]
    lags = range(-200, 201, 10)
    best = max(lags, key=lambda d: float(np.dot(np.roll(n[: len(ref)], d), ref)))
    assert best == 0
    # 1シーンだけ描き直しても他のシーンのファイルは変わらない
    before = json.loads((out / "manifest.json").read_text())["files"]
    m2, _ = export.export(tl, th, out, "テスト", music=music, fps=FPS, only={2})
    assert m2["rendered_scenes"] == [2]
    assert m2["files"]["scenes/scene-001.mov"] == before["scenes/scene-001.mov"]
    assert export.verify(out)["ok"]
    md = export.shot_list(tl, FPS, "テスト")
    assert "| S002-1 | S002 場面1 |" in md and "書影の図" in md
