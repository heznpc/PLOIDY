import pytest


@pytest.fixture(autouse=True)
def _test_db_path(tmp_path, monkeypatch):
    """Force each test to use an isolated writable SQLite path."""
    monkeypatch.setenv("PLOIDY_DB_PATH", str(tmp_path / "ploidy.db"))
    yield
