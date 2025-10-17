from __future__ import annotations

import sys
from http import HTTPStatus
from pathlib import Path
from typing import Dict, Iterator, Tuple

import pytest
from flask.testing import FlaskClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import database, main, paths  # noqa: E402
from app.database import Base


@pytest.fixture
def app_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Dict[str, object]]:
    test_db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{test_db_path}", connect_args={"check_same_thread": False}, future=True
    )
    testing_session_factory = scoped_session(
        sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    )

    monkeypatch.setattr(database, "engine", engine, raising=False)
    monkeypatch.setattr(main, "engine", engine, raising=False)
    monkeypatch.setattr(database, "SessionLocal", testing_session_factory, raising=False)

    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    monkeypatch.setattr(paths, "STORAGE_DIR", storage_dir, raising=False)
    monkeypatch.setattr(main, "STORAGE_DIR", storage_dir, raising=False)

    Base.metadata.create_all(bind=engine)

    test_app = main.create_app()
    test_app.config.update(TESTING=True)

    with test_app.test_client() as test_client:
        register_response = test_client.post(
            "/auth/register",
            json={"email": "tester@example.com", "password": "password123"},
        )
        assert register_response.status_code == HTTPStatus.CREATED
        yield {
            "client": test_client,
            "storage_dir": storage_dir,
            "session_factory": testing_session_factory,
        }

    testing_session_factory.remove()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(app_env: Dict[str, object]) -> Tuple[FlaskClient, Path]:
    return app_env["client"], app_env["storage_dir"]  # type: ignore[return-value]


@pytest.fixture
def db_session(app_env: Dict[str, object]) -> Iterator[Session]:
    session_factory = app_env["session_factory"]  # type: ignore[assignment]
    session = session_factory()  # type: ignore[operator]
    try:
        yield session
    finally:
        session.close()
