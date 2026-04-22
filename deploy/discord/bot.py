"""Minimal Discord bot that exposes Ploidy as a ``/ploidy`` slash command.

Runs as a long-lived process. On command invocation it opens the
Ploidy SSE stream, updates the reply message as each phase lands, and
finally posts the rendered markdown into a thread under the command
response.

Env vars
    DISCORD_TOKEN      — bot token from the Discord developer portal
    PLOIDY_URL         — Ploidy server base URL (default localhost:8765)
    PLOIDY_API_TOKEN   — bearer token if the server configures PLOIDY_TOKENS
    PLOIDY_GUILD_ID    — optional; register the command in one guild for
                         instant rollout instead of global (which takes
                         up to an hour to propagate)
"""

from __future__ import annotations

import json
import os

import discord
import httpx
from discord import app_commands

PLOIDY_URL = os.environ.get("PLOIDY_URL", "http://127.0.0.1:8765").rstrip("/")
PLOIDY_TOKEN = os.environ.get("PLOIDY_API_TOKEN")
GUILD_ID = os.environ.get("PLOIDY_GUILD_ID")

_PROGRESS_EMOJI = {
    "phase_started": "📍",
    "positions_generated": "🧠",
    "challenges_generated": "⚔️",
    "completed": "✅",
    "error": "❌",
}


def _describe(event_type: str, data: dict) -> str:
    if event_type == "phase_started":
        return f"phase: `{data.get('phase')}`"
    if event_type == "positions_generated":
        return f"{data.get('side')} positions × {data.get('count')}"
    if event_type == "challenges_generated":
        return "challenges exchanged"
    if event_type == "completed":
        conf = data.get("confidence")
        pct = f"{int(conf * 100)}%" if isinstance(conf, (int, float)) else "?"
        return f"done — confidence {pct}, {data.get('points')} points"
    if event_type == "error":
        return f"error: {data.get('message', '')}"
    return event_type


async def _stream_debate(prompt: str):
    headers = {"Content-Type": "application/json"}
    if PLOIDY_TOKEN:
        headers["Authorization"] = f"Bearer {PLOIDY_TOKEN}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as client:
        async with client.stream(
            "POST",
            f"{PLOIDY_URL}/v1/debate/stream",
            headers=headers,
            json={"prompt": prompt, "deep_n": 1, "fresh_n": 1},
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                decoded = body.decode(errors="replace")
                yield "error", {"message": f"HTTP {resp.status_code}: {decoded}"}
                return

            buffer = ""
            async for chunk in resp.aiter_bytes():
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n\n" in buffer:
                    frame, buffer = buffer.split("\n\n", 1)
                    event_type = None
                    data_line = None
                    for line in frame.splitlines():
                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                        elif line.startswith("data:"):
                            data_line = line[5:].strip()
                    if not event_type or data_line is None:
                        continue
                    try:
                        parsed = json.loads(data_line)
                    except json.JSONDecodeError:
                        continue
                    yield event_type, parsed.get("data", {})


intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@tree.command(name="ploidy", description="Run a Ploidy debate on a decision question.")
@app_commands.describe(question="The decision you want a second opinion on.")
async def ploidy(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)

    progress_lines: list[str] = []
    rendered: str | None = None
    errored = False

    async for event_type, data in _stream_debate(question):
        emoji = _PROGRESS_EMOJI.get(event_type, "·")
        progress_lines.append(f"{emoji} {_describe(event_type, data)}")
        if event_type == "error":
            errored = True

        # Discord permits editing the deferred message repeatedly.
        content = "\n".join(progress_lines[-12:])
        try:
            await interaction.edit_original_response(content=f"```\n{content}\n```")
        except discord.HTTPException:
            pass

        if event_type == "result":
            rendered = data.get("rendered_markdown") or data.get("synthesis")

    if errored or not rendered:
        await interaction.edit_original_response(
            content="```\n" + "\n".join(progress_lines) + "\n```"
        )
        return

    # Final reply = progress panel + threaded full markdown (Discord's 2000-char
    # limit is the reason we push the full rendered_markdown into a thread).
    await interaction.edit_original_response(
        content="```\n" + "\n".join(progress_lines[-6:]) + "\n```"
    )
    try:
        original = await interaction.original_response()
        thread = await original.create_thread(name=question[:90], auto_archive_duration=60)
        # Discord messages cap at 2000 chars — chunk accordingly.
        for chunk in _chunk(rendered, 1900):
            await thread.send(chunk)
    except discord.HTTPException as exc:
        await interaction.followup.send(f"Could not post thread: {exc}")


def _chunk(text: str, size: int):
    for i in range(0, len(text), size):
        yield text[i : i + size]


@client.event
async def on_ready():
    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
        print(f"Ready; /ploidy registered on guild {GUILD_ID}")
    else:
        await tree.sync()
        print("Ready; /ploidy registered globally (up to ~1h to propagate)")


def main() -> None:
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Set DISCORD_TOKEN before running.")
    client.run(token)


if __name__ == "__main__":
    main()
