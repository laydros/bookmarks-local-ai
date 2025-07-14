import os
import json
import tempfile
from core.backup_manager import BackupManager, create_safety_backup


def test_directory_backup_and_restore(tmp_path):
    src_dir = tmp_path / "data"
    src_dir.mkdir()
    # Create sample json files
    file1 = src_dir / "a.json"
    file2 = src_dir / "b.json"
    file1.write_text(json.dumps({"a": 1}))
    file2.write_text(json.dumps({"b": 2}))

    manager = BackupManager(backup_dir=str(tmp_path / "backups"))
    backup_dir = manager.create_directory_backup(str(src_dir))
    assert backup_dir is not None
    assert os.path.isdir(backup_dir)
    assert sorted(os.listdir(backup_dir)) == ["a.json", "b.json"]

    # Modify one file and restore from backup
    file1.write_text("changed")
    backup_file = os.path.join(backup_dir, "a.json")
    assert manager.restore_backup(backup_file, str(file1))
    with open(file1) as f:
        data = json.load(f)
    assert data == {"a": 1}


def test_get_backup_stats_and_extract(tmp_path):
    test_file = tmp_path / "test.json"
    test_file.write_text("{}")
    manager = BackupManager(backup_dir=str(tmp_path / "bk"))
    # create two backups to ensure stats count >1
    first = manager.create_backup(str(test_file))
    second = manager.create_backup(str(test_file), "second.backup")
    stats = manager.get_backup_stats()
    assert stats["total_backups"] >= 2
    assert stats["total_size_bytes"] > 0
    # test filename extraction helper
    extracted = manager._extract_original_filename(os.path.basename(first))
    assert extracted == os.path.basename(test_file)


def test_create_safety_backup(tmp_path):
    file_path = tmp_path / "f.json"
    file_path.write_text("{}")
    manager = BackupManager(backup_dir=str(tmp_path / "b"))
    path = create_safety_backup(str(file_path), backup_manager=manager)
    assert path is not None and os.path.exists(path)

    # Directory case
    dir_path = tmp_path / "dir"
    dir_path.mkdir()
    (dir_path / "d.json").write_text("{}")
    dir_backup = create_safety_backup(str(dir_path), backup_manager=manager)
    assert dir_backup is not None and os.path.isdir(dir_backup)
