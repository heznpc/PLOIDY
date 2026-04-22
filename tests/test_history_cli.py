"""Tests for the ploidy-history terminal browser."""

from __future__ import annotations

import pytest

from ploidy import history_cli
from ploidy.store import DebateStore


@pytest.fixture
async def seeded_store(tmp_path, monkeypatch):
    db = tmp_path / "hist.db"
    monkeypatch.setenv("PLOIDY_DB_PATH", str(db))
    store = DebateStore(db_path=db)
    await store.initialize()
    try:
        await store.save_debate("abc12345", "Rust vs Go?")
        await store.save_debate("def67890", "Monorepo or polyrepo?")
        await store.save_session("abc12345-deep-001", "abc12345", "deep", "Rust vs Go?")
        await store.save_convergence(
            "abc12345",
            synthesis="Consider Go for the teamsize.",
            confidence=0.75,
            points_json='[{"category":"agreement","summary":"Startup speed matters"}]',
        )
        await store.update_debate_status("abc12345", "complete")
    finally:
        await store.close()
    yield db


class TestListCommand:
    async def test_lists_debates_with_confidence(self, seeded_store, capsys):
        rc = await history_cli.run(["list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "abc12345" in out
        assert "def67890" in out
        assert "75%" in out
        assert "Rust vs Go?" in out

    async def test_empty_db_prints_placeholder(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("PLOIDY_DB_PATH", str(tmp_path / "empty.db"))
        rc = await history_cli.run(["list"])
        assert rc == 0
        assert "No debates yet" in capsys.readouterr().out

    async def test_default_command_is_list(self, seeded_store, capsys):
        rc = await history_cli.run([])
        assert rc == 0
        assert "abc12345" in capsys.readouterr().out


class TestShowCommand:
    async def test_show_exact_id(self, seeded_store, capsys):
        rc = await history_cli.run(["show", "abc12345"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Debate abc12345" in out
        assert "75%" in out
        assert "Consider Go" in out
        assert "Startup speed matters" in out

    async def test_show_by_prefix(self, seeded_store, capsys):
        rc = await history_cli.run(["show", "abc"])
        assert rc == 0
        assert "Debate abc12345" in capsys.readouterr().out

    async def test_show_unknown_id_returns_1(self, seeded_store, capsys):
        rc = await history_cli.run(["show", "nonexistent"])
        assert rc == 1
        # Error message goes to stderr.
        assert "No debate matches" in capsys.readouterr().err

    async def test_show_with_no_convergence_yet(self, tmp_path, monkeypatch, capsys):
        db = tmp_path / "pending.db"
        monkeypatch.setenv("PLOIDY_DB_PATH", str(db))
        store = DebateStore(db_path=db)
        await store.initialize()
        try:
            await store.save_debate("pending01", "In progress?")
        finally:
            await store.close()

        rc = await history_cli.run(["show", "pending01"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Debate pending01" in out
        assert "No convergence result yet" in out


class TestTableFormatter:
    def test_columns_align(self):
        table = history_cli._format_table(
            [["a", "short"], ["bb", "longer"]],
            ["col1", "col2"],
        )
        lines = table.splitlines()
        assert lines[0].startswith("col1")
        assert "col2" in lines[0]
        # Each data row parses back into at least one cell per column.
        for data_line in lines[2:]:
            assert len(data_line.split()) >= 2

    def test_truncate_respects_width(self):
        out = history_cli._truncate("a" * 100, 10)
        assert len(out) == 10
        assert out.endswith("…")
