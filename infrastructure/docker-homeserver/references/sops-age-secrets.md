# SOPS + Age: Encrypted Secrets for Docker Compose

Full recipe for migrating a monolithic `.env` to per-service SOPS-encrypted files with age — encryption at rest, per-container isolation, git-safety, and no new services.

## When to Use

- You have secrets (API keys, passwords, tokens) in a shared `.env` file
- You want secrets encrypted at rest (safe to commit)
- You want per-service isolation (container A can't read container B's secrets)
- Pragmatic: no Vault, no Infisical, no cloud dependency

## Architecture

```
homeserver/
├── .sops.yaml              # SOPS encryption config (age public key)
├── .env.example            # Documents required secrets (committable)
├── .gitignore              # Blocks plaintext, allows *.sops
├── deploy.sh               # Decrypt → deploy → cleanup
├── docker-compose.yml      # Uses per-service env_file: (no ${VAR} substitution)
└── secrets/
    ├── mc.env.sops         # MC_RCON_PASSWORD=***
    ├── zennotes.env.sops   # ZENNOTES_AUTH_TOKEN=***
    └── tailscale.env.sops  # TAILSCALE_AUTHKEY=***
```

## Step-by-Step Setup

### 1. Install SOPS and age

Download static binaries (no sudo, no go toolchain):

```bash
# age
curl -sL "https://github.com/FiloSottile/age/releases/download/v1.3.1/age-v1.3.1-linux-amd64.tar.gz" -o /tmp/age.tar.gz
tar -xzf /tmp/age.tar.gz -C /tmp/
cp /tmp/age/age /tmp/age/age-keygen ~/.local/bin/

# sops
curl -sL "https://github.com/getsops/sops/releases/download/v3.13.1/sops-v3.13.1.linux.amd64" -o ~/.local/bin/sops
chmod +x ~/.local/bin/sops
```

### 2. Generate age keypair

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
```

Back up `~/.config/sops/age/keys.txt` immediately — without it, all secrets are permanently inaccessible.

### 3. Create .sops.yaml in project root

```yaml
creation_rules:
  - path_regex: secrets/.*
    age: age1...your-public-key...
