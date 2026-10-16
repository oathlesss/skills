#!/bin/bash
# Combined pregen watcher: Chunky (real chunks) -> DH LOD pregen, on an itzg MC container.
# Supersedes chunky-watch.sh when DH LODs should follow Chunky.
# Re-runnable: the pregen tasks live INSIDE the server process, not this watcher.
# Run with: terminal(background=true, notify_on_complete=true).
#
# Exit 0 when BOTH Chunky and DH pregen finish. Exit 1 on a lost task (server restart)
# or if DH pregen fails to start.
#
# Usage: bash pregen-dh-watch.sh [container] [dh_chunk_radius]
CONTAINER="${1:-minecraft-evo2tech}"
DH_RADIUS="${2:-200}"

STARTED_AT=$(docker inspect --format '{{.State.StartedAt}}' "$CONTAINER" 2>/dev/null)
SAW_CHUNKY=0

# ---------- Phase 1: Chunky ----------
while true; do
  OUT=$(docker exec "$CONTAINER" rcon-cli "chunky progress" 2>&1)
  echo "[$(date +%H:%M:%S)] chunky: $OUT"

  if echo "$OUT" | grep -qiE "100\.00%"; then
    echo "=== CHUNKY COMPLETE (100%) ==="
    break
  fi
  if echo "$OUT" | grep -qiE "task running"; then
    SAW_CHUNKY=1
  fi
  if echo "$OUT" | grep -qiE "no tasks running|no tasks to continue"; then
    if [ "$SAW_CHUNKY" = "1" ]; then
      NOW=$(docker inspect --format '{{.State.StartedAt}}' "$CONTAINER" 2>/dev/null)
      if [ -n "$NOW" ] && [ "$NOW" = "$STARTED_AT" ]; then
        echo "=== CHUNKY COMPLETE (task finished, server stayed up) ==="
        break
      else
        echo "=== CHUNKY FAILED: server restarted, task lost ==="
        exit 1
      fi
    fi
  fi
  sleep 300
done

# ---------- Phase 2: DH LOD pregen ----------
echo "=== starting DH LOD pregen (overworld, radius $DH_RADIUS chunks) ==="
docker exec "$CONTAINER" rcon-cli "dh pregen start minecraft:overworld 0 0 $DH_RADIUS" 2>&1

# Confirm DH actually started (bounded, else we'd spin forever silently).
SAW_DH=0
for i in 1 2 3 4 5 6; do
  sleep 20
  OUT=$(docker exec "$CONTAINER" rcon-cli "dh pregen status" 2>&1)
  echo "[$(date +%H:%M:%S)] dh: $OUT"
  if ! echo "$OUT" | grep -qiE "Pregen is not running"; then
    SAW_DH=1
    break
  fi
done
if [ "$SAW_DH" = "0" ]; then
  echo "=== DH PREGEN FAILED TO START (status stayed 'not running') ==="
  exit 1
fi

while true; do
  OUT=$(docker exec "$CONTAINER" rcon-cli "dh pregen status" 2>&1)
  echo "[$(date +%H:%M:%S)] dh: $OUT"
  if echo "$OUT" | grep -qiE "Pregen is not running"; then
    NOW=$(docker inspect --format '{{.State.StartedAt}}' "$CONTAINER" 2>/dev/null)
    if [ -n "$NOW" ] && [ "$NOW" = "$STARTED_AT" ]; then
      echo "=== DH PREGEN COMPLETE ==="
      exit 0
    else
      echo "=== DH PREGEN FAILED: server restarted ==="
      exit 1
    fi
  fi
  sleep 120
done
