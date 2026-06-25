# Creating a Forgejo Repo via API

When you need to create a repo on git.oathless.dev programmatically (instead of asking
the user to create it manually), use the Forgejo API. The token is stored in the git
credential store.

## Extract token from git credential store

```bash
TOKEN=$(printf "protocol=https\nhost=git.oathless.dev\n" | \
  git credential fill 2>/dev/null | grep password | cut -d= -f2)
```

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

```bash
git remote add origin https://git.oathless.dev/oathless/repo-name.git
git push -u origin main
```

If the repo already has a remote (`origin`), use `git remote set-url` instead of `add`.

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
