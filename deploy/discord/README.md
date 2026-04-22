# Ploidy Discord bot

Minimal recipe to expose Ploidy as a `/ploidy` slash command in a
Discord server. One long-lived process that forwards the command to
your running Ploidy server via the SSE endpoint.

## One-time setup

1. **Create the Discord app.**
   Go to <https://discord.com/developers/applications> → **New
   Application**. Under the **Bot** tab, **Reset Token** and copy
   the token into `DISCORD_TOKEN`.

2. **Invite the bot to your server.**
   **OAuth2 → URL Generator** → check `bot` and
   `applications.commands`. Visit the generated URL and pick a server.

3. **Optional — limit to one guild for fast iteration.**
   Global slash commands can take up to an hour to propagate. Grab
   your server id (right-click server → Copy Server ID after
   enabling developer mode) and set `PLOIDY_GUILD_ID`. Registration
   becomes instant.

## Run locally

```sh
cd deploy/discord
pip install -r requirements.txt
export DISCORD_TOKEN=...
export PLOIDY_URL=http://127.0.0.1:8765    # or your deployed URL
export PLOIDY_API_TOKEN=...                # if PLOIDY_TOKENS is set server-side
python bot.py
```

Invoke in any channel where the bot is present:

```
/ploidy should we rewrite the ingestion pipeline in Rust?
```

The bot edits one message as the phases land (`phase_started` →
`positions_generated` → `challenges_generated` → `completed`), then
opens a thread under that message and posts the full
`rendered_markdown` chunked to Discord's 2000-char limit.

## Deploy via Docker

```sh
docker build -t ploidy-discord .
docker run -d --restart=unless-stopped \
  -e DISCORD_TOKEN=... \
  -e PLOIDY_URL=https://ploidy.example.com \
  -e PLOIDY_API_TOKEN=... \
  ploidy-discord
```

Also works on fly.io — no HTTP port exposed, so just
`flyctl launch --no-deploy`, set secrets, then `flyctl deploy`.

## Limits + caveats

- The bot edits one message repeatedly so progress shows up in place.
  Discord rate-limits message edits; bursty runs may drop an update
  (the final result still lands via the thread post).
- Markdown rendering in Discord is partial — `<details>` blocks do
  not collapse (Discord ignores raw HTML). Users see the full
  transcript expanded inside the thread. That is acceptable UX for
  Discord but note the difference from the web UI.
- One running bot process per Discord app. If you want per-tenant
  isolation, run multiple bots with different `DISCORD_TOKEN` +
  different `PLOIDY_API_TOKEN` — Ploidy's multitenant auth takes
  care of data separation.
