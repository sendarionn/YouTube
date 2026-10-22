"""音声合成

バックエンドを差し替えられるよう、synthesize(text) -> (np.ndarray[float32, -1..1], sample_rate) の形にそろえる
合成結果はテキストと設定のハッシュで cache に保存し、同じ文は再合成しない
"""
import hashlib
import json
import wave

import numpy as np

from .config import CACHE

SAMPLE_RATE = 48000


class OpenJTalk:
    """Open JTalk（pyopenjtalk）と HTS 音声 Mei（CC BY 3.0）"""

    credit = "音声合成：Open JTalk（HTS Voice \"Mei\" © Nagoya Institute of Technology, CC BY 3.0）"

    def __init__(self, speed=1.0, half_tone=0.0, gain=0.7):
        self.speed = speed
        self.half_tone = half_tone
        # pyopenjtalk の出力は16ビットの範囲を超えることがある（実測で最大約1.3倍）ため、合成直後に下げる
        self.gain = gain

    def key(self):
        return {"backend": "openjtalk-mei", "speed": self.speed, "half_tone": self.half_tone, "gain": self.gain}

    def synthesize(self, text):
        import pyopenjtalk

        x, sr = pyopenjtalk.tts(text, speed=self.speed, half_tone=self.half_tone)
        return (x / 32768.0 * self.gain).astype(np.float32), sr


def read_wav(path):
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32767
    return x, sr


def write_wav(path, x, sr=SAMPLE_RATE):
    y = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(y.tobytes())


def normalize_peak(x, peak_db=-1.0):
    """最大振幅を peak_db（dBFS）にそろえる"""
    m = float(np.abs(x).max()) if len(x) else 0.0
    return x if m == 0 else (x * (10 ** (peak_db / 20) / m)).astype(np.float32)


def trim_silence(x, threshold=0.004, keep=0.04, sr=SAMPLE_RATE):
    """前後の無音を詰める（前後に keep 秒だけ残す）"""
    idx = np.where(np.abs(x) > threshold)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(keep * sr))
    b = min(len(x), idx[-1] + int(keep * sr))
    return x[a:b]


