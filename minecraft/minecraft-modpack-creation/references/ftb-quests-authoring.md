# FTB Quests authoring (NeoForge 26.1.2)

How to author an FTB Quests quest book for a 26.1.2 NeoForge pack. Learned building evo2-tech's
21-chapter / 146-quest book, modeled on FTB Evolution 2's quest data (same `ftb-quests` version).

## File layout (pack-level, ships under `config/` in BOTH client and server builds)
```
config/ftbquests/quests/
├── chapter_groups.json5        # {"chapter_groups": [{"id": "<16-hex>"}]}  (one group is enough)
├── data.json5                  # global: version 13, tags ["standard"], progression_mode, defaults
├── chapters/<filename>.json5   # quest definitions: icons, x/y, shape, tasks, rewards, deps — NO titles
└── lang/en_us/
    ├── chapter.json5           # {"chapter.<ID>.title": "Name"}
    └── chapters/<filename>.json5  # {"quest.<ID>.title": "...", "quest.<ID>.quest_desc": [...]}
```

## Key facts
- **Titles/descriptions live in lang files, NOT inline on quests.** FTB Quests 2001.x (e.g.
  `26.1.2.9`) reads `quest.<ID>.title` and `quest.<ID>.quest_desc` (note: `quest_desc`, NOT
  `description`) — and `chapter.<ID>.title` for chapter names. Inline `title`/`description` fields
  on the quest object are unreliable; put text in lang files exactly like Evo 2 does.
- **Valid JSON (json.dump) IS valid JSON5.** Generate all quest files with Python's `json` module —
  never hand-write JSON5. Zero syntax risk across hundreds of quests.
- IDs (chapter/quest/task/reward) are **16-char uppercase hex**, must be unique, and **must be
  positive 64-bit longs**. Generate with `format(secrets.randbits(63), '016X')` — NOT
  `uuid.uuid4().hex[:16]` (see the "positive long" gotcha below).
- Task: `{"id", "type": "item", "item": {"id": "mod:item", "count": N}}` or `{"type": "checkmark"}`.
- Reward: `{"id", "type": "xp", "xp": N, "team_reward": false}` or
  `{"id", "type": "item", "item": {...}, "team_reward": false}`. `"type": "currency"` = FTB coin
  currency.
- `"dependencies": [<quest_id>, ...]` references earlier quest IDs to wire progression.

## Item-ID oracle (get correct IDs without launching the game)
Evo 2's own chapter files are the authoritative source of valid 26.1.2 item IDs for every mod in the
pack. Extract per-mod IDs with:
```bash
grep -oE 'id: "[a-z0-9_]+:[a-z0-9_/]+"' <chapter>.json5 | sort -u
```
Note the **unquoted JSON5 key** — it's `id: "..."` (no quotes around `id`), NOT `"id": "..."`. Grepping
for `"id":` returns nothing; grep for `id: "`.

## Reward preferences (Ruben — durable)
- **NO FTB coin currency.** Use XP + item rewards instead.
- Mix in item rewards on most quests; keep XP on every quest.
- Reward = a small stack of a **useful NEXT-step material or fuel**, never the quest's own item
  (redundant). Examples: coal/coal-block/lava-bucket for generator quests; ingots/crystals to smooth
  the grind; next-tier components (capacitors, machine cores, circuits).
- `team_reward: false` so each player claims their own on a friends server.
- "Doesn't have to match Evo 2 entirely" — don't copy its currency economy, loot tables, or
  cross-chapter gearing hub unless explicitly asked.

## Gotchas
- **CRITICAL — every id is a signed 64-bit `long`; negative ids get silently reassigned.** FTB
  Quests stores chapter/quest/task/reward/group ids as `long`s. A 16-hex id whose first digit is
  `8`–`F` parses as NEGATIVE, and FTB Quests rejects it on load — it assigns a fresh (positive) id,
  which no longer matches the `chapter.<ID>.title` / `quest.<ID>.title` lang key, so that object
  renders **"Unnamed"**. `uuid.uuid4().hex[:16]` yields a leading `8`–`F` ~50% of the time, so
  ~half your chapters silently lose their titles. Generate with `format(secrets.randbits(63), '016X')`
  (always starts `0`–`7`). **Verify after the first server load:** FTB Quests re-serializes the
  book to unquoted-key JSON5; diff live `chapters/*.json5` ids vs your source ids and assert NONE
  changed (and that `chapter_groups.json5` id is unchanged).
- **Client and server quest trees MUST be byte-identical — generate ids once, not per-tree.** The
  book ships under BOTH `client/config/ftbquests/` and `server/config/ftbquests/`. If a generation
  script loops over both trees and calls `secrets.randbits(63)` per tree, the two runs get DIFFERENT
  ids for any newly-added quest/task/reward (e.g. chapter-intro quests), so the trees silently diverge.
  Fix: either seed the RNG / derive ids deterministically, OR generate on ONE tree and `cp -r` it over
  the other, then `diff -rq` both trees and assert empty before shipping. (Hit this adding 20
  chapter-intro quests to evo2-tech — fixed by copying server→client.)
