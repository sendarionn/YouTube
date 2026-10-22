"""生成した音声を書き起こし、元の文と読みを比べて、読み間違いの候補を見つける（ローカルだけで行う）

使い方（faster-whisper と pyopenjtalk のある GPT-SoVITS の環境で、リポジトリ直下から）
  models/gpt-sovits/.venv/bin/python -m tools.voice.asr_check voices/self/eval/zeroshot [...]
- 漢字と算用数字の書き方の違いで差が出ないよう、両方をカタカナの読みにしてから比べる
- 結果は各ディレクトリの asr.json と標準出力。差の大きい文は聴いて確かめる（書き起こしの誤りもある）
"""
import difflib
import json
import re
import sys
from pathlib import Path

from tools.voice.evaluate import sentences


def reading(text):
    import pyopenjtalk

    kana = pyopenjtalk.g2p(text, kana=True)
    return re.sub(r"[^ァ-ヴー]", "", kana)


def kana_error_rate(ref, hyp):
    """読み（カタカナ）の文字誤り率"""
    a, b = reading(ref), reading(hyp)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    edits = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
    return edits / max(1, len(a)), a, b


def main():
    import librosa
    from faster_whisper import WhisperModel

    model = WhisperModel("medium", device="cpu", compute_type="int8")
    texts = dict(sentences())
    for d in map(Path, sys.argv[1:]):
        out = {}
        for sid, text in texts.items():
            f = d / f"{sid}.wav"
            if not f.exists():
                continue
            x, _ = librosa.load(f, sr=16000, mono=True)
            segs, _ = model.transcribe(x, language="ja", beam_size=5)
            hyp = "".join(s.text for s in segs).strip()
            cer, a, b = kana_error_rate(text, hyp)
            out[sid] = {"text": text, "asr": hyp, "kana_cer": round(cer, 3)}
            print(f"{d.name} {sid:>3} {cer:5.1%}  {hyp}", flush=True)
        (d / "asr.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        mean = sum(v["kana_cer"] for v in out.values()) / max(1, len(out))
        print(f"{d.name} 平均 {mean:.1%}")


if __name__ == "__main__":
    main()
