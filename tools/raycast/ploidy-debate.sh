#!/usr/bin/env bash
# Raycast Script Command — wraps `ploidy-ask` so a decision question can
# be run from the macOS Raycast launcher without leaving the keyboard.
#
# Install: Raycast → Extensions → Script Commands → add this directory,
# or symlink this file into ~/.config/raycast/scripts/.
#
# Prereqs:
#   pip install ploidy[cli]           # ploidy-ask in $PATH
#   export PLOIDY_URL=... (optional)  # defaults to http://127.0.0.1:8765
#   export PLOIDY_API_TOKEN=...       # if the server configures PLOIDY_TOKENS
#
# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Ploidy debate
# @raycast.mode fullOutput
# @raycast.icon 🎯
# @raycast.packageName Ploidy
# @raycast.argument1 { "type": "text", "placeholder": "Decision question" }
# @raycast.description Run a Ploidy debate on a question and show the rendered result.
# @raycast.author heznpc

set -euo pipefail

QUESTION="${1:-}"

if [[ -z "$QUESTION" ]]; then
    echo "❌ pass a decision question"
    exit 1
fi

if ! command -v ploidy-ask >/dev/null 2>&1; then
    echo "❌ ploidy-ask not found on \$PATH"
    echo ""
    echo "Install with:"
    echo "    pip install 'ploidy[cli]'"
    exit 1
fi

# ploidy-ask streams progress to stderr and final rendered_markdown to
# stdout. Raycast's fullOutput mode shows both concatenated, which is
# exactly what we want: live progress ticks followed by the answer.
exec ploidy-ask "$QUESTION"
