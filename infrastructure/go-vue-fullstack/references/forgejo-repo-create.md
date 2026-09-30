# Creating a Forgejo Repo via API

When you need to create a repo on git.oathless.dev programmatically (instead of asking
the user to create it manually), use the Forgejo API. The token is stored in the git
credential store.

## Extract token from git credential store

```bash
TOKEN=$(echo -e "protocol=https\nhost=git.oathless.dev\n\n" | \
  git credential fill 2>/dev/null | sed -n 's/^password=//p')
```

⚠️ **Use `echo -e`, NOT `printf`, inside the `$(...)` substitution.** The terminal tool's `***` security redaction mangles the `printf "protocol=…"` string — it substitutes the whole `$(printf …` prefix with `***`, which corrupts the command to `TOKEN=*** "protocol=…" | … )` (a bash syntax error). This happens even inside `write_file` content: the file on disk ends up with `TOKEN=*** "protocol=…"` instead of `TOKEN=$(printf …)`. `echo -e` avoids the trigger string entirely and survives redaction. Always verify the written script with `read_file` if the token line looks suspicious.

## Create repo

```bash
REPO="repo-name"
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"$REPO\",\"description\":\"Short description.\",\"private\":true}" \
  https://git.oathless.dev/api/v1/user/repos
```

HTTP 201 = created. HTTP 409 = already exists.

### ⚠️ Verify visibility after creation

Forgejo may default new repos to public despite the `"private":true` flag (instance defaults can override). Always verify and flip if needed:

```bash
VIS=$(curl -sf -H "Authorization: token $TOKEN" \
  "https://git.oathless.dev/api/v1/repos/oathless/$REPO" | jq -r .private)

if [ "$VIS" != "true" ]; then
  echo "Repo was public — flipping to private"
  curl -sf -X PATCH \
    -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"private":true}' \
    "https://git.oathless.dev/api/v1/repos/oathless/$REPO" | jq '{full_name, private}'
fi
```

## Push

Ruben's projects use the remote name **`forgejo`** (NOT `origin`) — e.g. the
`oathless-terminal` repo has remote `forgejo`. Match that convention:

```bash
# NOTE: existing repos on this instance use the remote name `forgejo` (NOT `origin`).
# Auto-detect the convention so you match it:
REMOTE=$(git remote | head -1); [ -z "$REMOTE" ] && REMOTE=forgejo
git remote add "$REMOTE" https://git.oathless.dev/oathless/repo-name.git
git push -u "$REMOTE" main
```

To auto-match an existing project's remote name:
`git -C ~/<existing-project> remote | head -1`

If a remote already exists, use `git remote set-url` instead of `add`.

Auth header: use `Authorization: token $TOKEN` (Forgejo/Gitea style). `Bearer`
also works but `token` is the documented form — pick one and stay consistent.

## ⚠️ PITFALL: Token redaction breaks multi-call patterns

The terminal tool's `***` security redaction interferes with token extraction across separate `terminal()` calls. A token saved to a temp file in one call may be empty/redacted when read in the next call. **Always chain extraction and use in a single terminal invocation:**

```bash
# RIGHT — extract, use, cleanup all in one call
echo -e "protocol=https\nhost=git.oathless.dev\n" | git credential fill | grep '^password=' | cut -d= -f2- > /tmp/forgejo_token && \
chmod 600 /tmp/forgejo_token && \
curl -sf -H "Authorization: Bearer $(cat /tmp/forgejo_token)" "https://git.oathless.dev/api/v1/repos/oathless/$REPO" && \
rm -f /tmp/forgejo_token
```

Do NOT split extraction and usage across separate `terminal()` calls — the redaction will substitute the token reference with `***` and the API call will fail with `"token is required"`.

## Common gotchas

- The user is always `oathless` on this Forgejo instance.
- "Push to create" is disabled — you must create the repo first, then push.
- If `git credential fill` returns nothing, check that `~/.git-credentials` has an entry for `git.oathless.dev`.
- The repo URL pattern is always `https://git.oathless.dev/oathless/<repo-name>.git`.
- Token redaction: chain extraction + API call in one `terminal()` invocation (see pitfall above).
- **`git init` defaults to `master`, not `main`** — this box's git has no `init.defaultBranch` set. A `git push -u <remote> main` right after `git init` fails with `src refspec main does not match any`. Fix: `git init -b main` (or `git branch -m main` before the first push). Always confirm the branch name with `git branch --show-current` before pushing.
- **Redaction mangles `$(printf ...)` inside `write_file` content too** — not just `terminal` commands. This session saw the same `$(printf "protocol=...")` line land correct on disk on one write and get corrupted to `TOKEN=*** "protocol=..."` on the next (a bash syntax error on execution). Safest pattern: use `echo -e` (not `printf`) in the credential invocation, write the create/verify script to a file, run it, then `rm` it. `read_file` the script back before running if the job is multi-step.
- **Large binaries are committed directly to git, no LFS.** `git-lfs` is not installed locally; the established convention on this instance is direct commit (the resourcepack repo holds a 126MB zip, the modpack repo a 958MB zip). For multi-hundred-MB pushes, set `git config http.postBuffer 524288000` first to avoid HTTP buffering stalls.
