import pytest
from fastapi.testclient import TestClient

from app import main


def test_app_startup_fails_when_database_initialization_fails(monkeypatch):
    async def fail_database_initialization():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(main, "init_db", fail_database_initialization)

    with pytest.raises(RuntimeError, match="database unavailable"):
        with TestClient(main.app):
            pass
