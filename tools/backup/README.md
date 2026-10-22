# tools/backup

Git 管理外の非公開原稿（`private/`。note の有料部分を含む原稿など）と録音原本（`voices/`）をバックアップし、復元を確認する
それぞれのディレクトリの下に追加したファイルは、自動的に対象になる

## 設定

バックアップ先はリポジトリの外に置き、パスは公開リポジトリに書かない
環境変数 `PRIVATE_BACKUP_DIR`、またはリポジトリ直下の `.env`（Git 管理外）に書く

```sh
PRIVATE_BACKUP_DIR=~/Backups/YouTube-private
```

- 外付けストレージや、暗号化したボリュームのパスも指定できる（例：macOS の「ディスクユーティリティ」で作った暗号化ディスクイメージをマウントした場所）。暗号化はこのツールでは行わない
- クラウドへのアップロードや同期はしない。クラウドに置く場合は、ユーザーの承認を得てから行う

## 使い方

リポジトリ直下で実行する

```sh
.venv/bin/python -m tools.backup create     # private/ を日時つきの tar.gz に保存し、元のファイルと照合する
.venv/bin/python -m tools.backup create voices   # voices/（録音原本）を同じ方法で保存する
.venv/bin/python -m tools.backup list       # バックアップの一覧と、それぞれの検証結果
.venv/bin/python -m tools.backup verify <バックアップ先>/private-YYYYmmdd-HHMMSS.tar.gz
```

- 保存するもの：`private-YYYYmmdd-HHMMSS.tar.gz` と、各ファイルの SHA-256 を記録した同名の `.json`（どちらも所有者だけが読める）
- 過去のバックアップは削除・上書きしない。原稿を誤って上書き・削除した場合は、その前の日時のバックアップから戻せる
- 原稿を直したとき、配布資料を大きく変えたとき、公開の前に `create` を実行する

## 復元

1. `list` で戻したい日時のバックアップを選び、`OK` になっていることを確かめる
2. 空のディレクトリに復元する。作業中の `private/` は上書きしない

   ```sh
   .venv/bin/python -m tools.backup restore <バックアップ先>/private-YYYYmmdd-HHMMSS.tar.gz /tmp/private-restore
   ```

3. 復元したファイルを確認してから、必要なファイルだけを `private/` に戻す（例：`cp /tmp/private-restore/<slug>/note/article.md private/<slug>/note/`）
4. 戻した後に `create` を実行し、新しいバックアップを作る

復元では tar.gz と各ファイルのハッシュを記録と照合し、一致しない場合は中止する
