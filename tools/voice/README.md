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

## 次の段階（承認後）

- 録音の確認が終わったら、試作する方式をユーザーが決める（`method-comparison.md`「進め方」）
- ElevenLabs を使う場合
  - 契約とクローンの作成はユーザーが行う。アップロードの前に、データ利用の設定（Terms and privacy > Data use）でモデル改善への利用を停止する
  - API キーと音声 ID は、リポジトリ直下の `.env`（Git 管理外）に `ELEVENLABS_API_KEY=` と `ELEVENLABS_VOICE_ID=` で書く。エージェントとの会話には貼らない
- 試作した声で `scripts/evaluation.md` の文章を生成し、評価表を `voices/self/evaluation.md` に保存する
- ユーザーが承認した後に、`tools/infographic/tts.py` にバックエンドを追加し、標準の音声に切り替える
