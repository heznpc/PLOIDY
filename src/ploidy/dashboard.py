"""Lightweight web dashboard for Ploidy debate history.

Provides a read-only web interface for viewing past debates, timelines,
convergence results, and session comparisons from the SQLite database.

Usage:
    python -m ploidy.dashboard          # Start on port 8766
    PLOIDY_DASH_PORT=9000 python -m ploidy.dashboard

Requires: pip install ploidy[dashboard]
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("ploidy.dashboard")

_DASH_PORT = int(os.environ.get("PLOIDY_DASH_PORT", "8766"))
_DB_PATH = Path(os.environ.get("PLOIDY_DB_PATH", str(Path.home() / ".ploidy" / "ploidy.db")))

# ---------------------------------------------------------------------------
# HTML Templates (inline to avoid external dependencies)
# ---------------------------------------------------------------------------

_BASE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ploidy Dashboard</title>
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --yellow: #d29922;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.6; }
  .container { max-width: 1200px; margin: 0 auto; padding: 1rem; }
  header { background: var(--surface); border-bottom: 1px solid var(--border);
           padding: 1rem 2rem; display: flex; align-items: center; gap: 1rem; }
  header h1 { font-size: 1.4rem; }
  header h1 span { color: var(--accent); }
  nav a { color: var(--muted); text-decoration: none; margin-left: 1.5rem;
          font-size: 0.9rem; }
  nav a:hover { color: var(--text); }
  .card { background: var(--surface); border: 1px solid var(--border);
          border-radius: 8px; padding: 1.2rem; margin: 1rem 0; }
  .card h2 { font-size: 1.1rem; margin-bottom: 0.8rem; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
           font-size: 0.75rem; font-weight: 600; }
  .badge-active { background: #1f6feb33; color: var(--accent); }
  .badge-complete { background: #23883333; color: var(--green); }
  .badge-cancelled { background: #f8514933; color: var(--red); }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.6rem 1rem; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-size: 0.85rem; text-transform: uppercase; }
  td a { color: var(--accent); text-decoration: none; }
  td a:hover { text-decoration: underline; }
  .timeline { position: relative; padding-left: 2rem; }
  .timeline::before { content: ''; position: absolute; left: 0.5rem; top: 0;
                       bottom: 0; width: 2px; background: var(--border); }
  .timeline-item { position: relative; margin-bottom: 1.5rem; }
  .timeline-item::before { content: ''; position: absolute; left: -1.65rem;
                            top: 0.5rem; width: 10px; height: 10px;
                            border-radius: 50%; background: var(--accent); }
  .timeline-item .phase { color: var(--accent); font-weight: 600;
                           text-transform: uppercase; font-size: 0.8rem; }
  .timeline-item .role { color: var(--muted); font-size: 0.85rem; }
  .timeline-item .content { margin-top: 0.3rem; white-space: pre-wrap;
                              font-size: 0.9rem; max-height: 200px;
                              overflow-y: auto; }
  .convergence-point { padding: 0.8rem; margin: 0.5rem 0;
                        border-left: 3px solid var(--border); }
  .convergence-point.agreement { border-color: var(--green); }
  .convergence-point.productive_disagreement { border-color: var(--yellow); }
  .convergence-point.irreducible { border-color: var(--red); }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
           gap: 1rem; margin: 1rem 0; }
  .stat { text-align: center; }
  .stat .value { font-size: 2rem; font-weight: 700; color: var(--accent); }
  .stat .label { color: var(--muted); font-size: 0.85rem; }
  .confidence-bar { height: 8px; border-radius: 4px; background: var(--border);
                     overflow: hidden; margin-top: 0.3rem; }
  .confidence-fill { height: 100%; border-radius: 4px; background: var(--green);
                      transition: width 0.3s; }
  footer { text-align: center; padding: 2rem; color: var(--muted);
           font-size: 0.8rem; }
</style>
</head>
<body>
<header>
  <h1><span>Ploidy</span> Dashboard</h1>
  <nav>
    <a href="/">Debates</a>
    <a href="/stats">Statistics</a>
  </nav>
</header>
<div class="container">
  {{CONTENT}}
</div>
<footer>Ploidy v0.2 &mdash; Context-Asymmetric Structured Debate</footer>
</body>
</html>"""


def _render(content: str) -> str:
    """Render content into the base HTML template."""
    return _BASE_HTML.replace("{{CONTENT}}", content)


def _badge(status: str) -> str:
    """Generate a status badge HTML."""
    cls = {
        "active": "badge-active",
        "complete": "badge-complete",
        "cancelled": "badge-cancelled",
    }.get(status, "badge-active")
    return f'<span class="badge {cls}">{status}</span>'


