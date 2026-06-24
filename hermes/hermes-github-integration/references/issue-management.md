# GitHub Issue Management via `gh` CLI

## Creating Labels

Labels must exist before attaching to issues. If they don't exist, `gh issue create --label` silently ignores them.

```bash
gh label create "phase-1" --color "d73a4a" --description "Prototype: movement + combat"
gh label create "critical" --color "b60205" --description "Go/No-Go blocker"
gh label create "ai-assisted" --color "C5DEF5" --description "AI-generated or AI-reviewed"
```

Check existing labels: `gh label list`

## Creating Structured Issues

Multi-line body via heredoc or quoted string:

```bash
gh issue create \
  --title "P1: Feature name (Week N)" \
  --label "phase-1,critical" \
  --body "## Goal
...
## Tasks
- [ ] Task one
- [ ] Task two
## Ref
\`DEVELOPMENT_PLAN.md\` §X.Y"
```

Labels must be comma-separated (no spaces after commas).

## Editing Issues

Add labels to existing issues:
```bash
gh issue edit 19 --add-label "critical"
```

Remove labels: `--remove-label`. Replace all: `--label "a,b,c"`.

## Pitfalls

- **Labels silently ignored on create:** If a label doesn't exist, `gh issue create --label "new-label"` creates the issue without it — no error. Create labels first, then create issues, or create issues first and add labels via `gh issue edit --add-label` (which DOES error on missing labels).
- **Commas in label args:** `--label "a, b"` (with space) doesn't work. Use `--label "a,b"`.
- **Body formatting:** GitHub-flavored Markdown works in issue bodies. Checkboxes (`- [ ]`) render as task lists. Backtick-quote file paths and code references.
- **Forgejo-specific:** Labels must be numeric IDs, not names. Create issues without labels, then use `PUT /repos/.../issues/{n}/labels` with `{"labels":[id1,id2]}`. See `references/forgejo-api-quirks.md` for full details.
