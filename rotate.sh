#!/bin/bash
# Rotates ~/.claude/session-log.md: moves every entry it holds into
# ~/.claude/session-log-history.md and resets the main file to its header.
# The sign-off skill runs this right before appending the new session entry,
# so the main file always contains exactly one session (the latest).
set -euo pipefail

MAIN="$HOME/.claude/session-log.md"
HIST="$HOME/.claude/session-log-history.md"

header() {
  printf '# Session Log — última sesión\n\n'
  printf 'Historial completo de sesiones anteriores: `~/.claude/session-log-history.md` (buscar por `## Session:` o por nombre de proyecto).\n'
}

[ -f "$HIST" ] || printf '# Session Log — History\n\n' > "$HIST"

if [ ! -f "$MAIN" ]; then
  header > "$MAIN"
  echo "rotated: main file did not exist, created empty"
  exit 0
fi

# Body = everything from the first "## " heading onward (skips the header block).
BODY=$(awk 'f{print; next} /^## /{f=1; print}' "$MAIN")

if [ -n "$(printf '%s' "$BODY" | tr -d '[:space:]')" ]; then
  printf '\n---\n\n%s\n' "$BODY" >> "$HIST"
  COUNT=$(printf '%s\n' "$BODY" | grep -c '^## ' || true)
else
  COUNT=0
fi

header > "$MAIN"
echo "rotated: $COUNT entr(y/ies) moved to $HIST"
