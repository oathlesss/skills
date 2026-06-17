# GitHub Integration for Hermes

Fine-grained PAT + `gh` CLI — full read/write to personal repos while blocking work org access.

## Token Creation

Go to https://github.com/settings/personal-access-tokens/new

- **Resource owner:** personal account (not an org)
- **Repository access:** All repositories (enables `gh repo create`, etc.)
- **Permissions (Repository):**
  - `Contents` → Read and write
  - `Issues` → Read and write
  - `Pull requests` → Read and write
  - `Metadata` → Read (auto-selected, mandatory)
- **Permissions (Organization):** grant NOTHING — leave every org permission unchecked

### Why "All repositories" + zero org perms is safe

Fine-grained PATs can only access org repos if the **org has explicitly enabled** fine-grained PATs in org settings → "Personal access tokens." Most work orgs keep this off or restricted. The org itself acts as a firewall — the token literally cannot cross the boundary even with "All repositories" selected.

## Installing `gh` CLI

If sudo isn't available, use the no-sudo host install pattern from the main skill:

```bash
curl -fsSL "https://github.com/cli/cli/releases/download/v2.82.0/gh_2.82.0_linux_amd64.tar.gz" -o /tmp/gh.tar.gz
tar -xzf /tmp/gh.tar.gz -C /tmp
mkdir -p ~/.local/bin
cp /tmp/gh_2.82.0_linux_amd64/bin/gh ~/.local/bin/gh
gh --version
rm -rf /tmp/gh.tar.gz /tmp/gh_2.82.0_linux_amd64
```

## Auth

```bash
echo "YOUR_TOKEN" | gh auth login --with-token
```

Or set `GH_TOKEN` / `GITHUB_TOKEN` in `~/.hermes/.env` for Hermes to pick up.

## Org Isolation Verification

After auth, verify work orgs are blocked:

```bash
# Should 403 if the org blocks fine-grained PATs
gh api /orgs/<work-org-name>/repos
```

If it returns data, the org allows fine-grained PATs — fall back to "Only select repositories" in token settings (lose `gh repo create`, but gain guaranteed isolation).

## Notification Polling (Cron)

Poll GitHub notifications every few minutes and surface new ones to Discord:

```bash
# Create a cron job that runs gh notifications and formats output
cronjob action=create schedule="every 3m" prompt="Run 'gh notifications --json repository,subject,reason,updatedAt' and format new/interesting notifications for the user. Skip stale ones older than 24h." enabled_toolsets=["terminal"]
```

## Common Operations

```bash
gh issue list --repo owner/repo          # list issues
gh issue view 42 --repo owner/repo       # view issue details
gh pr list --repo owner/repo             # list PRs
gh pr view 42 --repo owner/repo          # view PR details
gh search repos "topic" --owner owner    # search repos
gh notifications                        # list unread notifications
gh repo create owner/new-repo --public   # create a repo
```
