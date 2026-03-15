"""Persistence layer for Ploidy.

Stores debate history, session contexts, and convergence results
using aiosqlite for async SQLite access. All debate data is persisted
so that future sessions can reference past decisions -- this is how
Session A (the experienced session) accumulates context over time.

Tables:
    debates      -- Debate metadata (id, prompt, status, timestamps)
    sessions     -- Session contexts and roles within a debate
    messages     -- Individual debate messages with phase information
    convergence  -- Convergence results and synthesis outputs
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite

_DEFAULT_DB_DIR = Path.home() / ".ploidy"
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "ploidy.db"

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS debates (
    id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    debate_id TEXT NOT NULL REFERENCES debates(id),
    role TEXT NOT NULL,
    base_prompt TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id TEXT NOT NULL REFERENCES debates(id),
    session_id TEXT NOT NULL REFERENCES sessions(id),
    phase TEXT NOT NULL,
    content TEXT NOT NULL,
    action TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS convergence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id TEXT NOT NULL UNIQUE REFERENCES debates(id),
    synthesis TEXT NOT NULL,
    confidence REAL NOT NULL,
    points_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class DebateStore:
    """Async SQLite store for debate data.

    Provides CRUD operations for debates, sessions, messages,
    and convergence results. Supports async context manager usage.

    Usage::

        async with DebateStore() as store:
            await store.save_debate("d1", "Should we use Rust?")
    """

    def __init__(self, db_path: Path = _DEFAULT_DB_PATH) -> None:
        """Initialize the store.

        Args:
            db_path: Path to the SQLite database file.
                     Defaults to ``~/.ploidy/ploidy.db``.
        """
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def __aenter__(self) -> "DebateStore":
        """Enter the async context manager -- open DB and create tables."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit the async context manager -- close DB."""
        await self.close()

    async def initialize(self) -> None:
        """Create database tables if they don't exist.

        Sets up the schema for debates, sessions, messages,
        and convergence results.
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_CREATE_TABLES)
        await self._db.commit()

    async def save_debate(self, debate_id: str, prompt: str) -> None:
        """Persist a new debate record.

        Args:
            debate_id: Unique identifier for the debate.
            prompt: The decision prompt for the debate.
        """
        assert self._db is not None, "Store not initialized"
        await self._db.execute(
            "INSERT INTO debates (id, prompt) VALUES (?, ?)",
            (debate_id, prompt),
        )
        await self._db.commit()

    async def get_debate(self, debate_id: str) -> dict | None:
        """Retrieve a debate by its ID.

        Args:
            debate_id: The debate to look up.

        Returns:
            Debate record as a dict, or None if not found.
        """
        assert self._db is not None, "Store not initialized"
        cursor = await self._db.execute(
            "SELECT id, prompt, status, created_at, updated_at "
            "FROM debates WHERE id = ?",
            (debate_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def list_debates(self, limit: int = 50) -> list[dict]:
        """List recent debates.

        Args:
            limit: Maximum number of debates to return.

        Returns:
            List of debate records, most recent first.
        """
        assert self._db is not None, "Store not initialized"
        cursor = await self._db.execute(
            "SELECT id, prompt, status, created_at, updated_at "
            "FROM debates ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
