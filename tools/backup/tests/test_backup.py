"""private/ のバックアップと復元のテスト（一時ディレクトリで行う）"""
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools import backup  # noqa: E402
from tools.infographic.config import REPO  # noqa: E402


def make_source(tmp_path):
    src = tmp_path / "private"
    (src / "demo" / "note").mkdir(parents=True)
    (src / "demo" / "note" / "article.md").write_text("# 原稿\n\n有料部分を含む本文\n", encoding="utf-8")
    (src / "demo" / "note" / "report.md").write_text("# レポート\n", encoding="utf-8")
    return src


def test_create_verify_restore(tmp_path):
    src = make_source(tmp_path)
    dest = tmp_path / "backup"
    archive, rec = backup.create(src, dest, now=datetime(2026, 10, 21, 12, 0, 0))
    assert archive.name == "private-20261021-120000.tar.gz" and len(rec["files"]) == 2
    assert backup.verify(archive, src) == []
    out = tmp_path / "restored"
    files = backup.restore(archive, out)
    assert files == ["demo/note/article.md", "demo/note/report.md"]
    for f in files:
        assert (out / f).read_bytes() == (src / f).read_bytes()


def test_versions_are_kept_and_old_content_restorable(tmp_path):
    src = make_source(tmp_path)
    dest = tmp_path / "backup"
    a1, _ = backup.create(src, dest, now=datetime(2026, 10, 21, 12, 0, 0))
    (src / "demo" / "note" / "article.md").write_text("誤って上書きした", encoding="utf-8")
    a2, _ = backup.create(src, dest, now=datetime(2026, 10, 21, 13, 0, 0))
    assert backup.snapshots(dest) == [a1, a2]
    backup.restore(a1, tmp_path / "r1")
    assert "有料部分を含む本文" in (tmp_path / "r1" / "demo" / "note" / "article.md").read_text(encoding="utf-8")
    with pytest.raises(backup.BackupError):
        backup.create(src, dest, now=datetime(2026, 10, 21, 13, 0, 0))  # 同じ日時のバックアップを上書きしない


def test_corruption_is_detected(tmp_path):
    src = make_source(tmp_path)
    archive, _ = backup.create(src, tmp_path / "backup")
    data = bytearray(archive.read_bytes())
    data[len(data) // 2] ^= 0xFF
    archive.write_bytes(bytes(data))
    assert backup.verify(archive)
    with pytest.raises(backup.BackupError):
        backup.restore(archive, tmp_path / "r")


def test_refuses_unsafe_destinations(tmp_path):
    src = make_source(tmp_path)
    with pytest.raises(backup.BackupError):
        backup.create(src, REPO / "backup-in-repo")
    with pytest.raises(backup.BackupError):
        backup.create(src, src / "inside")
    archive, _ = backup.create(src, tmp_path / "backup")
    (tmp_path / "nonempty").mkdir()
    (tmp_path / "nonempty" / "x").write_text("x")
    with pytest.raises(backup.BackupError):
        backup.restore(archive, tmp_path / "nonempty")


def test_destination_is_not_hardcoded(monkeypatch):
    monkeypatch.delenv("PRIVATE_BACKUP_DIR", raising=False)
    monkeypatch.setattr(backup, "REPO", Path("/nonexistent-repo"))
    with pytest.raises(backup.BackupError):
        backup.backup_dir()
    monkeypatch.setenv("PRIVATE_BACKUP_DIR", "~/somewhere")
    assert backup.backup_dir() == Path("~/somewhere").expanduser()


def test_voices_source_uses_its_own_name(tmp_path):
    src = tmp_path / "voices"
    (src / "me" / "raw").mkdir(parents=True)
    (src / "me" / "raw" / "take01.wav").write_bytes(b"RIFF....WAVE")
    dest = tmp_path / "backup"
    archive, _ = backup.create(src, dest, now=datetime(2026, 10, 22, 9, 0, 0))
    assert archive.name == "voices-20261022-090000.tar.gz"
    assert backup.snapshots(dest, "voices") == [archive] and backup.snapshots(dest, "private") == []
    files = backup.restore(archive, tmp_path / "r")
    assert files == ["me/raw/take01.wav"]
