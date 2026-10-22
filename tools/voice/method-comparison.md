# オリジナル音声の方式比較

調査日：2026-10-22
料金・規約は変わるため、契約前に公式ページで再確認する。引用元は末尾の「出典」

## 結論（推奨）

1. **試作は ElevenLabs の Instant Voice Cloning（IVC）、Starter プラン（月6ドル）で行う**
   - 推奨する録音の長さ（1〜2分）が、今回の試作の想定と一致する
   - 日本語に対応したモデルが複数あり、文字ごとの時刻を返す API があるため、字幕・映像の同期に使える
   - 有料プランで作った音声は商用利用でき、解約後もその期間に作った音声の商用ライセンスは続く
2. **同じ録音で、ローカルの GPT-SoVITS も試作し、聴き比べる**（外部送信なし、費用なし）
   - コードと事前学習済みモデルは MIT ライセンス。Mac での推論に対応し、学習は CPU で可能
   - 日本語の品質と、この Mac での学習時間は未検証。良ければ ElevenLabs の契約を続けずに済む
3. Style-Bert-VITS2 は、学習に NVIDIA の GPU が必要で、この Mac では学習できない。クラウドの GPU を使う場合は録音を外部に送ることになるため、上の2つで品質が足りない場合の候補とする
4. Fish Speech（年間売上の上限つきライセンス）と F5-TTS（非営利ライセンス）は、収益化する動画には使わない

承認が必要なこと（今回はどれも実行していない）
- ElevenLabs の契約（Starter、月6ドル）と、録音のアップロード
- アップロード前に、アカウント設定でモデル改善への利用を停止すること（後述）
- GPT-SoVITS の導入（ダウンロード数GB、外部送信なし）

## この Mac の環境

| 項目 | 値 |
| --- | --- |
| 機種 | MacBook Air（Apple M3、CPU 8コア、GPU 10コア） |
| メモリ | 24GB |
| OS | macOS 26.4 |
| 空き容量 | 67GB（使用率85%） |
| 録音デバイス | MacBook Air の内蔵マイク、iPhone 15 Pro（連係マイク）。外付けマイクはない |
| NVIDIA GPU | なし（CUDA は使えない） |

## 比較

| | ElevenLabs IVC | ElevenLabs PVC | GPT-SoVITS（ローカル） | Style-Bert-VITS2 |
| --- | --- | --- | --- | --- |
| 必要な録音 | 1〜2分（3分を超えても改善は小さい） | 30分〜3時間 | 推論は5秒〜、追加学習は約1分 | 2〜14秒の音声を複数と書き起こし。総量の目安は「試行錯誤」 |
| 日本語 | 対応 | 対応 | 推論に対応（日本語の品質は未検証） | 日本語に特化（JP-Extra） |
| この Mac で使えるか | 使える（API） | 使える（API） | 推論は MPS/CPU、学習は CPU（Mac の GPU での学習は品質が下がると README に記載） | 推論は CPU で可能、学習は不可（NVIDIA GPU が必要） |
| 費用 | Starter 月6ドル（年払いなら月5ドル） | Creator 月22ドル（初月11ドル） | 無料（電気代のみ） | 無料。学習にクラウドの GPU を使う場合は別途 |
| 商用利用 | 有料プランで可 | 有料プランで可 | コード・事前学習済みモデルとも MIT | コード・ベースモデルとも AGPL-3.0。生成音声の扱いは未確認 |
| 録音の外部送信 | あり | あり（本人確認の録音も） | なし | 学習をクラウドで行う場合はあり |
| モデルの持ち出し | できない（アカウント内に残る） | できない | できる（ファイル） | できる（ファイル） |
| 字幕の同期 | 文字ごとの時刻を返す API がある | 同じ | 文ごとに合成して長さから決める | 同じ |
| 運用の負担 | 小（API キーと音声 ID の管理） | 小（学習に3〜24時間） | 中（Python 環境、モデル、学習） | 大（学習環境の用意） |