def _resample(x, sr):
    if sr == SAMPLE_RATE:
        return x
    n = int(len(x) * SAMPLE_RATE / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def _cache_path(backend, payload, ext):
    h = hashlib.sha1(json.dumps([backend.key(), payload], ensure_ascii=False).encode()).hexdigest()[:16]
    return CACHE / "tts" / f"{h}.{ext}"


def speak(backend, text):
    """キャッシュ付きで合成し、SAMPLE_RATE の float32 配列を返す"""
    path = _cache_path(backend, text, "wav")
    if path.exists():
        return read_wav(path)[0]
    x, sr = backend.synthesize(text)
    x = _resample(x, sr)
    if getattr(backend, "trim", True):
        x = trim_silence(x)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_wav(path, x)
    return x


def speak_group(backend, texts):
    """複数の字幕行を1文として合成し、(音声, 各行の(開始秒, 終了秒)) を返す

    1文での合成に対応しないバックエンド、または境界を特定できない場合は None
    """
    if len(texts) < 2 or not hasattr(backend, "synthesize_marked"):
        return None
    path = _cache_path(backend, texts, "wav")
    meta = path.with_suffix(".json")
    if path.exists() and meta.exists():
        return read_wav(path)[0], [tuple(s) for s in json.loads(meta.read_text())]
    r = backend.synthesize_marked(texts)
    if r is None:
        return None
    x, sr, spans = r
    x = _resample(x, sr)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_wav(path, x)
    meta.write_text(json.dumps(spans))
    return x, spans


_DIGIT_KANA = dict(zip("0123456789", ["レイ", "イチ", "ニ", "サン", "ヨン", "ゴ", "ロク", "ナナ", "ハチ", "キュウ"]))


def normalize_numbers_ja(text):
    """数字の書き方を、読み上げで誤りにくい形にする（GPT-SoVITS の日本語の前処理は、桁区切り・小数点・% を読まないため）

    1,435 → 1435、33.6 → 33点ロク、0.62 → レイ点ロクニ、74% → 74パーセント
    """
    import re

    while re.search(r"(\d),(\d{3})(?!\d)", text):
        text = re.sub(r"(\d),(\d{3})(?!\d)", r"\1\2", text)

    def dec(m):
        whole = "レイ" if m.group(1) == "0" else m.group(1)
        return whole + "点" + "".join(_DIGIT_KANA[d] for d in m.group(2))

    text = re.sub(r"(\d+)\.(\d+)", dec, text)
    return re.sub(r"[%％]", "パーセント", text)


def _file_sha1(path, _memo={}):
    """大きなモデルファイルもあるため、同じパス・更新時刻・大きさなら計算を省く"""
    import os

    st = os.stat(path)
    k = (str(path), st.st_mtime_ns, st.st_size)
    if k not in _memo:
        h = hashlib.sha1()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _memo[k] = h.hexdigest()
    return _memo[k]


class GptSovits:
    """GPT-SoVITS（ローカルで起動した api_v2.py の HTTP API）。ユーザー自身の声

    参照音声（ref_audio）とその書き起こし（prompt_text）、重み（gpt_weights、sovits_weights）で声を指定する
    サーバーが読み込んでいる重みに頼らず、最初の合成の前に必ず読み込ませる（キャッシュの識別と実際の声を一致させるため）
    キャッシュの識別には、参照音声と重みのハッシュ、生成の設定を含める
    """

    def __init__(self, ref_audio, prompt_text, gpt_weights, sovits_weights, url=None, label="self",
                 speed=1.0, seed=1234, top_k=15, top_p=1.0, temperature=1.0, repetition_penalty=1.35,
                 text_split_method="cut5", fragment_interval=0.3, credit_name=None, retries=3, normalize=True):
        import os

        self.url = (url or os.environ.get("GPTSOVITS_URL", "http://127.0.0.1:9880")).rstrip("/")
        self.ref_audio = str(ref_audio)
        self.prompt_text = prompt_text
        self.gpt_weights = str(gpt_weights)
        self.sovits_weights = str(sovits_weights)
        self.label = label
        self.params = {"speed_factor": speed, "seed": seed, "top_k": top_k, "top_p": top_p, "temperature": temperature,
                       "repetition_penalty": repetition_penalty, "text_split_method": text_split_method,
                       "fragment_interval": fragment_interval, "batch_size": 1, "parallel_infer": False}
        self.credit = credit_name or "音声合成：GPT-SoVITS（話者本人の声で学習）"
        self.retries = retries
        self.normalize = normalize  # 数字の書き方の正規化（normalize_numbers_ja）
        self._weights_ready = False

    def key(self):
        return {"backend": "gpt-sovits", "label": self.label, "ref_audio_sha1": _file_sha1(self.ref_audio),
                "prompt_text": self.prompt_text,
                "gpt_weights_sha1": _file_sha1(self.gpt_weights), "sovits_weights_sha1": _file_sha1(self.sovits_weights),
                "normalize": self.normalize, **self.params}

    def _request(self, method, path, **kw):
        import time

        import requests

        for attempt in range(self.retries):
            try:
                r = requests.request(method, f"{self.url}{path}", timeout=600, **kw)
                if r.status_code == 200:
                    return r
                raise RuntimeError(f"GPT-SoVITS {path} が失敗しました（{r.status_code}）：{r.text[:300]}")
            except requests.ConnectionError:
                if attempt == self.retries - 1:
                    raise RuntimeError(f"GPT-SoVITS のサーバーに接続できません（{self.url}）。api_v2.py を起動してください")
                time.sleep(2 * (attempt + 1))

    def ensure_weights(self):
        if self._weights_ready:
            return
        self._request("GET", "/set_gpt_weights", params={"weights_path": self.gpt_weights})
        self._request("GET", "/set_sovits_weights", params={"weights_path": self.sovits_weights})
        self._weights_ready = True

    def synthesize(self, text):
        import io

        self.ensure_weights()
        if self.normalize:
            text = normalize_numbers_ja(text)
        body = {"text": text, "text_lang": "ja", "ref_audio_path": self.ref_audio, "prompt_text": self.prompt_text,
                "prompt_lang": "ja", "media_type": "wav", "streaming_mode": False, **self.params}
        r = self._request("POST", "/tts", json=body)
        with wave.open(io.BytesIO(r.content)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return x, sr

    def info(self):
        """build_info.json に記録する内容"""
        return {"engine": "GPT-SoVITS (api_v2)", **self.key(), "ref_audio": self.ref_audio,
                "gpt_weights": self.gpt_weights, "sovits_weights": self.sovits_weights}


class Voicevox:
    """VOICEVOX ENGINE（HTTP API）。起動中のエンジンに接続する

    複数の字幕行を1文として合成し、読点のポーズ位置から各行の時刻を返す（synthesize_marked）
    """

    PUNCT = "、。！？"

    def __init__(self, speaker=8, url=None, speed=1.0, pitch=0.0, intonation=1.0, volume=1.0,
                 pre=0.1, post=0.1, pause_scale=1.0, credit_name=None, words=()):
        import os

        self.url = (url or os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")).rstrip("/")
        self.speaker = speaker
        self.params = {"speedScale": speed, "pitchScale": pitch, "intonationScale": intonation,
                       "volumeScale": volume, "prePhonemeLength": pre, "postPhonemeLength": post,
                       "pauseLengthScale": pause_scale, "outputSamplingRate": SAMPLE_RATE, "outputStereo": False}
        self.credit = f"VOICEVOX:{credit_name}" if credit_name else "VOICEVOX"
        self.trim = False  # 前後の無音はパラメータで決めるため詰めない
        # 読みの修正（ユーザー辞書）：(表記, カタカナの読み, アクセント核の位置)
        self.words = [tuple(w) for w in words]
        self._words_ready = False

    def _post(self, path, params=None, json_body=None):
        import requests

        r = requests.post(f"{self.url}{path}", params=params, json=json_body, timeout=120)
        r.raise_for_status()
        return r

    def version(self):
        import requests

        return requests.get(f"{self.url}/version", timeout=10).json()

    def key(self):
        return {"backend": "voicevox", "speaker": self.speaker, **self.params, "words": self.words}

    def ensure_words(self):
        """ユーザー辞書に読みの修正を登録する（同じ表記があれば置き換える）"""
        import requests

        if self._words_ready:
            return
        cur = requests.get(f"{self.url}/user_dict", timeout=10).json()
        for surface, pron, acc in self.words:
            for uid, w in cur.items():
                if w.get("surface") in (surface, surface.translate(str.maketrans(
                        "".join(chr(c) for c in range(0x21, 0x7f)), "".join(chr(c + 0xFEE0) for c in range(0x21, 0x7f))))):
                    requests.delete(f"{self.url}/user_dict_word/{uid}", timeout=10)
            self._post("/user_dict_word", {"surface": surface, "pronunciation": pron, "accent_type": acc,
                                           "word_type": "PROPER_NOUN"})
        self._words_ready = True

    def query(self, text):
        self.ensure_words()
        q = self._post("/audio_query", {"text": text, "speaker": self.speaker}).json()
        q.update(self.params)
        return q

    def reading(self, text):
        """エンジンが読む内容（カタカナ、' はアクセント核、/ はアクセント句、、はポーズ）"""
        return self.query(text)["kana"]

    def _render(self, q):
        import io

        r = self._post("/synthesis", {"speaker": self.speaker}, q)
        with wave.open(io.BytesIO(r.content)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return x, sr

    def synthesize(self, text):
        return self._render(self.query(text))

    def synthesize_marked(self, texts):
        """texts をつなげて1文として合成し、各要素の (開始秒, 終了秒) を返す

        境界は各要素の末尾の句読点に対応するポーズ。句読点とポーズの数が合わない場合は None を返す
        """
        q = self.query("".join(texts))
        # アクセント句ごとの長さ（速度を掛ける前）と、ポーズの位置
        seq = [("pre", q["prePhonemeLength"])]
        for ap in q["accent_phrases"]:
            seq.append(("ap", sum((m.get("consonant_length") or 0) + m["vowel_length"] for m in ap["moras"])))
            if ap.get("pause_mora"):
                seq.append(("pause", ap["pause_mora"]["vowel_length"]))
        seq.append(("post", q["postPhonemeLength"]))
        total = sum(v for _, v in seq)
        pauses, t = [], 0.0
        for kind, v in seq:
            if kind == "pause":
                pauses.append((t, t + v))
            t += v
        # 各要素の末尾までに現れる句読点の数（最後の要素の末尾は数えない）
        ends, count = [], 0
        for s in texts[:-1]:
            count += sum(ch in self.PUNCT for ch in s)
            ends.append(count - 1)
        n_inner = sum(ch in self.PUNCT for ch in "".join(texts).rstrip(self.PUNCT))
        if len(pauses) != n_inner or any(e < 0 or e >= len(pauses) for e in ends):
            return None
        x, sr = self._render(q)
        dur = len(x) / sr
        scale = dur / total
        spans, start = [], q["prePhonemeLength"] * scale
        for e in ends:
            a, b = pauses[e]
            spans.append((start, a * scale))
            start = b * scale
        spans.append((start, dur - q["postPhonemeLength"] * scale))
        return x, sr, spans
