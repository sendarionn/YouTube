"""Git 管理外の非公開原稿（private/）のバックアップと復元

バックアップ先はリポジトリの外に置く。パスはコードにも公開リポジトリにも書かず、環境変数 PRIVATE_BACKUP_DIR か、
リポジトリ直下の .env（Git 管理外）の PRIVATE_BACKUP_DIR= で指定する
外付けストレージや暗号化したボリューム（macOS の暗号化ディスクイメージなど）を指定できる。暗号化はこのツールでは行わない

- 1回のバックアップは日時つきの tar.gz（private-YYYYmmdd-HHMMSS.tar.gz）と、各ファイルの SHA-256 を記録した .json
- 過去のバックアップは削除・上書きしない（誤操作で消した原稿を前の日時から戻せる）
- 保存後に、書き出した tar.gz を読み直して元のファイルと一致するか確認する
- 復元は空のディレクトリにだけ行い、作業中の private/ を上書きしない
"""
import hashlib
import io
import json
import os
import tarfile
from datetime import datetime
from pathlib import Path

from tools.infographic.config import REPO

SOURCE = REPO / "private"


class BackupError(Exception):
    pass


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def backup_dir():
    """バックアップ先（環境変数、なければ .env）。リポジトリの中は拒否する"""
    value = os.environ.get("PRIVATE_BACKUP_DIR")
    env = REPO / ".env"
    if not value and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("PRIVATE_BACKUP_DIR="):
                value = line.split("=", 1)[1].strip().strip("\"'")
    if not value:
        raise BackupError("バックアップ先が未設定（PRIVATE_BACKUP_DIR を環境変数か .env に書く）")
    return Path(value).expanduser()


def _check_dest(dest, source):
    dest, source = dest.resolve(), source.resolve()
    for root in (REPO.resolve(), source):
        if dest == root or root in dest.parents:
            raise BackupError(f"バックアップ先がリポジトリまたは元の場所の中にある：{dest}")


def snapshot_files(source):
    return sorted(p for p in source.rglob("*") if p.is_file() and p.name != ".DS_Store")


def create(source=SOURCE, dest=None, now=None):
    """バックアップを1つ作り、検証して、(tar.gz のパス, 記録) を返す"""
    source = Path(source)
    dest = Path(dest) if dest else backup_dir()
    _check_dest(dest, source)
    files = snapshot_files(source)
    if not files:
        raise BackupError(f"バックアップするファイルがない：{source}")
    dest.mkdir(parents=True, exist_ok=True)
    os.chmod(dest, 0o700)  # 非公開原稿のため所有者だけが読めるようにする
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    archive = dest / f"private-{stamp}.tar.gz"
    if archive.exists():
        raise BackupError(f"同じ名前のバックアップがある：{archive}")
    record = {"created": stamp, "source": "private/", "files": {}}
    tmp = archive.with_suffix(".part")
    with tarfile.open(tmp, "w:gz") as tar:
        for p in files:
            data = p.read_bytes()
            rel = p.relative_to(source).as_posix()
            record["files"][rel] = {"sha256": _sha256(data), "bytes": len(data)}
            info = tarfile.TarInfo(f"private/{rel}")
            info.size = len(data)
            info.mtime = int(p.stat().st_mtime)
            info.mode = 0o600
            tar.addfile(info, io.BytesIO(data))
    os.chmod(tmp, 0o600)
    tmp.rename(archive)
    record["archive_sha256"] = _sha256(archive.read_bytes())
    meta = archive.with_name(archive.name[:-7] + ".json")
    meta.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(meta, 0o600)
    problems = verify(archive, source)
    if problems:
        raise BackupError("保存したバックアップが元と一致しない：" + "；".join(problems))
    return archive, record


def _record(archive):
    return json.loads(Path(archive).with_name(Path(archive).name[:-7] + ".json").read_text(encoding="utf-8"))


def verify(archive, source=None):
    """tar.gz が記録（とあれば元のファイル）と一致するか。問題の一覧を返す"""
    archive = Path(archive)
    rec = _record(archive)
    problems = []
    if "archive_sha256" in rec and _sha256(archive.read_bytes()) != rec["archive_sha256"]:
        problems.append("tar.gz のハッシュが記録と違う")
    seen = set()
    try:
        with tarfile.open(archive, "r:gz") as tar:
            for m in tar.getmembers():
                rel = m.name.split("/", 1)[1]
                seen.add(rel)
                data = tar.extractfile(m).read()
                if rel not in rec["files"] or _sha256(data) != rec["files"][rel]["sha256"]:
                    problems.append(f"記録と違う：{rel}")
                if source is not None and (Path(source) / rel).read_bytes() != data:
                    problems.append(f"元のファイルと違う：{rel}")
    except (tarfile.TarError, OSError, EOFError) as e:
        problems.append(f"展開できない：{e}")
    problems += [f"tar.gz にない：{f}" for f in set(rec["files"]) - seen]
    return problems


def snapshots(dest=None):
    dest = Path(dest) if dest else backup_dir()
    return sorted(dest.glob("private-*.tar.gz"))


def restore(archive, target):
    """空のディレクトリ target に private/ を復元し、記録と照合する"""
    archive, target = Path(archive), Path(target)
    if target.exists() and any(target.iterdir()):
        raise BackupError(f"復元先が空ではない（上書きしない）：{target}")
    problems = verify(archive)
    if problems:
        raise BackupError("バックアップが壊れている：" + "；".join(problems))
    rec = _record(archive)
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        for m in tar.getmembers():
            rel = m.name.split("/", 1)[1]
            if rel.startswith("/") or ".." in Path(rel).parts:
                raise BackupError(f"不正なパス：{m.name}")
            out = target / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(tar.extractfile(m).read())
    bad = [rel for rel, v in rec["files"].items() if _sha256((target / rel).read_bytes()) != v["sha256"]]
    if bad:
        raise BackupError("復元したファイルが記録と違う：" + "、".join(bad))
    return sorted(rec["files"])
