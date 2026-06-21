---
name: minecraft-modpack-research
description: Search and compare Minecraft modpacks using the Modrinth API — find packs by mod inclusion, version, category, and cross-reference dependency lists.
triggers:
  - Minecraft modpack
  - find modpack
  - modpack with
  - mods included in pack
  - search modpacks
  - CurseForge modpack search
  - what modpacks have
---

# Minecraft Modpack Research

Use this skill when the user asks to find, search, or compare Minecraft modpacks — especially by which mods they include, what version they're on, or what categories they belong to. Uses the **Modrinth API** (no auth needed) for structured search and dependency resolution.

## Core workflow

### 1. Search for modpacks by keyword or facet

```bash
# Basic keyword search
curl -s "https://api.modrinth.com/v2/search?query=Ars+Nouveau+Create&facets=%5B%5B%22project_type%3Amodpack%22%5D%5D&limit=20"

# Filter by MC version and category
curl -s "https://api.modrinth.com/v2/search?facets=%5B%5B%22project_type%3Amodpack%22%5D%2C%5B%22versions%3A1.21.1%22%5D%2C%5B%22categories%3Amagic%22%5D%5D&limit=50"
```

Facet encoding: `[["key:value"]]` → `%5B%5B%22key%3Avalue%22%5D%5D`. Multi-facet: join with `%2C`.

### 2. Get a project's version list (includes dependency IDs)

```bash
curl -s "https://api.modrinth.com/v2/project/<slug>/version"
```

The latest version's `dependencies` array contains `project_id` strings for every mod in the pack.

### 3. Resolve project IDs to names (batch)

```bash
# Up to 100 IDs per call
curl -s "https://api.modrinth.com/v2/projects?ids=%5B%22id1%22%2C%22id2%22%5D"
```

Use Python's `urllib.request` for batch resolution with list-chunking (20-50 IDs per batch).

### 4. Get a single project's metadata

```bash
curl -s "https://api.modrinth.com/v2/project/<slug>"
```

Returns title, downloads, versions array (version IDs, not MC versions), categories, description.

## Key project IDs (stable references)

| Mod | Project ID |
|-----|-----------|
| Ars Nouveau | `TKB6INcv` |
| Create | `LNytGWDc` |
| Create Aeronautics | `oWaK0Q19` |
| Minecolonies | `sSr0QEGx` (Modrinth listing, **only 1.18.2** — primary distribution on CurseForge) |
| Farmer's Delight | `R2OftAxM` |

## Pitfalls

- **Minecolonies on Modrinth is outdated** — the Modrinth listing only has 1.18.2. Its addons (Pathfinding Edition, Block Party) are on 1.21.1, confirming the mod exists for modern versions, but it lives on CurseForge. Don't assume a pack lacks Minecolonies just because Modrinth deps don't include it.
- **CurseForge pages are Cloudflare-protected** — direct scraping returns "Just a moment..." challenge pages. The CurseForge API requires an API key (not available by default). When a user links a CF-exclusive pack, you CANNOT verify its contents programmatically via CurseForge. **Workaround for major packs**: many large CF packs (ATM10, ATM9, Enigmatica, etc.) publish their modlist as a plain-text file on GitHub. Check `https://raw.githubusercontent.com/<org>/<repo>/main/modlist.txt` or similar. This is a fast, reliable way to verify whether a specific mod is in the pack without scraping CurseForge.
- **Deleted/replaced mods** — a pack may require a mod that no longer exists on CurseForge or Modrinth (e.g., `create_linear_motion_simulated`). This usually means the mod was renamed or merged into another. Search for the core functionality keyword (e.g., "propulsion", "simulated") to find the successor. The replacement almost always has the same API surface — just swap the jar and the pack should work.
- **Slug URLs with special characters** — slugs like `"medival,-magic-tech"` contain commas that break shell commands. URL-encode or quote carefully.
- **Dependency listing is `embedded` for modpack mods** — Modrinth packs list mods as `dependency_type: "embedded"`. Don't filter by dependency type.
- **`date_modified` may not exist** on all project responses. Don't rely on it.
- **Rate limiting** — batch-resolve IDs in chunks of 20-50 with small delays between batches if doing many.

## Reverse-search pattern (most effective)

When looking for packs with specific mods, the most efficient approach:

1. Search for the rarest mod (e.g., Create Aeronautics) to get candidate packs
2. For each candidate, fetch its dependency list
3. Check for the other required mods by project ID
4. Only resolve names for matches — don't waste API calls

```python
# Template: check all packs matching query for specific mod IDs
target_id = 'TKB6INcv'  # Ars Nouveau
for hit in hits:
    pid = hit['project_id']
    url = f'https://api.modrinth.com/v2/project/{pid}/version'
    resp = urllib.request.urlopen(url)
    deps = json.loads(resp.read())[0]['dependencies']
    if target_id in [d['project_id'] for d in deps]:
        print(f"Match: {hit['title']}")
```

## Catastrophic intersection pattern

When searching reveals a tiny intersection (e.g., 2 packs across 79+ candidates), state it plainly:
- Identify the root cause (version mismatch, mod ecosystem history)
- Show what's available if they drop each requirement
- Offer the DIY path (take the best pack and add the missing mod manually)

## Manual mod addition (when no pack has everything)

When no pack covers all desired mods, recommend adding the missing mod(s) to the best partial pack. Before suggesting this, verify:

1. **MC version match** — the mod must support the pack's MC version. Check via `/v2/project/<mod-slug>/version` → filter `game_versions`.
2. **Loader match** — Ars Nouveau 1.21.1 is NeoForge-only. A Forge pack on 1.21.1 can't use it. Check `loaders` in the version data.
3. **Dependency check** — fetch the mod's dependencies (required ones) and compare against what the pack already has. For Ars Nouveau 1.21.1: Geckolib, Curios API Continuation (most Create packs already have these).
4. **Worldgen conflict risk** — mods that add new biomes/structures (Oh The Biomes, YUNG's) have low conflict with magic mods. Mods that overhaul vanilla mechanics are higher risk.
5. **Server sync** — if playing multiplayer, everyone needs the same mods. Singleplayer is trivial (just drop in and launch).
