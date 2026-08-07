from pathlib import Path
import sqlite3
import pytest

from ka9q_beacon_monitor.operations.release import backup_sqlite_database, restore_sqlite_database, build_release_manifest, OperationsError


def _db(path: Path, value: str = "original"):
    c=sqlite3.connect(path); c.execute("create table sample(v text)"); c.execute("insert into sample values(?)",(value,)); c.commit(); c.close()


def test_backup_restore_roundtrip_and_checksum(tmp_path):
    db=tmp_path/'db.sqlite'; backup=tmp_path/'backup.sqlite'; _db(db)
    meta=backup_sqlite_database(db, backup)
    db.unlink(); restore_sqlite_database(backup, db, expected_sha256=meta['sha256'])
    c=sqlite3.connect(db); assert c.execute('select v from sample').fetchone()[0]=='original'; c.close()


def test_restore_rejects_tampered_backup_without_replacing_database(tmp_path):
    db=tmp_path/'db.sqlite'; backup=tmp_path/'backup.sqlite'; _db(db)
    meta=backup_sqlite_database(db, backup); backup.write_bytes(backup.read_bytes()+b'x')
    with pytest.raises(OperationsError): restore_sqlite_database(backup, db, expected_sha256=meta['sha256'])
    c=sqlite3.connect(db); assert c.execute('select v from sample').fetchone()[0]=='original'; c.close()


def test_release_manifest_blocks_field_release_when_phase0_unverified(tmp_path):
    package=tmp_path/'release.zip'; package.write_bytes(b'release')
    m=build_release_manifest(version='0.1.0', revision='abc', package_path=package,
        review_decisions={'M5.1':'APPROVED','M5.2':'APPROVED','M5.3':'APPROVED','M5.4':'APPROVED','M5.5':'APPROVED'},
        phase0_assumptions={'P0-A-001':'UNVERIFIED','P0-A-002':'UNVERIFIED','P0-A-003':'UNVERIFIED'})
    assert m['software_release_ready'] is True
    assert m['field_release_ready'] is False
    assert len(m['release_blockers']) == 3


def test_release_manifest_requires_all_reviews_approved(tmp_path):
    package=tmp_path/'release.zip'; package.write_bytes(b'release')
    m=build_release_manifest(version='0.1.0', revision='abc', package_path=package,
        review_decisions={'M5.5':'APPROVED_WITH_CHANGES'}, phase0_assumptions={})
    assert not m['software_release_ready'] and not m['field_release_ready']


def test_restore_copy_failure_cleans_staging_and_preserves_database(tmp_path, monkeypatch):
    db=tmp_path/'db.sqlite'; backup=tmp_path/'backup.sqlite'; _db(db)
    meta=backup_sqlite_database(db, backup)
    staging=db.with_name(db.name + '.restore-next')

    import ka9q_beacon_monitor.operations.release as release_module
    def failing_copy(src, dst):
        Path(dst).write_bytes(b'partial')
        raise OSError('simulated disk full during restore copy')
    monkeypatch.setattr(release_module.shutil, 'copy2', failing_copy)

    with pytest.raises(OSError, match='simulated disk full'):
        restore_sqlite_database(backup, db, expected_sha256=meta['sha256'])

    assert not staging.exists()
    c=sqlite3.connect(db); assert c.execute('select v from sample').fetchone()[0]=='original'; c.close()
