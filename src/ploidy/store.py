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

import asyncio
import json
import os
from contextlib import asynccontextmanager
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
    ("model", "ALTER TABLE sessions ADD COLUMN model TEXT"),
    ("effort", "ALTER TABLE sessions ADD COLUMN effort TEXT NOT NULL DEFAULT 'high'"),
)

_DEBATE_MIGRATIONS = (
    (
        "paused_context",
        "ALTER TABLE debates ADD COLUMN paused_context TEXT",
    ),
    (
        "config_json",
        "ALTER TABLE debates ADD COLUMN config_json TEXT NOT NULL DEFAULT '{}'",
    ),
    # Multitenancy: NULL == unscoped legacy row. Filter on owner_id at the
    # service layer; the column alone does not enforce isolation.
    ("owner_id", "ALTER TABLE debates ADD COLUMN owner_id TEXT"),
)

_MESSAGE_MIGRATIONS = (
    ("round", "ALTER TABLE messages ADD COLUMN round INTEGER NOT NULL DEFAULT 1"),
)

_CONVERGENCE_MIGRATIONS = (
    ("meta_analysis", "ALTER TABLE convergence ADD COLUMN meta_analysis TEXT"),
)

_CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_debates_status ON debates(status);
CREATE INDEX IF NOT EXISTS idx_debates_owner ON debates(owner_id);
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
        # Serialises per-write commits across callers; SQLite already serialises
        # writes at the file level but this keeps in-flight transactions coherent.
        self._tx_lock = asyncio.Lock()
        self._in_tx = False

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

    @asynccontextmanager
    async def transaction(self):
        """Batch every commit inside the block into a single SQLite transaction.

        While the context is active, ``db.commit()`` calls from other store
        methods become no-ops — the enclosing transaction commits on exit or
        rolls back on exception. Nested ``transaction()`` calls reuse the
        outermost transaction, so higher-level services can compose.
        """
        db = _require_db(self._db)
        if self._in_tx:
            # Nested call: defer commit/rollback to the outer transaction.
            yield
            return
        async with self._tx_lock:
            self._in_tx = True
            try:
                await db.execute("BEGIN")
                try:
                    yield
                except Exception:
                    await db.rollback()
                    raise
                else:
                    await db.commit()
            finally:
                self._in_tx = False

    async def _commit(self) -> None:
        """Commit unless we're inside a batching ``transaction()`` block."""
        db = _require_db(self._db)
        if self._in_tx:
            return
        await db.commit()

    async def _migrate_schema(self) -> None:
        """Apply additive schema migrations for older databases."""
        db = _require_db(self._db)

        async def _apply_migrations(table: str, migrations: tuple) -> None:
            cursor = await db.execute(f"PRAGMA table_info({table})")
            columns = {row["name"] for row in await cursor.fetchall()}
            for column, statement in migrations:
                if column not in columns:
                    await db.execute(statement)

        await _apply_migrations("sessions", _SESSION_MIGRATIONS)
        await _apply_migrations("debates", _DEBATE_MIGRATIONS)
        await _apply_migrations("messages", _MESSAGE_MIGRATIONS)
        await _apply_migrations("convergence", _CONVERGENCE_MIGRATIONS)

    # ------------------------------------------------------------------
    # Debates
    # ------------------------------------------------------------------

    async def save_debate(
        self,
        debate_id: str,
        prompt: str,
        config: dict | None = None,
        owner_id: str | None = None,
    ) -> None:
        """Persist a new debate record.

        Args:
            debate_id: Unique identifier for the debate.
            prompt: The decision prompt for the debate.
            config: Optional debate configuration dict (ploidy, injection, etc.).
            owner_id: Tenant/owner identifier for multitenant filtering.
                NULL treats the debate as unscoped.
        """
        db = _require_db(self._db)
        await db.execute(
            "INSERT INTO debates (id, prompt, config_json, owner_id) VALUES (?, ?, ?, ?)",
            (debate_id, prompt, json.dumps(config or {}), owner_id),
        )
        await self._commit()

    async def get_debate(self, debate_id: str, owner_id: str | None = None) -> dict | None:
        """Retrieve a debate by its ID.

        Args:
            debate_id: The debate to look up.
            owner_id: When set, enforce that the debate belongs to this owner.

        Returns:
            Debate record as a dict, or None if not found (or owned by someone else).
        """
        db = _require_db(self._db)
        if owner_id is None:
            cursor = await db.execute(
                "SELECT id, prompt, status, owner_id, created_at, updated_at "
                "FROM debates WHERE id = ?",
                (debate_id,),
            )
        else:
            cursor = await db.execute(
                "SELECT id, prompt, status, owner_id, created_at, updated_at "
                "FROM debates WHERE id = ? AND owner_id = ?",
                (debate_id, owner_id),
            )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def list_debates(self, limit: int = 50, owner_id: str | None = None) -> list[dict]:
        """List recent debates.

        Args:
            limit: Maximum number of debates to return.
            owner_id: When set, restrict to debates owned by this id.

        Returns:
            List of debate records, most recent first.
        """
        db = _require_db(self._db)
        if owner_id is None:
            cursor = await db.execute(
                "SELECT id, prompt, status, owner_id, created_at, updated_at "
                "FROM debates ORDER BY created_at DESC LIMIT ?",
                (min(limit, 200),),
            )
        else:
            cursor = await db.execute(
                "SELECT id, prompt, status, owner_id, created_at, updated_at "
                "FROM debates WHERE owner_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (owner_id, min(limit, 200)),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def list_active_debates(self) -> list[dict]:
        """List active debates for state recovery.

        Returns:
            List of active debate records (all owners — recovery is global).
        """
        db = _require_db(self._db)
        cursor = await db.execute(
            "SELECT id, prompt, status, owner_id, created_at, updated_at "
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
        await self._commit()

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
        await self._commit()

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
        await self._commit()

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
        model: str | None = None,
        effort: str = "high",
    ) -> None:
        """Persist a new session record.

        Args:
            session_id: Unique identifier for the session.
            debate_id: The debate this session belongs to.
            role: Session role ('deep', 'semi_fresh', or 'fresh').
            base_prompt: The decision prompt for this session.
            model: Model identifier used for this session.
            effort: Effort level for this session.
        """
        db = _require_db(self._db)
        await db.execute(
            "INSERT INTO sessions "
            "(id, debate_id, role, base_prompt, context_documents, delivery_mode, "
            "compressed_summary, metadata_json, model, effort) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                debate_id,
                role,
                base_prompt,
                json.dumps(context_documents or []),
                delivery_mode,
                compressed_summary,
                json.dumps(metadata or {}),
                model,
                effort,
            ),
        )
        await self._commit()

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
            "compressed_summary, metadata_json, model, effort, created_at "
            "FROM sessions WHERE debate_id = ?",
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
        await self._commit()

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
        await self._commit()

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
        self,
        debate_id: str,
        synthesis: str,
        confidence: float,
        points_json: str,
        meta_analysis: str | None = None,
    ) -> None:
        """Persist a convergence result.

        Args:
            debate_id: The debate this result belongs to.
            synthesis: The synthesized recommendation.
            confidence: Confidence score (0.0 to 1.0).
            points_json: JSON string of convergence points.
            meta_analysis: Optional LLM meta-analysis text.
        """
        db = _require_db(self._db)
        await db.execute(
            "INSERT INTO convergence "
            "(debate_id, synthesis, confidence, points_json, meta_analysis) "
            "VALUES (?, ?, ?, ?, ?)",
            (debate_id, synthesis, confidence, points_json, meta_analysis),
        )
        await self._commit()

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
        self,
        debate_id: str,
        synthesis: str,
        confidence: float,
        points_json: str,
        meta_analysis: str | None = None,
    ) -> None:
        """Atomically save convergence result and mark debate as complete.

        Args:
            debate_id: The debate to finalize.
            synthesis: The synthesized recommendation.
            confidence: Confidence score (0.0 to 1.0).
            points_json: JSON string of convergence points.
            meta_analysis: Optional LLM meta-analysis text.
        """
        db = _require_db(self._db)
        await db.execute(
            "INSERT INTO convergence "
            "(debate_id, synthesis, confidence, points_json, meta_analysis) "
            "VALUES (?, ?, ?, ?, ?)",
            (debate_id, synthesis, confidence, points_json, meta_analysis),
        )
        await db.execute(
            "UPDATE debates SET status = 'complete', updated_at = datetime('now') WHERE id = ?",
            (debate_id,),
        )
        await self._commit()

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
        await self._commit()

    async def purge_terminal_before(self, cutoff_iso: str) -> int:
        """Delete completed/cancelled debates whose updated_at < cutoff.

        Active and paused debates are preserved regardless of age so long
        running sessions are never reaped. Related messages, sessions, and
        convergence rows are cleaned up by the ON DELETE CASCADE FK wired
        into the schema.

        Args:
            cutoff_iso: ISO-8601 UTC timestamp. Rows older than this are
                eligible for deletion.

        Returns:
            Number of debate rows removed.
        """
        db = _require_db(self._db)
        async with self.transaction():
            cursor = await db.execute(
                "DELETE FROM debates WHERE status IN ('complete', 'cancelled') AND updated_at < ?",
                (cutoff_iso,),
            )
            return cursor.rowcount or 0

    async def vacuum(self) -> None:
        """Run ``VACUUM`` to reclaim space after a bulk delete.

        SQLite disallows VACUUM inside a transaction, so callers must
        ensure no ``transaction()`` context is active when this runs.
        """
        db = _require_db(self._db)
        await db.execute("VACUUM")
        await self._commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
