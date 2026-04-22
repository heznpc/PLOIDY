# Raycast integration

Macintosh power-launcher integration via Raycast's **Script Commands**
(not a full extension — those require a TypeScript build and Store
review, which is overkill for wrapping one CLI).

## Install

1. **Install the CLI** (once):
   ```sh
   pip install 'ploidy[cli]'
   ```
2. **Set the server URL** in your shell profile (once):
   ```sh
   export PLOIDY_URL=http://127.0.0.1:8765     # or your deployed URL
   export PLOIDY_API_TOKEN=...                 # if PLOIDY_TOKENS is set
   ```
3. **Register the script with Raycast**:
   Raycast → Settings → Extensions → **Script Commands** →
   **Add Directory** → pick this `tools/raycast/` folder. Raycast
   auto-discovers `ploidy-debate.sh` via the `@raycast.*` metadata
   comments.

## Use

Raycast → `ploidy debate` → type the decision question → return.
Progress streams into Raycast's output pane, the final
`rendered_markdown` lands after.

## Why scripts instead of a full extension

A full Raycast extension (TypeScript + React + a build toolchain +
Store submission) buys:
- Native forms with structured inputs
- Auto-refresh of past debates via the dashboard API

…which we already have via the web UI and `ploidy-history`. The
script command covers the 95% case — hotkey → decision → answer —
with zero new build pipeline. If the structured UI becomes worth the
maintenance, the extension can layer on top of the same HTTP API.
