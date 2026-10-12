#!/bin/bash
# Nightly Minecraft world backups — tar.gz each world, keep 7 days
# Usage: chmod +x, then create a Hermes no-agent cron:
#   cronjob action=create no_agent=true schedule="0 4 * * *" script="backup-minecraft.sh" deliver=local
set -euo pipefail

BACKUP_DIR="/home/ruben/homeserver/backups/minecraft"
WORLDS_DIR="/home/ruben/homeserver"

mkdir -p "$BACKUP_DIR"

for server in vanilla modded; do
    world_path="${WORLDS_DIR}/minecraft-${server}/data/world"
    if [ -d "$world_path" ]; then
        archive="${BACKUP_DIR}/${server}-$(date +%Y%m%d).tar.gz"
        tar -czf "$archive" -C "$(dirname "$world_path")" world/
        size=$(du -h "$archive" | cut -f1)
        echo "Backed up ${server}: ${archive} (${size})"
    else
        echo "WARNING: world dir not found: ${world_path}"
    fi
done

# Prune backups older than 7 days
pruned=$(find "$BACKUP_DIR" -name '*.tar.gz' -mtime +7 -delete -print | wc -l)
echo "Pruned ${pruned} old backup(s)"

echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null || echo "  (none yet)"
echo ""
echo "Total backup size: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)"
