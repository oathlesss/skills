# Webhook Deploy Pipeline — Scripts & Receivers

Concrete implementations for the patterns in the parent skill's "Automated Deploy Pipeline" section.

## Deploy Script Template

```bash
#!/bin/bash
# Deploy <SERVICE> from latest main with health check + rollback.
# Called by webhook receiver on push to main.
set -euo pipefail

PROJECT_DIR="/home/ruben/<project>"
COMPOSE_FILE="/home/ruben/homeserver/docker-compose.yml"
SERVICE="<service-name>"
IMAGE="${SERVICE}:local"
ROLLBACK_IMAGE="${SERVICE}:rollback"
LOG_FILE="/home/ruben/homeserver/logs/deploy-${SERVICE}.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

# ── Pull ──
log "Pulling latest from origin/main..."
git -C "$PROJECT_DIR" pull origin main 2>&1 | tee -a "$LOG_FILE"

HEAD_BEFORE=$(git -C "$PROJECT_DIR" rev-parse HEAD)
HEAD_AFTER=$(git -C "$PROJECT_DIR" rev-parse @{u} 2>/dev/null || echo "$HEAD_BEFORE")
if [ "$HEAD_BEFORE" = "$HEAD_AFTER" ]; then
    log "No new commits — nothing to deploy."
    exit 0
fi

# ── Save rollback ──
log "Tagging current image as rollback..."
docker tag "$IMAGE" "$ROLLBACK_IMAGE" 2>/dev/null && log "  saved." || log "  no existing image (first deploy)."

# ── Build ──
log "Building $SERVICE..."
cd "$(dirname "$COMPOSE_FILE")"
if ! docker compose -f "$COMPOSE_FILE" build --no-cache "$SERVICE" 2>&1 | tee -a "$LOG_FILE"; then
    log "BUILD FAILED."
    exit 1
fi

# ── Deploy ──
log "Redeploying $SERVICE..."
docker compose -f "$COMPOSE_FILE" up -d "$SERVICE" 2>&1 | tee -a "$LOG_FILE"

# ── Health check (10 retries, 2s apart) ──
log "Health check..."
sleep 3
for i in $(seq 1 10); do
    if docker exec "$SERVICE" wget -q -O /dev/null http://localhost:8080 2>/dev/null; then
        log "PASSED (attempt $i)."
        docker rmi "$ROLLBACK_IMAGE" 2>/dev/null || true
        log "DEPLOY SUCCESSFUL."
        exit 0
    fi
    sleep 2
done

# ── Rollback ──
log "HEALTH CHECK FAILED. Rolling back..."
docker tag "$ROLLBACK_IMAGE" "$IMAGE"
docker compose -f "$COMPOSE_FILE" up -d "$SERVICE" 2>&1 | tee -a "$LOG_FILE"
log "ROLLBACK COMPLETE."
exit 1
```

Key decisions:
- `set -euo pipefail` — fail on any error, undefined var, or pipe failure
- `git pull` first, bail early if already up to date (no build wasted)
- `docker tag` for rollback: zero-cost snapshot, just a pointer
- `docker exec <service> wget` for health check: works on internal Docker networks without port mapping
- 10 retries × 2s = 20s total wait, enough for a Go binary to come up

## Webhook Receiver

