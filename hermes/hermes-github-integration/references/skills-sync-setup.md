# Skills Sync to GitHub — Setup Reference

## Pattern

Turn `~/.hermes/skills/` into a git repo and auto-push every 12 hours via cron. This gives skills version control, backup, and portability (the dossier calls this pattern "copy the skills dir to a new machine").

## .gitignore

The skills directory contains Hermes internal files that must NOT be committed:

```gitignore
# Hermes internal state — regenerated, not source
.curator_state
.usage.json
.usage.json.lock

# If you ever get these
__pycache__/
*.pyc
```

## Init Sequence

```bash
cd ~/.hermes/skills
git init
git config user.email "rubenhesselink@pm.me"
git config user.name "Diaktoros"
gh auth setup-git                           # wire credential helper
git remote add origin https://github.com/oathlesss/skills.git
echo ".curator_state" >> .gitignore
echo ".usage.json" >> .gitignore
echo ".usage.json.lock" >> .gitignore
git add -A
git commit -m "Initial skills snapshot"
git push -u origin main
```

## Cron Job

Every 12 hours — commit any changes and push. The canonical implementation lives at `~/.hermes/scripts/sync-skills.sh`. It is:

- **Idempotent** — file-locked via `flock` so overlapping cron invocations skip silently
- **Token-aware** — reads GH_TOKEN from `~/.hermes/config.yaml` via python3 (since `hermes config get` returns exit code 2 for set keys)
- **Change-only** — `git diff --cached --quiet` prevents empty commits
- **Self-contained** — no hardcoded paths beyond `$HOME/.hermes`

Open the live script for the exact implementation. The cron job was created with: `action='create', schedule='every 12h', prompt='Run the script', deliver='local'`.

## Pitfalls

- **PAT needs Administration scope** — `gh repo create` fails with `Resource not accessible by personal access token (createRepository)` without it. The FG-PAT scope table in the parent skill includes this.
- **Git config needed** — `user.email` and `user.name` must be set in the repo before first commit, or git will error.
- **Credential helper** — `gh auth setup-git` must run after `gh auth login`, otherwise push hangs on "could not read Username".
