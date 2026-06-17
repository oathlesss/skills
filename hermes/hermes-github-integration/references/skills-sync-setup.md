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
git remote add origin https://github.com/oathlesss/hermes-skills.git
echo ".curator_state" >> .gitignore
echo ".usage.json" >> .gitignore
echo ".usage.json.lock" >> .gitignore
git add -A
git commit -m "Initial skills snapshot"
git push -u origin main
```

## Cron Job

Every 12 hours — commit any changes and push. Use a script (not inline shell) so it can be idempotent and lock-guarded:

```bash
#!/bin/bash
# ~/.hermes/scripts/sync-skills.sh
SKILLS_DIR="$HOME/.hermes/skills"
LOCKFILE="$HOME/.hermes/cron/.skills-sync.lock"

exec 9>"$LOCKFILE"
if ! flock -n 9; then
    exit 0  # another sync is running, skip silently
fi

cd "$SKILLS_DIR" || exit 1
git add -A
if git diff --cached --quiet; then
    exit 0  # nothing to commit
fi
git commit -m "auto: skills sync $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git push
```

Set the cron with `no_agent: true` (script-only, no LLM needed):

```
hermes cron create \
  --name "Skills Sync → GitHub" \
  --schedule "every 12h" \
  --script "sync-skills.sh" \
  --no-agent \
  --deliver "local"
```

## Pitfalls

- **PAT needs Administration scope** — `gh repo create` fails with `Resource not accessible by personal access token (createRepository)` without it. The FG-PAT scope table in the parent skill includes this.
- **Git config needed** — `user.email` and `user.name` must be set in the repo before first commit, or git will error.
- **Credential helper** — `gh auth setup-git` must run after `gh auth login`, otherwise push hangs on "could not read Username".
