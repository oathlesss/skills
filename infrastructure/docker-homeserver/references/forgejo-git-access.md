# Forgejo Git Access — SSH vs HTTPS

Forgejo in the Docker Compose stack serves the web UI through Caddy (HTTPS) but SSH access for `git push/pull` requires explicit setup.

## Diagnosis

```bash
# Check if Forgejo SSH is accessible from host
ssh -o ConnectTimeout=5 -T git@git.oathless.dev 2>&1

# Check if SSH is running inside the container
docker exec forgejo netstat -tlnp | grep :22
# → tcp  0.0.0.0:22  ...  LISTEN  17/sshd

# Check host port mappings
docker inspect forgejo --format '{{json .NetworkSettings.Ports}}' | python3 -m json.tool
# → null or empty → no ports exposed
```

Result: SSH runs inside Forgejo but has no host mapping. `git@git.oathless.dev:22` times out because host port 22 either belongs to the host sshd or is unused — neither reaches Forgejo.

## Option A: SSH (port mapping + key)

### 1. Expose Forgejo SSH port

In `docker-compose.yml`:

```yaml
forgejo:
  ports:
    - "2222:22"      # host 2222 → container 22
```

Restart: `docker compose up -d forgejo`

**Verify the port is listening after restart:**

```bash
# Should show port 2222 bound to all interfaces
ss -tlnp | grep 2222
# → LISTEN 0.0.0.0:2222

# Docker should show the mapping
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep forgejo
# → forgejo  3000/tcp, 0.0.0.0:2222->22/tcp, [::]:2222->22/tcp
```

### 2. Generate SSH key on the pushing machine

```bash
ssh-keygen -t ed25519 -C "description" -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
```

### 3. Add public key to Forgejo

Forgejo web UI → Settings → SSH/GPG Keys → Add Key → paste public key.

### 4. Configure ~/.ssh/config

```
Host git.oathless.dev
    Port 2222
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

### 5. Test

```bash
ssh -T git@git.oathless.dev
# → "Hi there, username! You've successfully authenticated..."
```

**⚠️ PITFALL: Router port forwarding for external clients.** The port mapping (`2222:22`) in docker-compose makes the port available on the host machine only. When cloning or pushing from a device outside the local network (e.g. a laptop via the internet, even over Tailscale), the router must forward port 2222 to the homelab's LAN IP. If the router doesn't forward 2222, external SSH connections will time out — the port is listening on the host but unreachable from the WAN or tailnet. Use the same router port-forwarding mechanism as Minecraft (25565) — just forward port 2222 to the same internal IP.

### 6. Use SSH remote

```bash
git remote add origin git@git.oathless.dev:username/repo.git
```

## Option B: HTTPS with token (no compose change)

### 1. Generate access token

Forgejo web UI → Settings → Applications → Generate Token
- Token name: e.g. "hermes"
- Scope: `write:repository` (read + write)

### 2. Determine your Forgejo username

```bash
curl -s https://git.oathless.dev/api/v1/users/search | python3 -m json.tool
# Look for "login" / "username" in the output
```

### 3. Configure git credential store

```bash
git config --global credential.https://git.oathless.dev.helper store
```

Then write to `~/.git-credentials`:

```
https://USERNAME:TOKEN@git.oathless.dev
```

Example: `https://oathless:abc123...@git.oathless.dev`

### 4. Verify the credential works

Use `git credential fill` — this exercises the credential helper chain and shows what git will use:

```bash
echo -e "protocol=https\nhost=git.oathless.dev\n" | git credential fill
# Should return username and password (the token)
```

### 5. Use HTTPS remote

```bash
git remote add origin https://git.oathless.dev/USERNAME/repo.git
```

### 6. End-to-end push test

Create a temporary test repo, push, then delete (all via API — no browser needed):

```bash
# Create test repo
curl -s -X POST \
  -H "Authorization: token TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"credential-test","private":true,"auto_init":false}' \
  https://git.oathless.dev/api/v1/user/repos

# Push to it
cd /tmp && mkdir test-push && cd test-push && git init
echo "test" > README.md && git add README.md && git commit -m "test"
git remote add origin https://git.oathless.dev/USERNAME/credential-test.git
# ⚠️ If local branch is "master" and remote expects "main":
git branch -m master main
git push -u origin main

# Clean up
rm -rf /tmp/test-push
curl -s -X DELETE \
  -H "Authorization: token TOKEN" \
  https://git.oathless.dev/api/v1/repos/USERNAME/credential-test
```

## Comparison

| | SSH | HTTPS + token |
|---|---|---|
| Compose change | Yes (port mapping) | No |
| Key/token management | One key per machine | One token (shared or per-use) |
| Token in URLs/logs | Never | Possible if not careful |
| Expiry | Never (rotate manually) | Never by default in Forgejo |
| Setup complexity | Slightly higher | Lower |

For a single machine, they're equivalent in practice. SSH is marginally cleaner for multi-repo usage since the key works ambiently for all repos without per-repo credential config.

## Verification Patterns

