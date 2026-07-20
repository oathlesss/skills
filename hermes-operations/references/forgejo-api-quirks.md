# Forgejo API Quirks (self-hosted Git)

Forgejo (Gitea fork) is GitHub API-compatible but has critical differences
that break common `gh` CLI workflows.

## Auth: `gh` CLI doesn't work → use curl + token

`gh auth login --hostname git.oathless.dev --with-token` stores the token
but `gh issue` commands still fail. The `gh` CLI is GitHub-specific.

**Working approach: use curl + Bearer token from `git credential fill`.**

```python
import subprocess, json

# Extract token (runs without reading .git-credentials file directly)
p = subprocess.run(['git', 'credential', 'fill'],
    input='protocol=https\nhost=git.oathless.dev\n',
    capture_output=True, text=True)
token = None
for line in p.stdout.strip().split('\n'):
    if line.startswith('password='):
        token = line.split('=',1)[1]

API = "https://git.oathless.dev/api/v1/repos/oathless"
HDR = ['-H', 'Authorization: token ' + token, '-H', 'Content-Type: application/json']

# All calls use curl:
subprocess.run(['curl', '-sk', '-X', 'GET'] + HDR[:2] + [API + '/repo/issues'],
    capture_output=True, text=True)
```

## Issue Creation: Labels MUST be numeric IDs

GitHub accepts label names as strings. Forgejo REJECTS them:

```
{"message":"[]: json: cannot unmarshal string into Go struct field CreateIssueOption.labels of type int64"}
```

**Fix: Create issues without labels, then apply labels afterward.**

```python
# Step 1: Create without labels
resp = api('POST', API + '/repo/issues', {"title": "...", "body": "..."})
issue_num = resp["number"]

# Step 2: Apply labels via dedicated endpoint
```

## Label Application: PUT /issues/{n}/labels, NOT PATCH /issues/{n}

GitHub's `gh issue edit --add-label` and `PATCH /repos/.../issues/{n}` both
work. Forgejo silently ignores the `labels` field on PATCH.

**Fix: Use the dedicated `PUT /repos/{owner}/{repo}/issues/{index}/labels` endpoint.**

```python
# Get label IDs
all_labels = api('GET', API + '/repo/labels')
name_to_id = {l['name']: l['id'] for l in all_labels}

# Apply labels
ids = [name_to_id[n] for n in ['epic', 'gameplay']]
api('PUT', API + '/repo/issues/%d/labels' % issue_num, {'labels': ids})
```

This REPLACES all labels on the issue (not additive). To append, read
current labels first, merge, then PUT.

## Complete Working Pattern

```python
def create_issue(repo, title, body):
    resp = api('POST', API + '/' + repo + '/issues', {"title": title, "body": body})
    return resp["number"]

def ensure_labels(repo, needed):
    existing = api('GET', API + '/' + repo + '/labels')
    name_to_id = {l['name']: l['id'] for l in existing}
    for name in needed:
        if name not in name_to_id:
            resp = api('POST', API + '/' + repo + '/labels', {
                "name": name, "color": "808080", "description": name
            })
            name_to_id[name] = resp["id"]
    return name_to_id

def set_labels(repo, issue_num, label_names):
    name_to_id = ensure_labels(repo, label_names)
    ids = [name_to_id[n] for n in label_names]
    api('PUT', API + '/' + repo + '/issues/%d/labels' % issue_num, {'labels': ids})

# Usage:
num = create_issue("my-repo", "Epic: Something", "## Goal\n...")
set_labels("my-repo", num, ["epic", "gameplay"])
```
