# Modrinth API — Modpack Research

Use the Modrinth v2 API to find modpacks by mod combination, resolve dependency lists, and cross-reference mods across packs. No auth required for read-only endpoints.

## Search for modpacks by keyword

```bash
curl -s "https://api.modrinth.com/v2/search?query=Ars+Nouveau+Create&facets=%5B%5B%22project_type%3Amodpack%22%5D%5D&limit=20" \
  | python3 -c "import json,sys; [print(f'{h[\"title\"]} | {h[\"versions\"]} | DLs: {h[\"downloads\"]} | {h[\"slug\"]}') for h in json.load(sys.stdin).get('hits',[])]"
```

Key facets:
- `[["project_type:modpack"]]` — modpacks only
- `[["project_type:mod"]]` — individual mods only
- `[["categories:forge"],["project_type:modpack"]]` — AND logic (Forge + modpack)
- Add `&offset=20` for pagination

## Fetch a pack's dependencies (mod list)

```bash
# Get the dependency IDs from the latest version
curl -s "https://api.modrinth.com/v2/project/<slug>/version" \
  | python3 -c "
import json, sys
versions = json.load(sys.stdin)
latest = versions[0]
deps = latest.get('dependencies', [])
for d in deps:
    print(d.get('project_id','?'), d.get('dependency_type','?'))
"
```

## Batch-resolve project IDs to names

The `/v2/projects?ids=` endpoint accepts up to 100 IDs:

```python
import json, urllib.request

ids = ['id1', 'id2', ...]  # deduplicated, no 'None' values
for i in range(0, len(ids), 20):
    batch = ids[i:i+20]
    ids_param = '%5B' + '%2C'.join(f'%22{id}%22' for id in batch) + '%5D'
    url = f'https://api.modrinth.com/v2/projects?ids={ids_param}'
    resp = urllib.request.urlopen(url)
    projects = json.loads(resp.read())
    for p in projects:
        print(f'{p["title"]:50s} | {p["slug"]}')
```

## Common research pattern

1. Search for packs matching your core mod combo
2. For each candidate, fetch its latest version's dependency list
3. Batch-resolve dependency IDs to human-readable names
4. Filter for your target mods (case-insensitive substring match on title/slug)

## Pitfalls

- Create Aeronautics is **1.21.1-only** — automatically excludes 1.20.1 packs
- Ars Nouveau ecosystem is mostly 1.20.1 — small intersection with Aeronautics packs
- `dependency_type` values: `required`, `optional`, `embedded` (shipped inside the pack)
- Some packs use `embedded` for all mods (no separate downloads needed); others use `required` to pull from Modrinth
- The `/v2/project/<slug>/version` endpoint returns ALL versions sorted newest-first — `versions[0]` is the latest
