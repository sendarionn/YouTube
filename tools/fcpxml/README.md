# tools/fcpxml

Final Cut Pro 用のタイムライン（FCPXML 1.13）を生成・検証する
書き出しの全体（シーン映像、音声の分離、final.mp4、manifest.json）は `tools/infographic/export.py`

## タイムラインの構成

| 要素 | 内容 |
| --- | --- |
| 基本ストーリーライン | シーンごとの映像クリップ（`scenes/scene-NNN.mov`、音声なし）。名前は「S001 冒頭」の形 |
| レーン -1 | ナレーション（`audio/narration.wav` をシーンの範囲で区切り、各シーンのクリップに接続）。ロール Dialogue（Narration） |
| レーン -2 | BGM（`audio/bgm.wav`、先頭のクリップに接続した1本）。ロール Music（BGM） |
| レーン -3 | 効果音（使う場合のみ）。ロール Effects（SFX） |
| マーカー | 各シーンの先頭に「S001 冒頭」。実写の挿入位置に To Do マーカー「実写 S005-1：…」 |

- シーンを移動すると、接続したナレーションも一緒に動く
- BGM は先頭のクリップに接続しているため、先頭のシーンを動かすと BGM も動く。先頭のシーンを入れ替える場合は、BGM のクリップを先にタイムラインの先頭に付け直す
- 場面転換のフェードはシーン映像の末尾に描き込み済み。Final Cut Pro のトランジションは使っていない
- アニメーションの中身（図形・文字）は Final Cut Pro では編集できない。変更は `projects/<slug>/video/scenes.py` を直して、そのシーンだけ書き出し直す（`build.py export --only N`）

## 読み込み

1. Final Cut Pro で「ファイル」>「読み込む」>「XML…」を選び、`output/<slug>/video/project.fcpxml` を開く
2. 読み込み先のライブラリを選ぶと、イベント（動画名）とプロジェクトが作られる
3. 素材はライブラリにコピーされず、出力ディレクトリのファイルを参照する（外部メディア）

## 別の Mac・別の場所へ移す

出力ディレクトリ（`output/<slug>/video/`）を丸ごと移す。FCPXML の素材パスは絶対パスのため、移した先で書き換える

```sh
.venv/bin/python -m tools.fcpxml.relink /移した先/project.fcpxml
```

`manifest.json` の相対パスに合わせて書き換え、素材の存在と DTD を検証する
すでに読み込んだライブラリで素材がオフラインになった場合は、Final Cut Pro の「ファイル」>「ファイルを再リンク」で出力ディレクトリを指定する

## 検証

- `validate()`：Final Cut Pro 同梱の DTD（`FCPXMLv1_13.dtd`）と `xmllint` で検証し、参照する素材の存在を確認する
- `tools.infographic.export.verify()`：final.mp4 とシーン映像をつないだものがフレーム単位で一致するか、音声の長さ、ファイルの欠落
- DTD 検証は Final Cut Pro での読み込みを保証しない。実際に読み込んで確認する
