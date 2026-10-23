"""ナレーションの声の選択（AGENTS.md「音声合成」）

声の定義は tools/voice/voices.json（Git 管理。音声ファイルとモデルは含まず、相対パスとハッシュだけ）
- narration(name)：声の名前からバックエンドを作る。省略時は環境変数 NARRATION_VOICE、なければ voices.json の default
- 本人の声（self）は、参照音声と重みのハッシュが承認時と一致することを確かめてから使う
"""
import json
import os

from .config import REPO
from .tts import GptSovits, Voicevox, _file_sha1

DEFINITIONS = REPO / "tools" / "voice" / "voices.json"


def definitions():
    return json.loads(DEFINITIONS.read_text(encoding="utf-8"))


def _checked(rel, sha1):
    path = REPO / rel
    if not path.exists():
        raise FileNotFoundError(f"声のファイルがない：{path}（tools/voice/README.md、バックアップから復元する）")
    if _file_sha1(path) != sha1:
        raise ValueError(f"声のファイルが承認時と違う：{path}")
    return path


def narration(name=None, words=()):
    """ナレーションのバックエンド。words は VOICEVOX の読みの修正（本人の声では使わない）"""
    d = definitions()
    name = name or os.environ.get("NARRATION_VOICE") or d["default"]
    v = d["voices"][name]
    if v["engine"] == "gpt-sovits":
        if not v.get("approved"):
            raise ValueError(f"声 {name} は承認されていない")
        p = v["params"]
        return GptSovits(_checked(v["ref_audio"], v["ref_audio_sha1"]), v["prompt_text"],
                         gpt_weights=_checked(v["gpt_weights"], v["gpt_weights_sha1"]),
                         sovits_weights=_checked(v["sovits_weights"], v["sovits_weights_sha1"]),
                         label=v["label"], speed=p["speed"], seed=p["seed"], top_k=p["top_k"], top_p=p["top_p"],
                         temperature=p["temperature"], repetition_penalty=p["repetition_penalty"],
                         text_split_method=p["text_split_method"], fragment_interval=p["fragment_interval"],
                         credit_name=v["credit"])
    if v["engine"] == "voicevox":
        p = v["params"]
        return Voicevox(speaker=v["speaker"], credit_name=v["credit_name"], speed=p["speed"],
                        intonation=p["intonation"], pre=p["pre"], post=p["post"], words=words)
    raise ValueError(f"未対応の声：{name}")
