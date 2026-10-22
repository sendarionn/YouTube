# tools/voice

ユーザー自身の声を基にした合成音声を、動画の標準ナレーションにするための準備
方式の比較と推奨は [method-comparison.md](method-comparison.md)。承認されるまでは標準の音声を VOICEVOX から変えない

| ファイル | 内容 |
| --- | --- |
| `method-comparison.md` | 方式の比較、費用、規約、この Mac で使えるか |
| `scripts/recording.md` | 録音原稿（約1分半〜2分） |
| `scripts/evaluation.md` | 評価用の文章（録音に含まれない）と評価表 |
| `check_recording.py` | 録音の品質確認（ローカルで行い、外部に送らない） |

## 録音

### 用意するもの

- iPhone 15 Pro の「ボイスメモ」（推奨）、または Mac の QuickTime Player（ファイル > 新規オーディオ収録）
  - ボイスメモは、iPhone の「設定 > アプリ > ボイスメモ > 音質」を「ロスレス」にしてから録る（既定の「圧縮」のままだと音質が落ちる）
  - 外付けのマイクはないため、内蔵マイクで録る。マイクの性能より、部屋の静かさと距離を一定に保つことのほうが効く
- 静かな部屋。カーテン・布団・服などの布が多い場所は反響が少ない（浴室や何もない部屋は響く）

### 録り方

1. エアコン・換気扇・冷蔵庫の音、窓の外の音ができるだけ小さい時間と場所を選ぶ
2. iPhone を机に置き、口から20cm ほど（握りこぶし2つ分）離し、正面から少し横にずらす（息が直接当たらないように）。録音の間、距離を変えない
3. 録音を始めて、5秒ほど黙ってから読み始める（雑音の確認に使う）
4. `scripts/recording.md` を、普段人に説明するときの口調で読む
   - 演技したり、抑揚をつけすぎたりしない。早口にもしない
   - 言い間違えたら、2秒ほど黙ってから、その文の頭から読み直す
5. 読み終えたら、3秒ほど黙ってから止める
6. 雑音除去・音量の補正・エフェクトはかけない（ボイスメモの「録音を強調」もオフ）

### 保存

- iPhone から AirDrop などで Mac に送り、`voices/self/raw/` に保存する。ファイル名は `YYYYMMDD-take01.m4a` のように日付と番号にする
- `voices/` は Git 管理外。公開リポジトリには入れない
- 保存したら、リポジトリ直下で品質を確認する

  ```sh
  .venv/bin/python -m tools.voice.check_recording voices/self/raw/20261022-take01.m4a
  ```

  - 長さ、話している部分の音量（−23〜−18dB を推奨）、ピーク、雑音、音割れ、長い無音を表示する
  - 「NG」が出たら録り直す。「注意」は内容を見て判断する（言い直しの無音は後で切り取る）
- 確認できたらバックアップする（バックアップ先は `.env` の `PRIVATE_BACKUP_DIR`）

  ```sh
  .venv/bin/python -m tools.backup create voices
  ```

## GPT-SoVITS（ローカル）

外部に送信せず、この Mac だけで学習・合成する。`models/gpt-sovits/`（Git 管理外）に置き、再現に必要なものは `tools/voice/gptsovits/` に残す

| ファイル | 内容 |
| --- | --- |
| `gptsovits/COMMIT` | 使った GPT-SoVITS のコミット |
| `gptsovits/local.patch` | ローカルの変更（macOS でデータ読み込みの worker が止まるため、0 にできるようにした） |
| `gptsovits/requirements-lock.txt` | 導入したパッケージの版 |
| `gptsovits/prepare.sh`、`gptsovits/train.py` | 前処理と追加学習（WebUI と同じ設定を CPU で実行） |
| `gptsovits/self.yaml` | API サーバーの設定 |

### 導入（初回だけ）

1. `git clone https://github.com/RVC-Boss/GPT-SoVITS.git models/gpt-sovits` し、`git checkout $(cat tools/voice/gptsovits/COMMIT)`、`git apply tools/voice/gptsovits/local.patch`
2. `models/gpt-sovits` で Python 3.12 の venv を作り、`pip install -r <リポジトリ>/tools/voice/gptsovits/requirements-lock.txt`（conda を使う install.sh は使わない）
3. 事前学習済みモデル（約5GB）を Hugging Face（XXXXRT/GPT-SoVITS-Pretrained の pretrained_models.zip、G2PWModel.zip、nltk_data.zip、open_jtalk_dic_utf_8-1.11.tar.gz）から取得し、install.sh と同じ場所に展開する
4. `local/` に `prepare.sh`、`train.py`、`self.yaml` を置く

### 学習

```sh
.venv/bin/python -m tools.voice.dataset voices/self/raw/<録音> voices/self/dataset/wav   # 無音で区切る
# 書き起こしを録音原稿と照合し、voices/self/dataset/train.list を作る（言い直しの区間は除く）
models/gpt-sovits/local/prepare.sh <リポジトリ>/voices/self/dataset/train.list
(cd models/gpt-sovits && .venv/bin/python local/train.py all 8 15)
```

- 約85秒の録音で、CPU で約35分
- GPT（韻律）まで追加学習すると、少ない録音では文の一部を飛ばした。SoVITS（声質）だけ追加学習し、GPT は事前学習のものを使う組み合わせ（hybrid）が最もよかった

### 合成と評価

```sh
(cd models/gpt-sovits && .venv/bin/python api_v2.py -a 127.0.0.1 -p 9880 -c local/self.yaml)   # サーバー
.venv/bin/python -m tools.voice.evaluate hybrid zeroshot voicevox                          # 評価用の文章を生成
models/gpt-sovits/.venv/bin/python -m tools.voice.asr_check voices/self/eval/hybrid             # 読み間違いの候補
```

- `voices/self/eval/index.html` をブラウザで開いて聴き比べ、`voices/self/evaluation.md` に評価を書く
- 合成は `tools/infographic/tts.py` の `GptSovits`（サーバーの HTTP API を呼ぶ）。数字の書き方は `normalize_numbers_ja` で読み上げやすい形にする

## 次の段階（承認後）

- 録音の確認が終わったら、試作する方式をユーザーが決める（`method-comparison.md`「進め方」）
- ElevenLabs を使う場合
  - 契約とクローンの作成はユーザーが行う。アップロードの前に、データ利用の設定（Terms and privacy > Data use）でモデル改善への利用を停止する
  - API キーと音声 ID は、リポジトリ直下の `.env`（Git 管理外）に `ELEVENLABS_API_KEY=` と `ELEVENLABS_VOICE_ID=` で書く。エージェントとの会話には貼らない
- 試作した声で `scripts/evaluation.md` の文章を生成し、評価表を `voices/self/evaluation.md` に保存する
- ユーザーが承認した後に、`tools/infographic/tts.py` にバックエンドを追加し、標準の音声に切り替える