# ---------------------------------------------------------------------------
# Database access (read-only)
# ---------------------------------------------------------------------------


async def _get_db():
    """Get a read-only database connection."""
    import aiosqlite

    db = await aiosqlite.connect(f"file:{_DB_PATH}?mode=ro", uri=True)
    db.row_factory = aiosqlite.Row
    return db


async def _fetch_debates(limit: int = 100) -> list[dict]:
    """Fetch recent debates from the database."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT id, prompt, status, created_at, updated_at "
            "FROM debates ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


async def _fetch_debate_detail(debate_id: str) -> dict | None:
    """Fetch full debate detail including sessions, messages, and convergence."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT id, prompt, status, created_at, updated_at FROM debates WHERE id = ?",
            (debate_id,),
        )
        debate = await cursor.fetchone()
        if not debate:
            return None
        result = dict(debate)

        cursor = await db.execute(
            "SELECT id, role, base_prompt, created_at FROM sessions WHERE debate_id = ?",
            (debate_id,),
        )
        result["sessions"] = [dict(r) for r in await cursor.fetchall()]

        cursor = await db.execute(
            "SELECT session_id, phase, content, action, timestamp "
            "FROM messages WHERE debate_id = ? ORDER BY id",
            (debate_id,),
        )
        result["messages"] = [dict(r) for r in await cursor.fetchall()]

        cursor = await db.execute(
            "SELECT synthesis, confidence, points_json, created_at "
            "FROM convergence WHERE debate_id = ?",
            (debate_id,),
        )
        conv = await cursor.fetchone()
        result["convergence"] = dict(conv) if conv else None

        return result
    finally:
        await db.close()


async def _fetch_stats() -> dict:
    """Fetch aggregate statistics."""
    db = await _get_db()
    try:
        stats = {}

        cursor = await db.execute("SELECT COUNT(*) as n FROM debates")
        stats["total_debates"] = (await cursor.fetchone())["n"]

        cursor = await db.execute("SELECT COUNT(*) as n FROM debates WHERE status = 'complete'")
        stats["completed"] = (await cursor.fetchone())["n"]

        cursor = await db.execute("SELECT COUNT(*) as n FROM debates WHERE status = 'active'")
        stats["active"] = (await cursor.fetchone())["n"]

        cursor = await db.execute("SELECT AVG(confidence) as avg_conf FROM convergence")
        row = await cursor.fetchone()
        stats["avg_confidence"] = round(row["avg_conf"] or 0, 3)

        cursor = await db.execute("SELECT COUNT(*) as n FROM messages")
        stats["total_messages"] = (await cursor.fetchone())["n"]

        cursor = await db.execute("SELECT COUNT(*) as n FROM sessions")
        stats["total_sessions"] = (await cursor.fetchone())["n"]

        return stats
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


