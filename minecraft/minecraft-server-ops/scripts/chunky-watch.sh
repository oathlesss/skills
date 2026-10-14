#!/bin/bash
# Poll a Chunky pregen task on an itzg MC container until it completes.
# Re-runnable — the pregen task lives INSIDE the server process, not in this watcher,
# so killing/relaunching loses nothing. Run with: terminal(background=true, notify_on_complete=true).
#
# Usage: bash chunky-watch.sh [container]   (default: minecraft-evo2)
CONTAINER="${1:-minecraft-evo2}"
while true; do
  OUT=$(docker exec "$CONTAINER" rcon-cli "chunky progress" 2>&1)
  echo "[$(date +%H:%M:%S)] $OUT"
  if echo "$OUT" | grep -qiE "no tasks running|100\.00%"; then
    echo "=== PREGEN COMPLETE ==="
    exit 0
  fi
  sleep 300
done
