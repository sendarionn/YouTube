"""Final Cut Pro 用のタイムライン（FCPXML）の生成と検証

シーンの映像クリップを基本ストーリーラインに並べ、ナレーションはシーンごとに区切って各クリップに接続する
BGM・効果音は先頭のクリップに接続した1本のクリップにする（シーンを並べ替えても音楽は動画全体に残る）
時刻はすべてフレーム数で受け取り、有理数の秒（例 "125/60s"）で書く
"""
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

VERSION = "1.13"
DTD_DIRS = [Path("/Applications/Final Cut Pro.app/Contents/Frameworks/Interchange.framework/Versions/A/Resources")]
ROLES = {"narration": "dialogue.Narration", "bgm": "music.BGM", "effects": "effects.SFX"}
LANES = {"narration": -1, "bgm": -2, "effects": -3}


@dataclass
class Marker:
    frame: int  # クリップの先頭からのフレーム数
    value: str
    note: str = ""
    todo: bool = False  # True で To Do マーカー
    done: bool = False  # To Do マーカーの完了


@dataclass
class SceneClip:
    id: str  # 例 "S001"
    name: str
    path: Path  # 映像ファイル（音声なし）
    frames: int
    markers: list = field(default_factory=list)


def rt(frames, fps):
    """フレーム数を FCPXML の時刻（有理数の秒）にする"""
    f = Fraction(frames, fps)
    return f"{f.numerator}s" if f.denominator == 1 else f"{f.numerator}/{f.denominator}s"


def file_url(path):
    return "file://" + quote(str(Path(path).resolve()))


def url_path(src):
    return Path(unquote(urlparse(src).path))


