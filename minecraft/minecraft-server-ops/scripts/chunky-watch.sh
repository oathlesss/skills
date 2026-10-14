#!/bin/bash
# Poll a Chunky pregen task on an itzg MC container until it completes.
# Re-runnable — the pregen task lives INSIDE the server process, not in this watcher,
# so killing/relaunching loses nothing. Run with: terminal(background=true, notify_on_complete=true).
#
# Exit 0 on genuine completion, exit 1 only if the task is LOST (server restart
# wipes Chunky's in-flight state). "No tasks running" is AMBIGUOUS — it is reported
# BOTH when a task finishes cleanly between polls (Chunky removes the task at 100%)
# AND after a crash-restart wipes the task. Two prior bugs came from misreading it:
#   * treating it as COMPLETE -> false "PREGEN COMPLETE" after an OOM crash
#   * treating it as FAILURE -> false "PREGEN FAILED" after a clean finish
# Disambiguate by comparing the container's StartedAt before/after: if the container
# never restarted, a vanished task means it FINISHED; if StartedAt changed, it was lost.
#
# Usage: bash chunky-watch.sh [container]   (default: minecraft-evo2)
CONTAINER="${1:-minecraft-evo2}"
STARTED_AT=$(docker inspect --format '{{.State.StartedAt}}' "$CONTAINER" 2>/dev/null)
SAW_RUNNING=0

while true; do
  OUT=$(docker exec "$CONTAINER" rcon-cli "chunky progress" 2>&1)
  echo "[$(date +%H:%M:%S)] $OUT"

  # 1) Explicit 100% -> done.
  if echo "$OUT" | grep -qiE "100\.00%"; then
    echo "=== PREGEN COMPLETE (100%) ==="
    exit 0
  fi

  # 2) Remember that a task was observed running — guards against being launched
  #    BEFORE the chunky task starts ("No tasks running" then is not terminal).
  if echo "$OUT" | grep -qiE "task running"; then
    SAW_RUNNING=1
  fi

  # 3) Task gone. Only meaningful if we previously saw it running.
  if echo "$OUT" | grep -qiE "no tasks running|no tasks to continue"; then
    if [ "$SAW_RUNNING" = "1" ]; then
      NOW_STARTED=$(docker inspect --format '{{.State.StartedAt}}' "$CONTAINER" 2>/dev/null)
      if [ -n "$NOW_STARTED" ] && [ "$NOW_STARTED" = "$STARTED_AT" ]; then
        echo "=== PREGEN COMPLETE (task finished, server stayed up) ==="
        exit 0
      else
        echo "=== PREGEN FAILED: server restarted, task lost ==="
        exit 1
      fi
    fi
    # else: task not started yet — keep waiting silently
  fi

  # "Failed to connect"/"connection refused" = server down/restarting. Keep polling;
  # the StartedAt comparison above catches the loss once the server comes back healthy.
  sleep 300
done
