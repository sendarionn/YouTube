"""評価用の文章を各方式で生成し、聴き比べのページを作る（ローカルだけで行い、外部に送らない）

使い方：.venv/bin/python -m tools.voice.evaluate [方式の名前 ...]
- 方式は VOICES に定義する（GPT-SoVITS のサーバー、VOICEVOX ENGINE を起動しておく）
- 出力：voices/self/eval/<方式>/<番号>.wav と voices/self/eval/index.html（Git 管理外）
- 合成は tools/infographic/tts.py の speak を使い、同じ文・同じ設定はキャッシュから読む
"""
import html
import json
import re
import sys
from pathlib import Path

from tools.infographic.config import REPO
from tools.infographic.tts import SAMPLE_RATE, GptSovits, Voicevox, speak, write_wav

EVAL_MD = REPO / "tools" / "voice" / "scripts" / "evaluation.md"
NARRATION = REPO / "projects" / "business-manners" / "video" / "narration.md"
VOICE_DIR = REPO / "voices" / "self"
OUT = VOICE_DIR / "eval"
DATASET = VOICE_DIR / "dataset" / "wav"
GPTSOVITS = REPO / "models" / "gpt-sovits"

# 参照音声（学習用の音声の1つ。3〜10秒）とその書き起こし
REF = DATASET / "clip-003.wav"
REF_TEXT = "この数字を見て、多くの人がそのくらいもらっている、と考えるのは自然なことです。"


def voices():
    """評価する方式（名前 → (説明, バックエンドを作る関数)）"""
    return {
        "zeroshot": ("学習なし（録音の一部を見本にするだけ）", lambda: GptSovits(
            REF, REF_TEXT, gpt_weights=GPTSOVITS / "GPT_SoVITS/pretrained_models/s1v3.ckpt",
            sovits_weights=GPTSOVITS / "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2ProPlus.pth", label="zeroshot")),
        "finetuned": ("声質と話し方の両方を学習", lambda: finetuned()),
        "hybrid": ("声質だけ学習、話し方は学習前のモデル（推奨候補）", lambda: finetuned(base_gpt=True)),
        "voicevox": ("VOICEVOX 春日部つむぎ（現在の標準）", lambda: Voicevox(
            speaker=8, credit_name="春日部つむぎ", speed=1.1, intonation=1.1, pre=0.1, post=0.15)),
    }


def finetuned(base_gpt=False):
    """追加学習した重みのうち、最新のもの。base_gpt=True では GPT（韻律）だけ事前学習のものを使う"""
    gpt = sorted((GPTSOVITS / "GPT_weights_v2ProPlus").glob("self-*.ckpt"))
    sovits = sorted((GPTSOVITS / "SoVITS_weights_v2ProPlus").glob("self_*.pth"))
    if not gpt or not sovits:
        raise FileNotFoundError("追加学習した重みがない（tools/voice/README.md「追加学習」）")
    if base_gpt:
        gpt = [GPTSOVITS / "GPT_SoVITS/pretrained_models/s1v3.ckpt"]
    return GptSovits(REF, REF_TEXT, gpt_weights=gpt[-1], sovits_weights=sovits[-1],
                     label="hybrid" if base_gpt else "finetuned")


def sentences():
    """評価用の文章 [(番号, 文)]。12 は business-manners の冒頭の場面"""
    items = []
    for line in EVAL_MD.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\d+a?)\. (?!`)(.+)$", line.strip())
        if m:
            items.append((m.group(1), m.group(2)))
    text = NARRATION.read_text(encoding="utf-8")
    sec = re.search(r"^## 冒頭.*?$(.*?)^## ", text, re.M | re.S).group(1)
    lines = [re.sub(r"^- \d+:\d+\.\d ", "", x) for x in sec.splitlines() if x.startswith("- ")]
    items.append(("12", "".join(lines)))
    return items


def generate(name, backend):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    for sid, text in sentences():
        path = d / f"{sid}.wav"
        x = speak(backend, text)
        write_wav(path, x, SAMPLE_RATE)
        print(f"  {name} {sid}（{len(x) / SAMPLE_RATE:.1f}秒）", flush=True)
    info = backend.info() if hasattr(backend, "info") else backend.key()
    (d / "settings.json").write_text(json.dumps(info, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def page():
    """聴き比べのページ（ローカルのファイルを参照する。公開しない）"""
    order = ["hybrid", "zeroshot", "finetuned", "voicevox"]
    names = [n for n in order if (OUT / n).exists()]
    desc = {n: voices()[n][0] for n in names}
    rows = []
    for sid, text in sentences():
        cells = "".join(f'<td><audio controls preload="none" src="{n}/{sid}.wav"></audio></td>'
                        if (OUT / n / f"{sid}.wav").exists() else "<td>－</td>" for n in names)
        rows.append(f"<tr><th>{sid}</th><td class=t>{html.escape(text)}</td>{cells}</tr>")
    head = "".join(f"<th>{html.escape(n)}<br><small>{html.escape(desc[n])}</small></th>" for n in names)
    ref = Path("..") / "dataset" / "wav" / REF.name
    doc = f"""<!doctype html><html lang="ja"><meta charset="utf-8"><title>声の聴き比べ</title>
<style>body{{font-family:sans-serif;margin:16px}} table{{border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:6px;vertical-align:top}}
.t{{max-width:420px;font-size:14px}} audio{{width:220px}}</style>
<h1>声の聴き比べ</h1>
<p>本人の録音（参照音声）：<audio controls src="{ref}"></audio>　評価表は tools/voice/scripts/evaluation.md</p>
<table><tr><th>番号</th><th>文章</th>{head}</tr>{''.join(rows)}</table></html>
"""
    (OUT / "index.html").write_text(doc, encoding="utf-8")
    return OUT / "index.html"


def main():
    targets = sys.argv[1:] or ["zeroshot", "voicevox"]
    for name in targets:
        desc, make = voices()[name]
        print(f"{name}：{desc}", flush=True)
        generate(name, make())
    print(page())


if __name__ == "__main__":
    main()