## ElevenLabs の詳細

### プランと費用

| プラン | 月額 | 月のクレジット | 商用利用 | IVC | PVC |
| --- | --- | --- | --- | --- | --- |
| Free | 0ドル | 1万 | 不可（帰属表示が必要） | なし | なし |
| Starter | 6ドル | 3万 | 可 | あり | なし |
| Creator | 22ドル（初月11ドル） | 12.1万 | 可 | あり | 1 |
| Pro | 99ドル | 60万 | 可 | あり | 1 |

- Multilingual v2 は1文字＝1クレジット。Flash / Turbo v2.5 は API で1文字0.5〜1クレジット
- 使わなかったクレジットは2か月分まで繰り越せる（Free を除く）
- API 料金のページは、API の利用を「クレジットではなく米ドルで課金」としており、Starter に含まれる文字数を「7.5万」としている。料金ページのクレジットとの関係は公式ページだけでは読み取れないため、契約時に確認する
- 支出の上限を設定する方法は、公式ページに記載がない。こちらの実装で、1回・1か月あたりの文字数に上限を設ける

この動画の規模での目安（Multilingual v2、1文字＝1クレジットとした場合）

| 対象 | 文字数 | Starter（3万）で |
| --- | --- | --- |
| business-manners の全ナレーション | 3,657 | 月に約8本分 |
| founders-elite の全ナレーション | 2,241 | 月に約13本分 |
| 試作・評価（評価用原稿を数回生成） | 約3,000〜6,000 | 1か月目の大半 |

- 一度生成した音声は保存して再利用するため、再生成しない限りクレジットは減らない
- 直した文だけを再生成する

### モデル

| モデル | 日本語 | 1回の上限 | 公式の位置づけ |
| --- | --- | --- | --- |
| eleven_v4 | 対応 | 1万字 | 品質・コンテンツ制作向け |
| eleven_multilingual_v2 | 対応 | 1万字 | 品質・コンテンツ制作向け。数字の読み上げに強い |
| eleven_v3 | 対応 | 5,000字 | 前世代 |
| eleven_flash_v2_5 | 対応 | 4万字 | 低遅延・低価格。数字の正規化は既定で無効 |

- v4 と Multilingual v2 を聴き比べて選ぶ。IVC の FAQ は「Flash v2.5 と Multilingual v2 の言語でクローンできる」としており、v4 での IVC の扱いは試作で確認する
- `language_code` は Multilingual v2 では使えない。日本語専用のテキスト正規化（`apply_language_text_normalization`）があるが、遅延が大きく増えると注意書きがある
- 一貫性のための指定：`seed`（同じ結果は保証されない）、`previous_text` / `next_text`、`voice_settings`（stability、similarity_boost、style、speed）
- 出力形式：WAV / PCM の48kHz がある。44.1kHz の PCM / WAV は Pro 以上
- 発音辞書（pronunciation dictionaries）を1回に3つまで指定できる

### 録音・データの扱い

- 有料プランで作った音声は商用利用でき、解約後もその期間に作った音声の商用ライセンスは続く。Free で作った音声は商用利用できない
- 生成した音声の権利は利用者に残る。音声モデル自体は「Output」に含まれない
- アップロードした録音は、規約上、サービスの改善と新しいサービスの開発に使われうる。アカウントの設定（Terms and privacy > Data use の「Improve the models for everyone」）で停止でき、停止後に送ったデータには学習に使わない。停止前の利用には及ばない
  - → アップロードの前に停止する
- 声のモデルは削除できる（元に戻せない）。アップロードした録音そのものが一緒に消えるかは記載がない。声に関するデータは最後の利用から最大3年保持すると、プライバシーポリシーにある
- クローンは単独のファイルとして書き出せず、アカウントの中に残る。作り直すには元の録音が必要 → 録音原本を `voices/` に保存し、バックアップする
- 自分の声のクローンを作るには、本人確認（音声の CAPTCHA）を求められることがある
- ElevenLabs の電子透かしを他のプラットフォームは検出できず、YouTube の収益化とは関係しないと、ヘルプにある

