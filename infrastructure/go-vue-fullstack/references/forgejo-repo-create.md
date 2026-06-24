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
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"repo-name","description":"Short description.","private":false}' \
  https://git.oathless.dev/api/v1/user/repos
```

HTTP 201 = created. HTTP 409 = already exists.

## Push

```bash
git remote add origin https://git.oathless.dev/oathless/repo-name.git
git push -u origin main
```

If the repo already has a remote (`origin`), use `git remote set-url` instead of `add`.

## Common gotchas

- The user is always `oathless` on this Forgejo instance.
- "Push to create" is disabled — you must create the repo first, then push.
- If `git credential fill` returns nothing, check that `~/.git-credentials` has an entry for `git.oathless.dev`.
- The repo URL pattern is always `https://git.oathless.dev/oathless/<repo-name>.git`.
