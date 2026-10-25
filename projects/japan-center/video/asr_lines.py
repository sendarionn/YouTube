"""ナレーションを文ごとに書き起こし、台本と読み（カタカナ）を比べて読み間違いの候補を出す（ローカルだけで行う）

使い方（faster-whisper と pyopenjtalk のある GPT-SoVITS の環境で、リポジトリ直下から）
  models/gpt-sovits/.venv/bin/python projects/japan-center/video/asr_lines.py
入力：output/japan-center/video/audio/narration.wav と subtitles.srt（文の時刻）、lines.json（読み上げ用の文）
出力：output/japan-center/video/asr.json と、読みの差が大きい文の一覧（標準出力）
- VOICEVOX は読点でつながる複数の行を1回で合成するため、行ごとのキャッシュではなく書き出した音声を時刻で切り出す
- 書き起こしの誤りもあるため、差の大きい文は聴いて確かめる（tools/voice/asr_check.py と同じ比べ方）
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.infographic.config import OUTPUT  # noqa: E402
from tools.infographic.tts import normalize_numbers_ja  # noqa: E402
from tools.voice.asr_check import kana_error_rate  # noqa: E402

OUT = OUTPUT / "japan-center" / "video"


def cues():
    def sec(t):
        h, m, s = t.replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    out = []
    for blk in (OUT / "subtitles.srt").read_text(encoding="utf-8").strip().split("\n\n"):
        _, ts, text = blk.split("\n", 2)
        a, b = ts.split(" --> ")
        out.append((sec(a), sec(b), text.strip()))
    return out


def main():
    import librosa
    from faster_whisper import WhisperModel

    model = WhisperModel("medium", device="cpu", compute_type="int8")
    audio, sr = librosa.load(str(OUT / "audio" / "narration.wav"), sr=16000)
    lines = json.loads((OUT / "lines.json").read_text(encoding="utf-8"))
    res = []
    for (a, b, text), ln in zip(cues(), lines):
        assert text == ln["text"]
        seg = audio[int(max(0, a - 0.1) * sr):int((b + 0.1) * sr)]
        segs, _ = model.transcribe(seg, language="ja", beam_size=5)
        hyp = "".join(s.text for s in segs)
        say = re.sub(r"[「」]", "", ln["say"])
        cer, *_ = kana_error_rate(normalize_numbers_ja(say), hyp)
        res.append({**ln, "asr": hyp, "kana_error_rate": round(cer, 3)})
        print(f"{cer:.2f} {ln['text']}\n     {hyp}", flush=True)
    (OUT / "asr.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    bad = [r for r in res if r["kana_error_rate"] >= 0.1]
    print(f"\n差が 0.1 以上：{len(bad)}文 / {len(res)}文")
    for r in sorted(bad, key=lambda r: -r["kana_error_rate"]):
        print(f"{r['kana_error_rate']:.2f} [{r['scene']}] {r['say']}\n     → {r['asr']}")


if __name__ == "__main__":
    main()
