#!/usr/bin/env bash
# deploy.sh — Decrypt secrets with SOPS + age, then deploy Docker Compose stack
#
# Usage:
#   ./deploy.sh              # Start all services
#   ./deploy.sh --always-on  # Start all including VPN profile
#   ./deploy.sh down         # Stop everything
#   ./deploy.sh restart mc   # Restart specific services
#
# Prerequisites:
#   - sops and age binaries in ~/.local/bin/
#   - age private key at ~/.config/sops/age/keys.txt
#   - .sops.yaml in project root
#   - Encrypted secrets in secrets/*.sops

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SOPS="${HOME}/.local/bin/sops"
SECRETS_DIR="${SCRIPT_DIR}/secrets"

# --- color helpers ---
red()    { echo -e "\033[31m$*\033[0m"; }
green()  { echo -e "\033[32m$*\033[0m"; }
yellow() { echo -e "\033[33m$*\033[0m"; }

# --- check prerequisites ---
if [[ ! -x "$SOPS" ]]; then
    red "ERROR: sops not found at $SOPS"
    echo "Install: download from https://github.com/getsops/sops/releases"
    exit 1
fi

if [[ ! -f "${HOME}/.config/sops/age/keys.txt" ]]; then
    red "ERROR: age key not found at ~/.config/sops/age/keys.txt"
    echo "Generate: age-keygen -o ~/.config/sops/age/keys.txt"
    exit 1
fi

# --- decrypt secrets ---
decrypt_secrets() {
    echo "→ Decrypting secrets..."
    local failed=0

    for sops_file in "$SECRETS_DIR"/*.sops; do
        [[ -f "$sops_file" ]] || continue
        local out_file="${sops_file%.sops}"

        if [[ "$sops_file" == *.txt.sops ]]; then
            # Plain text secrets (no dotenv wrapper)
            if "$SOPS" --decrypt "$sops_file" > "$out_file" 2>/dev/null; then
                chmod 600 "$out_file"
                green "  ✓ $(basename "$out_file")"
            else
                red "  ✗ Failed to decrypt $(basename "$sops_file")"
                failed=1
            fi
        else
            # Dotenv secrets
            if "$SOPS" --input-type dotenv --output-type dotenv --decrypt "$sops_file" > "$out_file" 2>/dev/null; then
                chmod 600 "$out_file"
                green "  ✓ $(basename "$out_file")"
            else
                red "  ✗ Failed to decrypt $(basename "$sops_file")"
                failed=1
            fi
        fi
    done

    return $failed
}

# --- cleanup decrypted files ---
cleanup_secrets() {
    for sops_file in "$SECRETS_DIR"/*.sops; do
        [[ -f "$sops_file" ]] || continue
        rm -f "${sops_file%.sops}"
    done
}

# --- main ---
COMPOSE_ARGS=()
ACTION="up"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --always-on)
            COMPOSE_ARGS+=(--profile always-on)
            shift
            ;;
        down|stop|restart|logs|ps)
            ACTION="$1"
            shift
            COMPOSE_ARGS+=("$@")
            break
            ;;
        *)
            COMPOSE_ARGS+=("$1")
            shift
            ;;
    esac
done

if [[ "$ACTION" == "up" ]]; then
    COMPOSE_ARGS+=("-d")

    if ! decrypt_secrets; then
        red "Secret decryption failed. Aborting."
        exit 1
    fi

    echo ""
    echo "→ Starting services..."
    docker compose up "${COMPOSE_ARGS[@]}"
    DOCKER_EXIT=$?

    cleanup_secrets

    if [[ $DOCKER_EXIT -eq 0 ]]; then
        green "✅ Deploy complete!"
    else
        red "❌ Deploy failed (exit code: $DOCKER_EXIT)"
        exit $DOCKER_EXIT
    fi
else
    docker compose "$ACTION" "${COMPOSE_ARGS[@]}"
fi
