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

import json
import os
from pathlib import Path

import aiosqlite

from ploidy.exceptions import PloidyError  # noqa: I001


def default_db_path() -> Path:
    """Resolve the database path from the current environment."""
    return Path(os.environ.get("PLOIDY_DB_PATH", str(Path.home() / ".ploidy" / "ploidy.db")))


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
    debate_id TEXT NOT NULL REFERENCES debates(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    base_prompt TEXT NOT NULL,
    context_documents TEXT NOT NULL DEFAULT '[]',
    delivery_mode TEXT NOT NULL DEFAULT 'none',
    compressed_summary TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id TEXT NOT NULL REFERENCES debates(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    phase TEXT NOT NULL,
    content TEXT NOT NULL,
    action TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS convergence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id TEXT NOT NULL UNIQUE REFERENCES debates(id) ON DELETE CASCADE,
    synthesis TEXT NOT NULL,
    confidence REAL NOT NULL,
    points_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_SESSION_MIGRATIONS = (
    (
        "context_documents",
        "ALTER TABLE sessions ADD COLUMN context_documents TEXT NOT NULL DEFAULT '[]'",
    ),
    ("delivery_mode", "ALTER TABLE sessions ADD COLUMN delivery_mode TEXT NOT NULL DEFAULT 'none'"),
    ("compressed_summary", "ALTER TABLE sessions ADD COLUMN compressed_summary TEXT"),
    ("metadata_json", "ALTER TABLE sessions ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'"),
)

_DEBATE_MIGRATIONS = (
    (
        "paused_context",
        "ALTER TABLE debates ADD COLUMN paused_context TEXT",
    ),
)

_CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_debates_status ON debates(status);
CREATE INDEX IF NOT EXISTS idx_sessions_debate_id ON sessions(debate_id);
CREATE INDEX IF NOT EXISTS idx_messages_debate_id ON messages(debate_id);
"""


def _require_db(db: aiosqlite.Connection | None) -> aiosqlite.Connection:
    """Validate that the database connection is initialized."""
    if db is None:
        raise PloidyError("Store not initialized — call initialize() first")
    return db


class DebateStore:
    """Async SQLite store for debate data.

    Provides CRUD operations for debates, sessions, messages,
    and convergence results. Supports async context manager usage.

    Usage::

        async with DebateStore() as store:
            await store.save_debate("d1", "Should we use Rust?")
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize the store.

        Args:
            db_path: Path to the SQLite database file.
                     Defaults to ``~/.ploidy/ploidy.db``.
        """
        self.db_path = db_path or default_db_path()
        self._db: aiosqlite.Connection | None = None

    async def __aenter__(self) -> DebateStore:
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

        Enables WAL mode for concurrent read/write access and sets up
        the schema for debates, sessions, messages, and convergence results.
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA busy_timeout=5000")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._db.executescript(_CREATE_TABLES)
        await self._migrate_schema()
        await self._db.executescript(_CREATE_INDEXES)
        await self._db.commit()

    async def _migrate_schema(self) -> None:
        """Apply additive schema migrations for older databases."""
        db = _require_db(self._db)
        cursor = await db.execute("PRAGMA table_info(sessions)")
        columns = {row["name"] for row in await cursor.fetchall()}
        for column, statement in _SESSION_MIGRATIONS:
            if column not in columns:
                await db.execute(statement)

        cursor = await db.execute("PRAGMA table_info(debates)")
        debate_columns = {row["name"] for row in await cursor.fetchall()}
        for column, statement in _DEBATE_MIGRATIONS:
            if column not in debate_columns:
                await db.execute(statement)

    # ------------------------------------------------------------------
    # Debates
    # ------------------------------------------------------------------

    async def save_debate(self, debate_id: str, prompt: str) -> None:
        """Persist a new debate record.

        Args:
            debate_id: Unique identifier for the debate.
            prompt: The decision prompt for the debate.
        """
        db = _require_db(self._db)
        await db.execute(
            "INSERT INTO debates (id, prompt) VALUES (?, ?)",
            (debate_id, prompt),
        )
        await db.commit()

    async def get_debate(self, debate_id: str) -> dict | None:
        """Retrieve a debate by its ID.

        Args:
            debate_id: The debate to look up.

        Returns:
            Debate record as a dict, or None if not found.
        """
        db = _require_db(self._db)
        cursor = await db.execute(
            "SELECT id, prompt, status, created_at, updated_at FROM debates WHERE id = ?",
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
        db = _require_db(self._db)
        cursor = await db.execute(
            "SELECT id, prompt, status, created_at, updated_at "
            "FROM debates ORDER BY created_at DESC LIMIT ?",
            (min(limit, 200),),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def list_active_debates(self) -> list[dict]:
        """List active debates for state recovery.

        Returns:
            List of active debate records.
        """
        db = _require_db(self._db)
        cursor = await db.execute(
            "SELECT id, prompt, status, created_at, updated_at "
            "FROM debates WHERE status = 'active' ORDER BY created_at",
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def update_debate_status(self, debate_id: str, status: str) -> None:
        """Update a debate's status.

        Args:
            debate_id: The debate to update.
            status: New status value.
        """
        db = _require_db(self._db)
        await db.execute(
            "UPDATE debates SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, debate_id),
        )
        await db.commit()

    async def save_paused_context(self, debate_id: str, context: dict) -> None:
        """Persist paused auto-debate context alongside the debate record.

        This ensures HITL paused state survives server restarts.

        Args:
            debate_id: The paused debate.
            context: The auto-debate context dict to serialize.
        """
        db = _require_db(self._db)
        await db.execute(
            "UPDATE debates SET paused_context = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(context), debate_id),
        )
        await db.commit()

    async def load_paused_context(self, debate_id: str) -> dict | None:
        """Load persisted paused context for a debate.

        Args:
            debate_id: The debate to look up.

        Returns:
            The paused context dict, or None if not found.
        """
        db = _require_db(self._db)
        cursor = await db.execute(
            "SELECT paused_context FROM debates WHERE id = ?",
            (debate_id,),
        )
        row = await cursor.fetchone()
        if row is None or row["paused_context"] is None:
            return None
        return json.loads(row["paused_context"])

    async def clear_paused_context(self, debate_id: str) -> None:
        """Clear persisted paused context (e.g., after resume or cancel).

        Args:
            debate_id: The debate to clear paused context for.
        """
        db = _require_db(self._db)
        await db.execute(
            "UPDATE debates SET paused_context = NULL, updated_at = datetime('now') WHERE id = ?",
            (debate_id,),
        )
        await db.commit()

    async def list_paused_debates(self) -> list[dict]:
        """List paused debates for state recovery.

        Returns:
            List of paused debate records.
        """
        db = _require_db(self._db)
        cursor = await db.execute(
            "SELECT id, prompt, status, paused_context, created_at, updated_at "
            "FROM debates WHERE status = 'paused' ORDER BY created_at",
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def save_session(
        self,
        session_id: str,
        debate_id: str,
        role: str,
        base_prompt: str,
        context_documents: list[str] | None = None,
        delivery_mode: str = "none",
        compressed_summary: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Persist a new session record.

        Args:
            session_id: Unique identifier for the session.
            debate_id: The debate this session belongs to.
            role: Session role ('experienced' or 'fresh').
            base_prompt: The decision prompt for this session.
        """
        db = _require_db(self._db)
        await db.execute(
            "INSERT INTO sessions "
            "(id, debate_id, role, base_prompt, context_documents, delivery_mode, "
            "compressed_summary, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                debate_id,
                role,
                base_prompt,
                json.dumps(context_documents or []),
                delivery_mode,
                compressed_summary,
                json.dumps(metadata or {}),
            ),
        )
        await db.commit()

    async def get_sessions(self, debate_id: str) -> list[dict]:
        """Retrieve all sessions for a debate.

        Args:
            debate_id: The debate to look up sessions for.

        Returns:
            List of session records.
        """
        db = _require_db(self._db)
        cursor = await db.execute(
            "SELECT id, debate_id, role, base_prompt, context_documents, delivery_mode, "
            "compressed_summary, metadata_json, created_at FROM sessions WHERE debate_id = ?",
            (debate_id,),
        )
        sessions = []
        for row in await cursor.fetchall():
            session = dict(row)
            session["context_documents"] = json.loads(session.get("context_documents") or "[]")
            session["metadata"] = json.loads(session.pop("metadata_json", "{}") or "{}")
            sessions.append(session)
        return sessions

    async def update_session_context(
        self,
        session_id: str,
        *,
        context_documents: list[str] | None = None,
        delivery_mode: str | None = None,
        compressed_summary: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Update persisted session context fields."""
        db = _require_db(self._db)
        await db.execute(
            "UPDATE sessions SET context_documents = ?, delivery_mode = ?, "
            "compressed_summary = ?, metadata_json = ? WHERE id = ?",
            (
                json.dumps(context_documents or []),
                delivery_mode or "none",
                compressed_summary,
                json.dumps(metadata or {}),
                session_id,
            ),
        )
        await db.commit()

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    async def save_message(
        self,
        debate_id: str,
        session_id: str,
        phase: str,
        content: str,
        action: str | None = None,
    ) -> None:
        """Persist a debate message.

        Args:
            debate_id: The debate this message belongs to.
            session_id: The session that authored this message.
            phase: The debate phase when this message was created.
            content: The message content.
            action: Optional semantic action classifying the message.
        """
        db = _require_db(self._db)
        await db.execute(
            "INSERT INTO messages (debate_id, session_id, phase, content, action) "
            "VALUES (?, ?, ?, ?, ?)",
            (debate_id, session_id, phase, content, action),
        )
        await db.commit()

    async def get_messages(self, debate_id: str) -> list[dict]:
        """Retrieve all messages for a debate, ordered by creation time.

        Args:
            debate_id: The debate to look up messages for.

        Returns:
            List of message records.
        """
        db = _require_db(self._db)
        cursor = await db.execute(
            "SELECT id, debate_id, session_id, phase, content, action, timestamp "
            "FROM messages WHERE debate_id = ? ORDER BY id",
            (debate_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Convergence
    # ------------------------------------------------------------------

    async def save_convergence(
        self, debate_id: str, synthesis: str, confidence: float, points_json: str
    ) -> None:
        """Persist a convergence result.

        Args:
            debate_id: The debate this result belongs to.
            synthesis: The synthesized recommendation.
            confidence: Confidence score (0.0 to 1.0).
            points_json: JSON string of convergence points.
        """
        db = _require_db(self._db)
        await db.execute(
            "INSERT INTO convergence (debate_id, synthesis, confidence, points_json) "
            "VALUES (?, ?, ?, ?)",
            (debate_id, synthesis, confidence, points_json),
        )
        await db.commit()

    async def get_convergence(self, debate_id: str) -> dict | None:
        """Retrieve the convergence result for a debate.

        Args:
            debate_id: The debate to look up.

        Returns:
            Convergence record as a dict, or None if not found.
        """
        db = _require_db(self._db)
        cursor = await db.execute(
            "SELECT debate_id, synthesis, confidence, points_json, created_at "
            "FROM convergence WHERE debate_id = ?",
            (debate_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    async def save_convergence_and_complete(
        self, debate_id: str, synthesis: str, confidence: float, points_json: str
    ) -> None:
        """Atomically save convergence result and mark debate as complete.

        Args:
            debate_id: The debate to finalize.
            synthesis: The synthesized recommendation.
            confidence: Confidence score (0.0 to 1.0).
            points_json: JSON string of convergence points.
        """
        db = _require_db(self._db)
        await db.execute(
            "INSERT INTO convergence (debate_id, synthesis, confidence, points_json) "
            "VALUES (?, ?, ?, ?)",
            (debate_id, synthesis, confidence, points_json),
        )
        await db.execute(
            "UPDATE debates SET status = 'complete', updated_at = datetime('now') WHERE id = ?",
            (debate_id,),
        )
        await db.commit()

    async def delete_debate(self, debate_id: str) -> None:
        """Permanently delete a debate and all associated data.

        Removes messages, sessions, convergence results, and the debate itself.

        Args:
            debate_id: The debate to delete.
        """
        db = _require_db(self._db)
        await db.execute("DELETE FROM messages WHERE debate_id = ?", (debate_id,))
        await db.execute("DELETE FROM convergence WHERE debate_id = ?", (debate_id,))
        await db.execute("DELETE FROM sessions WHERE debate_id = ?", (debate_id,))
        await db.execute("DELETE FROM debates WHERE id = ?", (debate_id,))
        await db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