def _render_debate_list(debates: list[dict]) -> str:
    """Render the debate list page."""
    if not debates:
        return _render('<div class="card"><p>No debates yet. Start one!</p></div>')

    rows = ""
    for d in debates:
        prompt_preview = (d["prompt"] or "")[:80]
        if len(d["prompt"] or "") > 80:
            prompt_preview += "..."
        rows += (
            f"<tr>"
            f'<td><a href="/debate/{d["id"]}">{d["id"]}</a></td>'
            f"<td>{prompt_preview}</td>"
            f"<td>{_badge(d['status'])}</td>"
            f"<td>{d['created_at']}</td>"
            f"</tr>"
        )

    return _render(
        f'<div class="card"><h2>Recent Debates</h2>'
        f"<table><thead><tr>"
        f"<th>ID</th><th>Prompt</th><th>Status</th><th>Created</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _render_debate_detail(d: dict) -> str:
    """Render a single debate detail page."""
    sessions_html = ""
    role_map = {}
    for s in d.get("sessions", []):
        role_map[s["id"]] = s["role"]
        sessions_html += (
            f'<div class="card"><strong>{s["role"].capitalize()}</strong> &mdash; {s["id"]}</div>'
        )

    timeline_html = ""
    for m in d.get("messages", []):
        role = role_map.get(m["session_id"], "unknown")
        action_label = f" [{m['action']}]" if m.get("action") else ""
        content_preview = (m["content"] or "")[:500]
        timeline_html += (
            f'<div class="timeline-item">'
            f'<div class="phase">{m["phase"]}{action_label}</div>'
            f'<div class="role">{role} &mdash; {m.get("timestamp", "")}</div>'
            f'<div class="content">{content_preview}</div>'
            f"</div>"
        )

    convergence_html = ""
    conv = d.get("convergence")
    if conv:
        conf_pct = int((conv.get("confidence") or 0) * 100)
        convergence_html += (
            f'<div class="card"><h2>Convergence Result</h2>'
            f'<div class="confidence-bar">'
            f'<div class="confidence-fill" style="width:{conf_pct}%"></div>'
            f"</div>"
            f"<p>Confidence: {conf_pct}%</p>"
        )

        try:
            points = json.loads(conv.get("points_json", "[]"))
            for p in points:
                cat = p.get("category", "irreducible")
                convergence_html += (
                    f'<div class="convergence-point {cat}">'
                    f"<strong>{cat.replace('_', ' ').title()}</strong>: "
                    f"{p.get('summary', '')[:200]}"
                    f"</div>"
                )
        except (json.JSONDecodeError, TypeError):
            pass

        synthesis = conv.get("synthesis", "")
        convergence_html += f"<h3>Synthesis</h3><pre>{synthesis[:2000]}</pre></div>"

    return _render(
        f'<div class="card"><h2>Debate: {d["id"]}</h2>'
        f"<p>{d.get('prompt', '')}</p>"
        f"<p>{_badge(d.get('status', 'active'))}</p>"
        f"<p>Created: {d.get('created_at', '')}</p></div>"
        f'<div class="card"><h2>Sessions</h2>{sessions_html}</div>'
        f'<div class="card"><h2>Timeline</h2>'
        f'<div class="timeline">{timeline_html}</div></div>'
        f"{convergence_html}"
    )


def _render_stats(stats: dict) -> str:
    """Render the statistics page."""
    return _render(
        f'<div class="stats">'
        f'<div class="stat"><div class="value">{stats.get("total_debates", 0)}</div>'
        f'<div class="label">Total Debates</div></div>'
        f'<div class="stat"><div class="value">{stats.get("completed", 0)}</div>'
        f'<div class="label">Completed</div></div>'
        f'<div class="stat"><div class="value">{stats.get("active", 0)}</div>'
        f'<div class="label">Active</div></div>'
        f'<div class="stat"><div class="value">{stats.get("avg_confidence", 0)}</div>'
        f'<div class="label">Avg Confidence</div></div>'
        f'<div class="stat"><div class="value">{stats.get("total_messages", 0)}</div>'
        f'<div class="label">Messages</div></div>'
        f'<div class="stat"><div class="value">{stats.get("total_sessions", 0)}</div>'
        f'<div class="label">Sessions</div></div>'
        f"</div>"
    )


# ---------------------------------------------------------------------------
# ASGI Application
# ---------------------------------------------------------------------------


async def app(scope, receive, send):
    """Minimal ASGI application for the Ploidy dashboard."""
    if scope["type"] != "http":
        return

    path = scope["path"]
    method = scope["method"]

    if method != "GET":
        await _send_response(send, 405, "Method not allowed")
        return

    try:
        if path == "/" or path == "":
            debates = await _fetch_debates()
            html = _render_debate_list(debates)
            await _send_response(send, 200, html)

        elif path.startswith("/debate/"):
            debate_id = path.split("/debate/")[1].strip("/")
            detail = await _fetch_debate_detail(debate_id)
            if detail is None:
                await _send_response(send, 404, _render("<p>Debate not found.</p>"))
            else:
                html = _render_debate_detail(detail)
                await _send_response(send, 200, html)

        elif path == "/stats":
            stats = await _fetch_stats()
            html = _render_stats(stats)
            await _send_response(send, 200, html)

        elif path == "/api/debates":
            debates = await _fetch_debates()
            await _send_json(send, 200, debates)

        elif path.startswith("/api/debate/"):
            debate_id = path.split("/api/debate/")[1].strip("/")
            detail = await _fetch_debate_detail(debate_id)
            if detail is None:
                await _send_json(send, 404, {"error": "not found"})
            else:
                await _send_json(send, 200, detail)

        elif path == "/api/stats":
            stats = await _fetch_stats()
            await _send_json(send, 200, stats)

        else:
            await _send_response(send, 404, _render("<p>Page not found.</p>"))

    except Exception as e:
        logger.error("Dashboard error: %s", e)
        await _send_response(send, 500, _render(f"<p>Error: {e}</p>"))


async def _send_response(send, status: int, body: str):
    """Send an HTML response."""
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"text/html; charset=utf-8"],
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": body.encode("utf-8"),
        }
    )


async def _send_json(send, status: int, data):
    """Send a JSON response."""
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"),
        }
    )


def main():
    """Run the dashboard server."""
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "uvicorn required for dashboard. Install with: pip install ploidy[dashboard]"
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Starting Ploidy Dashboard on port %d", _DASH_PORT)
    logger.info("Database: %s", _DB_PATH)
    uvicorn.run(app, host="0.0.0.0", port=_DASH_PORT)


if __name__ == "__main__":
    main()