- **`ftb-materials` / `ftb-armory` are NOT in evo2-tech** (and FTBIC/Stellaris only *soft*-reference
  them — their `mods.toml` has no hard requirement on `ftbmaterials`). Don't reward `ftbmaterials:*`
  or `ftbarmory:*` items; use each mod's native IDs (`oritech:nickel_ingot`, `stellaris:pipe_t1`, etc.).
  If a pack DOES pull in `ftb-materials`, those unified-material IDs become valid.
- Quest DEFINITIONS are server-side and ship in both builds; progress syncs to clients. For a
  dedicated server only `server/config/ftbquests/` matters, but ship both so single-player works.
- Evo 2 stores per-chapter lang in `lang/en_us/chapters/<filename>.json5`; chapter titles in
  `lang/en_us/chapter.json5`; also has `lang/en_us/chapter_group.json5` (group titles, optional).

## Reusable generation pattern
Build chapters as Python data — list of `(key, title, icon, [task_item_ids], [dep_keys], [desc_lines])`
specs. Auto-position quests (first = diamond/size 1.5, last = hexagon "goal", rest = square in a
2-column grid), resolve `dep_keys`→IDs inline (deps always point to earlier quests), emit positive-long hex
IDs (`secrets.randbits(63)`), dump with `json.dump`. ~21 chapters / 146 quests generated cleanly with zero JSON errors.
Validate afterward with `json.load` on every `.json5` glob.

## Deploying quest changes to a LIVE server (progress-safe)
The live book lives at `<itzg-data>/config/ftbquests/quests/` (e.g.
`/home/ruben/homeserver/minecraft-evo2tech/data/config/ftbquests/quests/`). FTB Quests
re-serializes these files to unquoted-key JSON5 on first load, but **quest/task/reward IDs are
stable** — only formatting changes. So overwriting with clean source files is safe.

1. **Progress-safety check FIRST.** Before touching anything, diff live vs source quest IDs and
   assert ZERO ids exist only in live (a dropped id = lost player progress). New additive ids
   (intro quests) are fine. Parse both trees with a lenient JSON5 loader (strip `//`, trailing
   commas, unquote keys) and compare `quests[].id` per chapter file.
2. **Back up** the live quest dir: `cp -r <live> <live>.bak-$(date +%Y%m%d-%H%M%S)`.
3. **Deploy:** `docker stop <container>` → `cp -r <src>/quests/. <live>/quests/` → `docker start`.
   (Stop first so the world saves and no file races; FTB Quests reads config only at boot.)
4. **Verify via the log line**, not just container health:
   `[FTB Quests/] Loaded <N> chapter groups, <N> chapters, <N> quests, <N> reward tables`.
   Quest count should equal old + new-intros, and there must be **no "Unnamed" / reassignment
   warnings**. `docker logs --since 3m ... | grep -i "FTB Quests"`.
5. **Non-gating intros don't lock players.** A "Welcome to [Mod]" intro quest with a checkmark
   task and NO incoming dependencies is purely additive — existing players keep all progress and
   just see a new top node to check. Only *structural* changes (new gating deps, removing/renaming
   quest ids) risk locking/rekeying progress. For a LIVE pack, prefer additive polish (rich
   descriptions, intro quests, reward bumps) over structural rewiring.

## Shipping updated quest files into existing archives
The pack ships as a client `.mrpack` (Prism, `modrinth.index.json` + `overrides/`) and a server
`.zip` (flat `config/` + `mods/`). Both bundle the FULL generated config tree — which the
hand-maintained `client/config/` + `server/config/` source dirs do NOT contain. So **never rebuild
the archive from source**; surgically replace only the quest entries instead, preserving everything
else (the other mods' generated configs, `modrinth.index.json`, and the client-only
`config/ftbquests-client.json5`):

```python
import zipfile, os
SRC = "/path/to/.../server/config/ftbquests/quests"   # quest dir (identical in both builds)
PREFIX = "overrides/config/ftbquests/quests/"          # .mrpack; use "config/ftbquests/quests/" for a flat .zip
entries = {}
for dp, _, fns in os.walk(SRC):
    for fn in fns:
        rel = os.path.relpath(os.path.join(dp, fn), SRC).replace(os.sep, "/")
        entries[PREFIX + rel] = open(os.path.join(dp, fn), "rb").read()
tmp = ARCHIVE + ".tmp"
zin, zout = zipfile.ZipFile(ARCHIVE), zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    zout.writestr(item, entries.get(item.filename, zin.read(item.filename)))  # replace or copy
zin.close(); zout.close(); os.replace(tmp, ARCHIVE)
```

Deliver the client `.mrpack` by dropping it in `~/homeserver/www/` → served at
`https://oathless.dev/files/<name>` (Caddy `handle_path /files/*` → `root * /srv/www`). Verify with
`zipfile.testzip()` + a `curl -sI` for HTTP 200 before telling the user it shipped.