```python
#!/usr/bin/env python3
"""
Webhook receiver for Forgejo → Docker Compose deployment.
Python stdlib only — zero dependencies.
"""
import hashlib, hmac, json, os, subprocess, sys
from http.server import HTTPServer, BaseHTTPRequestHandler

SECRET = os.environ.get("WEBHOOK_SECRET", "").encode()
DEPLOY_SCRIPT = os.environ.get("DEPLOY_SCRIPT", "/home/ruben/homeserver/deploy-service.sh")
PORT = int(os.environ.get("WEBHOOK_PORT", "9090"))
LOG_FILE = os.environ.get("LOG_FILE", "/home/ruben/homeserver/logs/webhook.log")


def log(msg: str) -> None:
    import datetime
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        cl = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(cl)

        # Verify HMAC
        sig = self.headers.get("X-Forgejo-Signature", "")
        if SECRET:
            expected = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                log(f"Signature mismatch from {self.client_address}")
                self.send_error(403, "Invalid signature")
                return

        event = self.headers.get("X-Forgejo-Event", "")
        if event != "push":
            self.send_response(200); self.end_headers()
            self.wfile.write(b"OK (not a push)")
            return

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        ref = payload.get("ref", "")
        if ref != "refs/heads/main":
            self.send_response(200); self.end_headers()
            self.wfile.write(b"OK (not main)")
            return

        pusher = payload.get("pusher", {}).get("login", "unknown")
        repo = payload.get("repository", {}).get("full_name", "unknown")
        log(f"Push to main by {pusher} on {repo} — triggering deploy...")

        try:
            result = subprocess.run([DEPLOY_SCRIPT], capture_output=True, text=True, timeout=300)
            log(result.stdout.rstrip())
            if result.returncode != 0:
                log(f"DEPLOY FAILED:\n{result.stderr}")
                self.send_error(500, "Deploy failed")
            else:
                self.send_response(200); self.end_headers()
                self.wfile.write(b"Deployed!")
        except subprocess.TimeoutExpired:
            log("Deploy timed out (300s)")
            self.send_error(504, "Timed out")
        except Exception as e:
            log(f"Error: {e}")
            self.send_error(500, str(e))

    def do_GET(self) -> None:
        self.send_response(200); self.end_headers()
        self.wfile.write(b"webhook receiver OK\n")

    def log_message(self, format, *args):
        pass  # use our own log() instead of stderr


def main():
    log(f"Starting webhook receiver on :{PORT}")
    HTTPServer(("0.0.0.0", PORT), WebhookHandler).serve_forever()


if __name__ == "__main__":
    main()
```

## Systemd User Service

```ini
# ~/.config/systemd/user/webhook-receiver.service
[Unit]
Description=<Service Name> Webhook Receiver
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/ruben/homeserver/webhook-receiver.py
Restart=always
RestartSec=10
EnvironmentFile=/home/ruben/homeserver/webhook.env

[Install]
WantedBy=default.target
```

Environment file (`/home/ruben/homeserver/webhook.env`, chmod 600):
```
WEBHOOK_SECRET=<openssl rand -hex 32>
WEBHOOK_PORT=9090
DEPLOY_SCRIPT=/home/ruben/homeserver/deploy-<service>.sh
LOG_FILE=/home/ruben/homeserver/logs/webhook.log
```

Enable and start:
```bash
systemctl --user daemon-reload
systemctl --user enable --now webhook-receiver.service
```

## Forgejo Webhook Config

In the Forgejo repo: Settings → Webhooks → Add Webhook → Forgejo:
- **Target URL**: `http://<docker-gateway>:9090/` (e.g. `http://172.18.0.1:9090/`)
- **HTTP Method**: POST
- **Secret**: same as `WEBHOOK_SECRET`
- **Trigger On**: Push events
- **Active**: ✓

## Testing the Webhook

```bash
# Verify receiver is listening
curl -s http://localhost:9090/

# Test with a signed push payload
SECRET=$(grep WEBHOOK_SECRET /home/ruben/homeserver/webhook.env | cut -d= -f2)
BODY='{"ref":"refs/heads/main","pusher":{"login":"test"},"repository":{"full_name":"owner/repo"}}'
SIG=$(python3 -c "import hmac,hashlib; print(hmac.new('$SECRET'.encode(), '$BODY'.encode(), hashlib.sha256).hexdigest())")
curl -s -X POST http://localhost:9090/ \
  -H "Content-Type: application/json" \
  -H "X-Forgejo-Event: push" \
  -H "X-Forgejo-Signature: $SIG" \
  -d "$BODY"
# Should return: Deployed! (or "No new commits" if already up to date)
```

## Why This Over Alternatives

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Forgejo Actions + runner** | Integrated CI, build status in commits | Another container, registration token dance, Docker-in-Docker complexity | Overkill for single-service deploys |
| **Webhook receiver** (chosen) | Zero extra containers, transparent, stdlib-only Python | No per-commit status in Forgejo UI | Right size for homelab |
| **Cron polling** | Simplest to set up | Polling delay, waste, not event-driven | Feels hacky |
| **Kubernetes** | — | OptiPlex micro, single service | No |
