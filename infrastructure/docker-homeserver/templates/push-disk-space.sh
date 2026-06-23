#!/bin/bash
# Push disk usage to Uptime Kuma push monitor — alerts if >80%
# Usage: create a Uptime Kuma push monitor first, get its token, paste below,
# then create a Hermes no-agent cron:
#   cronjob action=create no_agent=true schedule="every 1m" script="push-disk-space.sh" deliver=local
set -euo pipefail

THRESHOLD=80
PUSH_TOKEN="REPLACE_WITH_20_CHAR_TOKEN"
PUSH_URL="https://status.oathless.dev/api/push/${PUSH_TOKEN}"

usage=$(df / | awk 'NR==2 {print $5}' | tr -d '%')

if [ "$usage" -gt "$THRESHOLD" ]; then
    curl -sk "${PUSH_URL}?status=down&msg=Disk+${usage}%25+used+(threshold+${THRESHOLD}%25)&ping=" &>/dev/null
else
    curl -sk "${PUSH_URL}?status=up&msg=${usage}%25+used&ping=" &>/dev/null
fi