def build(name, scenes, audio, fps=60, width=1920, height=1080, sample_rate=48000, captions=None, caption_lang="ja"):
    """FCPXML の文字列を返す

    scenes：SceneClip の列（タイムラインの順）
    audio：{"narration": パス, "bgm": パス, "effects": パス}。各音声は動画全体と同じ長さで、モノラル
    captions：(開始フレーム, 終了フレーム, 文) の列（タイムラインの時刻）。指定すると、開始を含むシーンのクリップに
              字幕クリップ（SRT 形式のロール）として接続する。シーンを動かすと字幕も一緒に動く
    """
    if sample_rate % fps:
        raise ValueError("サンプリングレートがフレームレートで割り切れない（音声の区切りがフレームに合わない）")
    total = sum(s.frames for s in scenes)
    root = ET.Element("fcpxml", version=VERSION)
    res = ET.SubElement(root, "resources")
    ET.SubElement(res, "format", id="r0", name=f"FFVideoFormat{height}p{fps}", frameDuration=rt(1, fps),
                  width=str(width), height=str(height), colorSpace="1-1-1 (Rec. 709)")
    ids = {}

    def asset(key, path, frames, video):
        aid = f"r{len(ids) + 1}"
        ids[key] = aid
        attrs = {"id": aid, "name": Path(path).stem, "start": "0s", "duration": rt(frames, fps)}
        if video:
            attrs.update(hasVideo="1", format="r0", videoSources="1")
        else:
            attrs.update(hasAudio="1", audioSources="1", audioChannels="1", audioRate=str(sample_rate))
        a = ET.SubElement(res, "asset", attrs)
        ET.SubElement(a, "media-rep", kind="original-media", src=file_url(path))

    for s in scenes:
        asset(s.id, s.path, s.frames, True)
    for kind, path in audio.items():
        if path:
            asset(kind, path, total, False)

    event = ET.SubElement(root, "event", name=name)
    project = ET.SubElement(event, "project", name=name)
    seq = ET.SubElement(project, "sequence", format="r0", duration=rt(total, fps), tcStart="0s", tcFormat="NDF",
                        audioLayout="stereo", audioRate=f"{sample_rate // 1000}k")
    spine = ET.SubElement(seq, "spine")
    starts = []
    acc = 0
    for s in scenes:
        starts.append(acc)
        acc += s.frames
    by_scene = {}
    for a, b, text in captions or []:
        k = max(i for i, p in enumerate(starts) if p <= a)
        by_scene.setdefault(k, []).append((a - starts[k], b - a, text))
    n_style = 0
    pos = 0
    for k, s in enumerate(scenes):
        clip = ET.SubElement(spine, "asset-clip", ref=ids[s.id], offset=rt(pos, fps), name=f"{s.id} {s.name}",
                             start="0s", duration=rt(s.frames, fps), tcFormat="NDF")
        # 接続クリップ（anchor）はマーカーより前に置く（DTD の順序）
        if "narration" in ids:
            ET.SubElement(clip, "asset-clip", ref=ids["narration"], lane=str(LANES["narration"]), offset="0s",
                          name=f"{s.id} ナレーション", start=rt(pos, fps), duration=rt(s.frames, fps),
                          audioRole=ROLES["narration"])
        if k == 0:
            for kind in ("bgm", "effects"):
                if kind in ids:
                    ET.SubElement(clip, "asset-clip", ref=ids[kind], lane=str(LANES[kind]), offset="0s",
                                  name=Path(audio[kind]).stem, start="0s", duration=rt(total, fps),
                                  audioRole=ROLES[kind])
        for off, dur, text in by_scene.get(k, []):
            n_style += 1
            cap = ET.SubElement(clip, "caption", lane="1", offset=rt(off, fps), name=text[:40], start="0s",
                                duration=rt(max(1, dur), fps), role=f"SRT?captionFormat=SRT.{caption_lang}")
            t = ET.SubElement(cap, "text", placement="bottom")
            ET.SubElement(t, "text-style", ref=f"cap{n_style}").text = text
            d = ET.SubElement(cap, "text-style-def", id=f"cap{n_style}")
            ET.SubElement(d, "text-style", font=".SF NS Text", fontSize="13", fontFace="Regular",
                          fontColor="1 1 1 1", backgroundColor="0 0 0 1")
        for m in s.markers:
            attrs = {"start": rt(m.frame, fps), "duration": rt(1, fps), "value": m.value}
            if m.todo:
                attrs["completed"] = "1" if m.done else "0"
            if m.note:
                attrs["note"] = m.note
            ET.SubElement(clip, "marker", attrs)
        pos += s.frames
    ET.indent(root, "  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + ET.tostring(root, encoding="unicode") + "\n"


def find_dtd(version=VERSION):
    for d in DTD_DIRS:
        p = d / f"FCPXMLv{version.replace('.', '_')}.dtd"
        if p.exists():
            return p
    return None


def validate(path):
    """DTD による検証と、参照する素材の存在確認。問題の一覧を返す（空なら問題なし）

    DTD は Final Cut Pro のアプリに同梱されたものを使う。見つからない場合は検証できなかったことを返す
    """
    path = Path(path)
    problems = []
    dtd = find_dtd()
    if dtd is None or not shutil.which("xmllint"):
        problems.append("DTD 検証を実行できない（Final Cut Pro の DTD または xmllint が見つからない）")
    else:
        r = subprocess.run(["xmllint", "--noout", "--dtdvalid", file_url(dtd), str(path)], capture_output=True, text=True)
        if r.returncode != 0:
            problems.append("DTD 検証に失敗：" + r.stderr.strip())
    for rep in ET.parse(path).getroot().iter("media-rep"):
        p = url_path(rep.get("src"))
        if not p.exists():
            problems.append(f"素材が見つからない：{p}")
    return problems


def relink(path, base, rel_paths):
    """FCPXML の素材パスを base 以下に書き換える（別の Mac や別の場所へ移した場合）

    rel_paths：出力ディレクトリからの相対パスの一覧（manifest.json の files）。元のパスの末尾が一致するものに置き換える
    """
    path, base = Path(path), Path(base)
    text = path.read_text(encoding="utf-8")
    root = ET.parse(path).getroot()
    changed = 0
    for rep in root.iter("media-rep"):
        old = url_path(rep.get("src")).as_posix()
        for rel in sorted(rel_paths, key=len, reverse=True):
            if old.endswith("/" + rel):
                new = file_url(base / rel)
                if new != rep.get("src"):
                    text = text.replace(f'src="{rep.get("src")}"', f'src="{new}"')
                    changed += 1
                break
    path.write_text(text, encoding="utf-8")
    return changed
