from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from app.mock_data import seed_mock_data
from app.models import File, Folder


def test_seed_mock_data_idempotent(db_session, app_env) -> None:
    storage_dir: Path = app_env["storage_dir"]  # type: ignore[assignment]

    seed_mock_data(db_session, storage_dir)

    folders = db_session.execute(select(Folder)).scalars().all()
    files = db_session.execute(select(File)).scalars().all()
    storage_files = sorted(storage_dir.iterdir())

    # Seed a second time to confirm no duplicate records are created.
    seed_mock_data(db_session, storage_dir)

    folders_after = db_session.execute(select(Folder)).scalars().all()
    files_after = db_session.execute(select(File)).scalars().all()
    storage_files_after = sorted(storage_dir.iterdir())

    assert len(folders_after) == len(folders)
    assert len(files_after) == len(files)
    assert len(storage_files_after) == len(storage_files)

    assert {file.storage_path for file in files_after} == set(storage_files_after)