```

SOPS auto-discovers the private key from `~/.config/sops/age/keys.txt`.

### 4. Create per-service .env files (plaintext)

```bash
mkdir -p secrets
echo "MC_RCON_PASSWORD=*** > secrets/mc.env
echo "ZENNOTES_AUTH_TOKEN=*** > secrets/zennotes.env
echo "TAILSCALE_AUTHKEY=*** > secrets/tailscale.env
chmod 600 secrets/*.env
```

### 5. Encrypt with SOPS

**⚠️ CRITICAL: Use `--input-type dotenv --output-type dotenv`.** SOPS defaults to JSON/YAML. Without the type flag, decryption fails with "invalid character 'M' looking for beginning of value" because it tries to parse the env content as JSON.

```bash
for f in secrets/*.env; do
    sops --input-type dotenv --output-type dotenv --encrypt "$f" > "${f}.sops"
done
```

### 6. Remove plaintext files

```bash
rm secrets/*.env    # only .sops remains
```

### 7. Update docker-compose.yml

Replace `${VAR}` references with per-service `env_file:`:

```yaml
services:
  minecraft-vanilla:
    env_file:
      - ./secrets/mc.env
    environment:
      RCON_PASSWORD: ${MC_RCON_PASSWORD}  # from env_file
      # ... other non-secret env vars
```

The `env_file:` directive loads key=value pairs into the container's environment. Each service only sees the env file(s) listed in its `env_file:` block.

### 8. Create .env.example

Documents required secrets without values (safe to commit):

```
# MC_RCON_PASSWORD=<see secrets/mc.env.sops>
# ZENNOTES_AUTH_TOKEN=<see secrets/zennotes.env.sops>
# TAILSCALE_AUTHKEY=<see secrets/tailscale.env.sops>
```

### 9. Create .gitignore

```
# Secrets — keep encrypted .sops files, ignore plaintext
secrets/*.env
!secrets/*.env.sops
.env
```

### 10. Create deploy.sh

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
SOPS="${HOME}/.local/bin/sops"

# Decrypt secrets
for sops_file in secrets/*.sops; do
    env_file="${sops_file%.sops}"
    "$SOPS" --input-type dotenv --output-type dotenv --decrypt "$sops_file" > "$env_file"
    chmod 600 "$env_file"
done

# Deploy
docker compose up -d "$@"

# Cleanup plaintext immediately
rm -f secrets/*.env
```

## Day-to-Day Operations

### Deploy
```bash
./deploy.sh              # all services
./deploy.sh --always-on  # include Tailscale
```

### Add a new secret
```bash
echo "NEW_VAR=*** > secrets/new.env
sops --input-type dotenv --output-type dotenv --encrypt secrets/new.env > secrets/new.env.sops
rm secrets/new.env
# Add env_file: - ./secrets/new.env to the service in docker-compose.yml
```

### Update an existing secret
```bash
sops --input-type dotenv --output-type dotenv --decrypt secrets/mc.env.sops > secrets/mc.env
# Edit secrets/mc.env
sops --input-type dotenv --output-type dotenv --encrypt secrets/mc.env > secrets/mc.env.sops
rm secrets/mc.env
```

### Rotate the age key (key compromised or lost)
```bash
age-keygen -o ~/.config/sops/age/keys.txt.new
# Add the new public key to .sops.yaml rotation list
sops updatekeys secrets/*.sops
```

## Verification Checklist

After setup, run through these checks systematically (V1 through V6):

| # | Check | How | Passing |
|---|---|---|---|
| V1 | SOPS decrypts all files | `sops --input-type dotenv --output-type dotenv --decrypt secrets/*.sops | grep -c "="` | ≥1 line per file |
| V2 | No plaintext on disk | `ls secrets/ | grep -v '.sops$'` | Empty |
| V3 | .sops files in git | `git ls-files secrets/` | All .sops files listed |
| V4 | Decrypt cycle works | Decrypt all → verify each has ≥1 variable → cleanup | No errors |
| V5 | Compose config resolves secrets | Decrypt → `docker compose config | grep -c "MC_RCON_PASSWORD:"` | Secrets resolved (not `${VAR}` literals) |
| V6 | Live deploy | `./deploy.sh` against running stack | Only services with changed secrets restart; all become healthy |

**⚠️ IMPORTANT: Clean up decrypted files between V5 and V6.** `docker compose config` dumps resolved secrets to stdout. Always `rm secrets/*.env` immediately after config validation.

**⚠️ V5 tip:** Use `grep -c` to verify secret resolution without exposing values. Hermes' output filter may redact the actual values — counting lines proves the variables are present without needing to see their content.

### ❌ SOPS without --input-type dotenv
SOPS encrypts the file but cannot decrypt it. The error "invalid character 'M' looking for beginning of value" means it tried to parse the dotenv content as JSON/YAML. **Always** use `--input-type dotenv --output-type dotenv` for .env files.

### ❌ docker compose config leaks secrets
Running `docker compose config` with decrypted env files present **prints all resolved secrets** to stdout. Always clean up decrypted files first, or only run config validation in a controlled environment.

### ❌ Age key not backed up
The age private key in `~/.config/sops/age/keys.txt` is the **only** way to decrypt secrets. Lost key = lost secrets. Back up immediately after generation.

### ❌ env_file with variable substitution
Docker Compose supports `${VAR}` in `env_file:` paths only if the variable is defined in a `.env` file or shell environment. Hardcode paths (`./secrets/mc.env`) to avoid chicken-and-egg problems.

### ❌ Per-service env_file with same variable in environment block
If a variable appears in both `env_file:` and `environment:`, the `environment:` value wins. Use one or the other — don't split secret vars between both.

### ❌ Hermes output filter redacts secret values
When verifying decryption or checking resolved config via Hermes' terminal tool, values matching secret patterns (passwords, tokens) are replaced with `***` in the output. Don't trust what you see — verify with line counts (`grep -c`, `wc -l`), length checks (`wc -c`), or hex dumps (`xxd`). A value that appears to contain literal `...` in terminal output may be the actual content or may be filter redaction. Use byte-level tools to confirm.

## Migration from Monolithic .env

The `templates/migrate-secrets.py` script handles:
1. Reading the old `.env`
2. Creating per-service `.env` files
3. Encrypting each with SOPS
4. Generating `.env.example`
5. Cleaning up plaintext

Run once, commit the `.sops` files, delete the script.

## Comparison with Alternatives

| Approach | Encrypted at rest | Per-service isolation | Git-safe | Complexity | New services |
|---|---|---|---|---|---|
| Single .env | ❌ | ❌ | ❌ | Lowest | 0 |
| Compose `secrets:` | ❌ | ✅ | ❌ | Low | 0 |
| **SOPS + age** | ✅ | ✅ | ✅ | Low-Med | 0 |
| Bitwarden CLI | ✅ | ⚠️ (scripting) | N/A | Medium | 0 (external) |
| Infisical | ✅ | ✅ | N/A | Med-High | 3 (PG+Redis+Inf) |
| Vault | ✅ | ✅ | N/A | Very High | 1+ (unseal pain) |

SOPS + age is the pragmatic sweet spot for single-machine Docker Compose homeservers: encryption at rest, per-container isolation, git-safety, and zero new services.
