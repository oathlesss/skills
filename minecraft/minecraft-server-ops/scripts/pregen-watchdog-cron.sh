#!/bin/bash
# Single-shot Chunky pregen completion + C2ME deadlock watchdog — for LONG pregens.
# WHY: chunky-watch.sh (a terminal-background `sleep 300` loop) can get orphaned/reaped
# over a 10h+ sleep. For pregens over ~10h, register this via a cron no_agent job instead:
#   cronjob(action=create, no_agent=true, script="pregen-watchdog-cron.sh", schedule="every 30m")
# It prints a message ONLY when there is something to report; empty stdout => the cron
# delivers nothing (silent watchdog pattern). A marker file dedupes completion notifications;
# a state file tracks the Processed count so a FROZEN task (C2ME deadlock) is caught across ticks.
#
# Usage: bash pregen-watchdog-cron.sh [container]   (default: minecraft-evo2)
CONTAINER="${1:-minecraft-evo2}"
BASE="/home/ruben/homeserver/${CONTAINER}"
MARKER="$BASE/.pregen-done"
STATE="$BASE/.pregen-state"

[ -f "$MARKER" ] && exit 0

# ---- completion (authoritative: the log line, not `chunky progress`) ----
if docker logs --since 24h "$CONTAINER" 2>&1 | grep -qiE "\[Chunky\] Task finished for minecraft:overworld"; then
  touch "$MARKER"
  echo "✅ Minecraft pregen COMPLETE — overworld fully generated."
  exit 0
fi

# ---- task missing (lost / cancelled) ----
PROG=$(docker exec "$CONTAINER" rcon-cli "chunky progress" 2>&1)
if echo "$PROG" | grep -qiE "no tasks running|no tasks to continue"; then
  echo "⚠️ Minecraft pregen: Chunky task missing (not running, no completion in log) — check $CONTAINER."
  exit 0
fi

# ---- C2ME thread explosion (deadlock signature: 8199 threads vs normal ~150) ----
PIDS=$(docker stats --no-stream --format '{{.PIDs}}' "$CONTAINER" 2>/dev/null | grep -oE '[0-9]+' | head -1)
if [ -n "$PIDS" ] && [ "$PIDS" -gt 1000 ] 2>/dev/null; then
  echo "🚨 C2ME thread explosion: $PIDS PIDs (normal ~150). Remove C2ME (rm c2me-*.jar) and restart."
  exit 0
fi

# ---- chunky frozen (Processed count unchanged across ticks) ----
# Read Processed from the LOG, NOT rcon-cli: under heavy C2ME load `rcon-cli "chunky progress"`
# can return EMPTY (the progress response goes to the server log instead). Chunky logs ~1s.
LAST_PROG=$(docker logs --tail 200 "$CONTAINER" 2>&1 | grep -oE "Processed: [0-9]+ chunks" | tail -1)
PROCESSED=$(echo "$LAST_PROG" | grep -oE "[0-9]+" | head -1)
if [ -n "$PROCESSED" ]; then
  PREV=$(cat "$STATE" 2>/dev/null)
  if [ -n "$PREV" ] && [ "$PREV" = "$PROCESSED" ]; then
    echo "🚨 Chunky appears FROZEN: Processed stuck at $PROCESSED for one tick (C2ME deadlock?). Check $CONTAINER."
  fi
  printf '%s' "$PROCESSED" > "$STATE"
fi

exit 0
