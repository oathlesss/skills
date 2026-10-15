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
