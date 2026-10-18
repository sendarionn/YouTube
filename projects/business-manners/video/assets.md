# 素材管理

使った外部素材と、独自に生成したもの
原本と台帳は `library/`（原本は Git 管理外、台帳は Git 管理）

## 外部素材

| 種類 | 素材 | 取得元 | ライセンス | 商用・YouTube | クレジット | 台帳 |
| --- | --- | --- | --- | --- | --- | --- |
| アイコン | Tabler Icons 3.48.0（outline、5,166点のうち使用分） | npm パッケージ @tabler/icons の公式配布ファイル（jsDelivr 経由、`tabler-nodes-outline.json`） | MIT | 可 | 表示義務はないが概要欄に記載 | library/icons/catalog.json |
| BGM | Gymnopedie No. 1〜3（Erik Satie 作曲、Kevin MacLeod 演奏） | Wikimedia Commons（incompetech.com の配布） | CC BY 3.0 | 可（収益化可、Content ID 未登録） | 必須。概要欄と動画末尾に記載 | library/bgm/catalog.json（前回の動画で取得・確認済み） |
| 音声 | VOICEVOX ENGINE 0.25.2、春日部つむぎ（ノーマル） | 公式リリース（models/voicevox/） | VOICEVOX・春日部つむぎの利用規約 | 可 | 「VOICEVOX:春日部つむぎ」必須。概要欄と動画末尾に記載 | build_info.json |
| フォント | BIZ UDPゴシック | macOS にインストール済み | SIL Open Font License 1.1 | 可 | 不要 | — |

- アイコンは取得したベクターデータから、動画の配色（DESIGN.md の標準値）と線幅1.75で描き直している
- 使ったアイコンの一覧は `build_info.json` の `icons.used`
- 書籍の表紙、新聞紙面、Web記事のスクリーンショットは使っていない（権利処理が個別に必要なため）

## 独自に生成したもの

`video/scenes.py` で描画（データは `data/` の CSV）

- 年表：戦前、戦後、1980年代の担い手、客室乗務員のイメージの区分、「了解は失礼」の広まり、「ご苦労様」の変化
- グラフ：題名に「マナー」を含む本の数（折れ線）、マナー本319冊の「了解」の扱い（積み上げ棒）、失礼とする理由（横棒）、文化庁調査（横棒）、意識調査（横棒）
- 関係図：担い手の図、「失礼」が広まる流れ、二つの判断、四つの問い、中核と細部、慣習の働き
- ピクトグラム：江戸期の用例23例（人のアイコンは Tabler Icons）
