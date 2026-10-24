"""ナレーションの各文を書き起こし、台本と読み（カタカナ）を比べて読み間違いの候補を出す（ローカルだけで行う）

使い方（faster-whisper と pyopenjtalk のある GPT-SoVITS の環境で、リポジトリ直下から）
  models/gpt-sovits/.venv/bin/python projects/shinsho-labels/video/asr_lines.py
入力：output/shinsho-labels/video/lines.json（build.py script が書く。各文の音声のキャッシュのパス）
出力：output/shinsho-labels/video/asr.json と、読みの差が大きい文の一覧（標準出力）
- 書き起こしの誤りもあるため、差の大きい文は聴いて確かめる（tools/voice/asr_check.py と同じ比べ方）
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.infographic.config import OUTPUT  # noqa: E402
from tools.infographic.tts import normalize_numbers_ja  # noqa: E402
from tools.voice.asr_check import kana_error_rate  # noqa: E402

OUT = OUTPUT / "shinsho-labels" / "video"


def main():
    import librosa
    from faster_whisper import WhisperModel

    model = WhisperModel("medium", device="cpu", compute_type="int8")
    lines = json.loads((OUT / "lines.json").read_text(encoding="utf-8"))
    res = []
    for ln in lines:
        audio, _ = librosa.load(ln["wav"], sr=16000)  # ファイルを直接渡すと av の版の違いで読めないため配列で渡す
        segs, _ = model.transcribe(audio, language="ja", beam_size=5)
        hyp = "".join(s.text for s in segs)
        cer, a, b = kana_error_rate(normalize_numbers_ja(ln["say"]), hyp)
        res.append({**ln, "asr": hyp, "kana_error_rate": round(cer, 3)})
        print(f"{cer:.2f} {ln['say']}\n     {hyp}", flush=True)
    (OUT / "asr.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    bad = [r for r in res if r["kana_error_rate"] >= 0.1]
    print(f"\n差が 0.1 以上：{len(bad)}文 / {len(res)}文")
    for r in sorted(bad, key=lambda r: -r["kana_error_rate"]):
        print(f"{r['kana_error_rate']:.2f} [{r['scene']}] {r['say']}\n     → {r['asr']}")


if __name__ == "__main__":
    main()