## ローカル方式の詳細

### GPT-SoVITS

- コード：MIT。事前学習済みモデル（Hugging Face の lj1995/GPT-SoVITS）：MIT（モデルページのメタデータによる）
- 5秒の音声での推論（ゼロショット）と、約1分の音声での追加学習（few-shot）
- 推論の言語に日本語を含む。README の今後の課題に「Japanese and English dataset fine tune training」がある
- macOS は `install.sh --device MPS|CPU` で導入できる。Mac の GPU で学習したモデルは品質がかなり下がるため、当面は CPU で学習すると README にある
- この Mac での学習時間・メモリ使用量・日本語の品質は、導入して試すまで分からない

### Style-Bert-VITS2

- 日本語に特化した高品質な方式。学習には「2〜14秒程度の音声ファイルが複数と、その書き起こし」が必要
- 「NVIDIA の GPU が無い場合は学習はできません」と README にあり、この Mac では学習できない。推論は CPU で動く
- 動作確認済みの環境は Windows・WSL2・Linux で、macOS の記載はない

### 使わないもの

- Fish Speech：独自ライセンス（年間売上50万ドル未満の場合だけ商用利用可、それ以外は別契約）。日本語の記載もない
- F5-TTS：事前学習済みモデルが CC-BY-NC（非営利）

## 進め方

1. ユーザーが録音する（`tools/voice/README.md`、原稿は `tools/voice/scripts/recording.md`）
2. `python -m tools.voice.check_recording` で録音の品質を確認する
3. 承認を得てから、次のどちらか、または両方を試作する
   - ElevenLabs：ユーザーが Starter を契約し、データ利用の停止を設定してから、ユーザー自身が IVC を作る。API キーと音声 ID は `.env` に書く（エージェントには貼らない）
   - GPT-SoVITS：`models/gpt-sovits/` に導入し、同じ録音で試す
4. 評価用の原稿（`tools/voice/scripts/evaluation.md`）を生成し、評価表で比べる
5. ユーザーが承認したら、`tools/infographic/tts.py` にバックエンドを追加し、標準の音声にする（承認までは VOICEVOX のまま）

## 出典

ElevenLabs（2026-10-22 確認）
- Instant Voice Cloning：https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/instant-voice-cloning
- Professional Voice Cloning：https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/professional-voice-cloning
- Voice cloning（API の概要）：https://elevenlabs.io/docs/eleven-api/concepts/voice-cloning
- 料金：https://elevenlabs.io/pricing 、https://elevenlabs.io/pricing/api
- モデル：https://elevenlabs.io/docs/overview/models
- 時刻つきの音声合成 API：https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
- 利用規約（2026-10-09 更新）：https://elevenlabs.io/terms-of-use
- プライバシーポリシー：https://elevenlabs.io/privacy-policy
- 禁止用途：https://elevenlabs.io/use-policy
- 商用利用：https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform.md
- データ利用の停止：https://elevenlabs.io/docs/help-center/legal/is-my-data-used-to-improve-eleven-labs-ai-models
- 解約後の権利：https://elevenlabs.io/docs/help-center/account/general/what-happens-to-my-content-after-my-subscription-ends.md
- 声の削除：https://elevenlabs.io/docs/help-center/product/voices/my-voices/how-do-i-delete-voices-from-my-voices.md

ローカル方式
- GPT-SoVITS：https://github.com/RVC-Boss/GPT-SoVITS 、事前学習済みモデル https://huggingface.co/lj1995/GPT-SoVITS
- Style-Bert-VITS2：https://github.com/litagin02/Style-Bert-VITS2 、ベースモデル https://huggingface.co/litagin/Style-Bert-VITS2-2.0-base-JP-Extra
- Fish Speech：https://github.com/fishaudio/fish-speech
- F5-TTS：https://github.com/SWivid/F5-TTS
