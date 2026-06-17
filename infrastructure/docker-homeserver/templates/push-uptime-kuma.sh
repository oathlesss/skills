#!/bin/bash
# Push a health heartbeat to Uptime Kuma push monitor
# Usage: ./push-uptime-kuma.sh
#
# Replace TOKEN and KUMA_URL with actual values.
# Replace the 'hermes gateway status' check with your actual health check command.
#
# This template is designed for Hermes no-agent cron jobs:
#   cronjob action=create schedule="every 1m" script="push-uptime-kuma.sh"
#         no_agent=true deliver=local
#
# IMPORTANT: cron interval must be ≤ half the Uptime Kuma monitor interval.
# If the monitor expects a heartbeat within 180s, run cron every 90s or faster.
# Matching them (e.g. both 120s) will cause false DOWN alerts from scheduler jitter.

KUMA_URL="https://status.oathless.dev"
PUSH_TOKEN="TOKEN"

if hermes gateway status &>/dev/null; then
    curl -sk "${KUMA_URL}/api/push/${PUSH_TOKEN}?status=up&msg=OK" &>/dev/null
else
    curl -sk "${KUMA_URL}/api/push/${PUSH_TOKEN}?status=down&msg=Service%20not%20running" &>/dev/null
fi
