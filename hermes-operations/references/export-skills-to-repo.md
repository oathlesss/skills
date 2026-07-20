# Exporting Hermes Skills to a GitHub Repo

Full-replacement workflow: reads all Hermes skills and writes them into a git repo,
overwriting whatever was there before.

## When to use

- Initial migration from another skill format (Claude, Codex, etc.)
- Bulk refresh after major skill changes across many skills
- The repo is the canonical public copy of your skills

## Workflow

### 1. Find or create the target repo

```bash
gh repo list oathlesss --json name,url --jq '.[] | select(.name=="skills")'
```

If it doesn't exist: `gh repo create skills --public --clone`

### 2. Clone to a temp location

```bash
cd /tmp && gh repo clone oathlesss/skills skills-repo
```

### 3. Read all skills

```python
# Use skills_list() to enumerate names, then skill_view(name) for each.
# Skills with linked_files need separate skill_view calls for each file.
```

### 4. Nuke and replace

```python
import os, shutil

repo = "/tmp/skills-repo"
for item in os.listdir(repo):
    if item == ".git":
        continue
    path = os.path.join(repo, item)
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
```

Then write each skill:

```
repo/
  skill-name/
    SKILL.md
    references/   (if any linked files)
    templates/    (if any linked files)
    scripts/      (if any linked files)
```

Use `execute_code` with `os.makedirs` + `open(…, 'w')` for bulk writes — avoids the overhead of individual `write_file` calls.

### 5. Configure git credential helper

HTTPS clones need `gh` as the credential helper for push:

```bash
git config --get credential.https://github.com.helper
# If empty or wrong:
gh auth setup-git
```

### 6. Commit and push

```bash
git add -A
git commit -m "Replace old skills with Hermes skills" --author="Diaktoros <rubenhesselink@pm.me>"
git push origin main
```

### 7. Clean up

```bash
rm -rf /tmp/skills-repo
```

## Pitfalls

- **HTTPS push auth fails** (`could not read Username`): run `gh auth setup-git` to wire up the credential helper.
- **Long skill content**: split writes across multiple `execute_code` calls if content approaches 50KB.
- **Commit author**: use `--author="Diaktoros <rubenhesselink@pm.me>"` for commits from Hermes.
