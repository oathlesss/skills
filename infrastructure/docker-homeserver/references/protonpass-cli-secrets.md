# ProtonPass CLI — Alternative to SOPS+age

ProtonPass offers a CLI (`pass-cli`) that can replace SOPS+age for managing Docker Compose secrets. This is a **pull-from-API** model (vs. SOPS's **decrypt-local** model).

## CLI

- **Repo:** [github.com/protonpass/pass-cli](https://github.com/protonpass/pass-cli)
- **License:** GPL-3.0 (since v2.1.2)
- **Docs:** [protonpass.github.io/pass-cli](https://protonpass.github.io/pass-cli)
- **Binary:** `pass-cli-linux-x86_64` from GitHub releases

Install:
```bash
curl -sL "https://github.com/protonpass/pass-cli/releases/latest/download/pass-cli-linux-x86_64" \
  -o ~/.local/bin/pass-cli
chmod +x ~/.local/bin/pass-cli
```

## Machine-to-Machine Auth

Two token types for scripted/agent access:

1. **Personal Access Tokens (PAT)** — For CI/CD, cron, deploy scripts, headless servers. Created in ProtonPass web settings. Scoped per-vault.
2. **AI Access Tokens** — Announced May 2026. Scoped tokens specifically for programmatic/agent access with restricted permissions.

The token must live on the server (env var or `chmod 600` file). `pass-cli` authenticates with it — no interactive login.

## Migration from SOPS+age

### Mapping 4 secrets files → ProtonPass items

| Current File | ProtonPass Item |
|---|---|
| `secrets/mc.env` → MC_RCON_PASSWORD=*** | Item: "homelab/minecraft" |
| `secrets/tailscale.env` → TS_AUTHKEY=*** | Item: "homelab/tailscale" |
| `secrets/zennotes.env` → ZENNOTES_AUTH_TOKEN=*** | Item: "homelab/zennotes" |
| `secrets/cf_api_key.txt` → raw key | Item: "homelab/curseforge" |

### deploy.sh rewrite (conceptual)

Current: `sops --decrypt secrets/mc.env.sops > secrets/mc.env`
New: `pass-cli item get "homelab/minecraft" --format env > secrets/mc.env`

The deploy loop changes from decrypting local `.sops` files to fetching from the ProtonPass API. Cleanup remains the same (delete plaintext after `docker compose up`).

### What gets removed

- `.sops.yaml`
- `secrets/*.sops` files (after verification)
- `sops` binary (optional)
- `~/.config/sops/age/keys.txt` (after one last backup)

## Trade-offs vs. SOPS+age

| Aspect | SOPS+age | ProtonPass CLI |
|---|---|---|
| Offline deploy | ✅ Works offline | ❌ Needs network |
| Git safety | ✅ Encrypted files committable | ✅ No secrets in repo at all |
| SPOF | Age key file (manual backup) | ProtonPass account + PAT (cloud-redundant) |
| Auth at deploy | Local key, no network | PAT on server (chmod 600) |
| Secret rotation | Edit file, re-encrypt, commit | Edit in ProtonPass UI, redeploy |
| Multi-machine | Copy age key | Same PAT works anywhere |
| Agent-friendly | ❌ Needs sops binary + key file | ✅ PAT designed for this |
| Dependency | sops + age binaries | pass-cli binary + network |

## Unknown (requires testing)

**Output format of `pass-cli item get`.** SOPS handles dotenv natively (`--input-type dotenv --output-type dotenv`). If `pass-cli` can output `KEY=VALUE` directly (or JSON trivially transformable), migration is a 1:1 `deploy.sh` change. If it only outputs structured JSON needing custom field-to-env-var mapping, a thin translation layer is needed.

**To test:** install `pass-cli`, create a dummy item with key=value fields, and inspect `pass-cli item get <item> --format json` output.
