#!/bin/bash
# Single-shot Chunky pregen completion check for LONG pregens (10+ hours).
# Use with cronjob(no_agent=true, script=this-file, schedule="every 30m") INSTEAD of
# chunky-watch.sh: a multi-hour terminal(background) watcher can get orphaned/reaped while
# sleeping, but a cron no_agent watchdog is stateless and robust. Prints a message ONLY when
# there is something to report (empty stdout => cron stays silent). A marker file prevents
# duplicate completion notifications on subsequent ticks.
#
# Usage: bash pregen-completion-check.sh [container]   (default: minecraft-evo2)
# Then: cronjob(action=create, no_agent=true, schedule="every 30m", script="pregen-completion-check.sh")
CONTAINER="${1:-minecraft-evo2}"
MARKER="/home/ruben/homeserver/${CONTAINER}/.pregen-done"

[ -f "$MARKER" ] && exit 0

PROG=$(docker exec "$CONTAINER" rcon-cli "chunky progress" 2>&1)

# 1) Explicit 100% -> done.
if echo "$PROG" | grep -qiE "100\.00%"; then
  touch "$MARKER"
  echo "✅ Minecraft pregen COMPLETE — ${CONTAINER} overworld fully generated."
  exit 0
fi

# 2) Completion line in the server log -> done.
if docker logs --since 24h "$CONTAINER" 2>&1 | grep -qiE "\[Chunky\] Task finished for minecraft:overworld"; then
  touch "$MARKER"
  echo "✅ Minecraft pregen COMPLETE — ${CONTAINER} overworld fully generated."
  exit 0
fi

# 3) Task missing with no completion -> something went wrong.
if echo "$PROG" | grep -qiE "no tasks running|no tasks to continue"; then
  echo "⚠️ Minecraft pregen: Chunky task is missing on ${CONTAINER} (not running, no completion in log) — check it."
fi

exit 0