### `git credential fill` — the reliable credential check

This exercises the full credential helper chain and returns what git will actually use for auth:

```bash
echo -e "protocol=https\nhost=git.oathless.dev\n" | git credential fill
# Returns: username=xxx, password=xxx
```

This is more reliable than `curl` testing because it exercises the exact same path `git push` uses — credential helper, store format, encoding.

### Branch name mismatch (master vs main)

Older git installs default to `master` for the initial branch. Forgejo defaults to `main`. When pushing:

```bash
# Error: src refspec main does not match any
# Fix: rename the local branch
git branch -m master main
git push -u origin main
```

## Batch Pushing Existing Repos to Forgejo

When migrating repos from another forge (GitHub) or promoting local-only repos to Forgejo, follow this sequence:

### 1. Discover all repos on the machine

```bash
find /home/ruben -name '.git' -type d 2>/dev/null | \
  grep -v '/\.cargo/' | grep -v '/\.local/' | grep -v '/cache/' | \
  grep -v '/homeserver/' | grep -v '/snap/' | grep -v '/node_modules'
```

### 2. Skips-based filtering

Not every `.git` directory is a project to push:
- Reference/source repos cloned from other people's GitHub (e.g., TC6 source, Thavma reference) — skip
- The Hermes skills directory (`.hermes/skills/.git`) — skip
- Anything under `~/.local/share/`, `~/.cargo/`, `~/.cache/` — skip

### 3. Check existing remotes

```bash
for repo in /path/to/repo1 /path/to/repo2; do
  echo "=== $(basename $repo) ===" && git -C "$repo" remote -v
done
```

This tells you whether a repo has:
- **No remotes** (local only) → Forgejo should become `origin`
- **A GitHub remote** → Forgejo should be added as `forgejo` (alongside)

### 4. Create repos on Forgejo via API

```bash
token=$(echo -e "protocol=https\nhost=git.oathless.dev\n" | git credential fill 2>/dev/null | grep '^password=' | cut -d= -f2)

for repo in thaumcraft oathless-terminal project-arachne; do
  curl -s -X POST \
    -H "Authorization: token $token" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$repo\",\"private\":true,\"auto_init\":false}" \
    "https://git.oathless.dev/api/v1/user/repos" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  {d.get(\"full_name\",\"ERROR\")} - {d.get(\"html_url\",\"\")}')"
done
```

### 5. Add remotes and push — handle both scenarios

**Repos with NO existing remote (local only):** Set Forgejo as `origin`:
```bash
git -C /path/to/repo remote add origin https://git.oathless.dev/oathless/repo.git
git -C /path/to/repo push --all origin
git -C /path/to/repo push --tags origin
```

**Repos with existing GitHub `origin`:** Add Forgejo as a second remote named `forgejo`:
```bash
git -C /path/to/repo remote add forgejo https://git.oathless.dev/oathless/repo.git
git -C /path/to/repo push --all forgejo
git -C /path/to/repo push --tags forgejo
```

**⚠️ PITFALL: `git push --all` does not push tags.** Run `git push --tags <remote>` separately after `--all`.

### 6. Verify

```bash
git -C /path/to/repo ls-remote --heads <remote>
```

### Common pitfalls

**PITFALL: `master` vs `main` mismatch.** Older git installs default to `master`; Forgejo defaults to `main`. If `git push` fails with "src refspec main does not match any", rename the local branch first:
```bash
git -C /path/to/repo branch -m master main
```

**PITFALL: Working directory corruption from `rm -rf` while `cd`'d into it.** After creating/deleting test repos with `cd /tmp/test && ... && rm -rf /tmp/test`, the shell's CWD is destroyed. Next `terminal()` call fails with "No such file or directory". Always `cd /home/ruben` before subsequent shell commands, or use `workdir=` parameter on `terminal()` calls after cleanup operations.

## Forgejo API Quirks

### Auth header format

Forgejo uses `Authorization: token <token>`, **not** `Authorization: Bearer <token>`:

```bash
# CORRECT
curl -H "Authorization: token abc123..." https://git.oathless.dev/api/v1/user

# WRONG — returns "token is required"
curl -H "Authorization: Bearer abc123..." https://git.oathless.dev/api/v1/user
```

This differs from GitHub (which accepts both `token` and `Bearer` prefixes).

### Repository operations via API

Forgejo exposes a REST API compatible with Gitea's. Key endpoints:

```bash
# List user repos
curl -s -H "Authorization: token TOKEN" https://git.oathless.dev/api/v1/user/repos

# Create repo
curl -s -X POST \
  -H "Authorization: token TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"repo-name","private":true}' \
  https://git.oathless.dev/api/v1/user/repos

# Delete repo (returns 204 on success)
curl -s -X DELETE \
  -H "Authorization: token TOKEN" \
  -w "\nHTTP %{http_code}" \
  https://git.oathless.dev/api/v1/repos/USERNAME/repo-name

# Search users (to find your own username)
curl -s https://git.oathless.dev/api/v1/users/search
```
