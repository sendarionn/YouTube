"""ナレーションの声の選択のテスト（一時ディレクトリの偽の声で行う）"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.infographic import tts, voices  # noqa: E402


def setup(tmp_path, monkeypatch, approved="2026-10-23", tamper=False):
    files = {"ref.wav": b"ref", "gpt.ckpt": b"gpt", "sovits.pth": b"sovits"}
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    sha = {n: hashlib.sha1(d).hexdigest() for n, d in files.items()}
    if tamper:
        (tmp_path / "sovits.pth").write_bytes(b"changed")
    d = {"default": "self", "voices": {
        "self": {"engine": "gpt-sovits", "approved": approved, "label": "hybrid",
                 "ref_audio": "ref.wav", "ref_audio_sha1": sha["ref.wav"], "prompt_text": "参照",
                 "gpt_weights": "gpt.ckpt", "gpt_weights_sha1": sha["gpt.ckpt"],
                 "sovits_weights": "sovits.pth", "sovits_weights_sha1": sha["sovits.pth"],
                 "params": {"speed": 1.0, "seed": 1, "top_k": 15, "top_p": 1.0, "temperature": 1.0,
                            "repetition_penalty": 1.35, "text_split_method": "cut5", "fragment_interval": 0.3},
                 "credit": "本人の声"},
        "voicevox": {"engine": "voicevox", "speaker": 8, "credit_name": "春日部つむぎ",
                     "params": {"speed": 1.1, "intonation": 1.1, "pre": 0.1, "post": 0.15}}}}
    path = tmp_path / "voices.json"
    path.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(voices, "REPO", tmp_path)
    monkeypatch.setattr(voices, "DEFINITIONS", path)
    monkeypatch.delenv("NARRATION_VOICE", raising=False)


def test_default_is_self_and_checks_hashes(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    b = voices.narration()
    assert isinstance(b, tts.GptSovits) and b.credit == "本人の声"
    assert b.key()["label"] == "hybrid" and b.key()["normalize"] is True


def test_switch_to_voicevox(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setenv("NARRATION_VOICE", "voicevox")
    b = voices.narration()
    assert isinstance(b, tts.Voicevox) and b.credit == "VOICEVOX:春日部つむぎ"


def test_changed_model_is_rejected(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, tamper=True)
    with pytest.raises(ValueError):
        voices.narration("self")


def test_unapproved_voice_is_rejected(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, approved=None)
    with pytest.raises(ValueError):
        voices.narration("self")


def test_repository_definition_is_valid():
    d = json.loads((Path(__file__).resolve().parents[2] / "voice" / "voices.json").read_text(encoding="utf-8"))
    assert d["default"] in d["voices"] and "voicevox" in d["voices"]
