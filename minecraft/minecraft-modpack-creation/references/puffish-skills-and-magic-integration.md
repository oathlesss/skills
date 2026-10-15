# Puffish Skills + Magic mods (skill trees, XP sources, Combat Roll, Thaumaturge)

How to add a **Puffish Skills** tree + magic mods (Ars Magica, Thaumaturge, Combat Roll) to a
lean 26.1.2 NeoForge pack. All verified on MC 26.1.2 / NeoForge 26.1.2.109.

## Delivery mechanism: Paxi (not a resource pack, not global_packs)
Puffish loads its skill tree from a **datapack**. On a server you ship it via **Paxi**
(YUNG's global datapack loader, Modrinth slug `paxi` — `Paxi-26.1.2-NeoForge-6.1.0.jar`).
Paxi loads datapacks from `config/paxi/datapacks/<name>/`. (Global Packs only had a 26.1.0
build at the time — Paxi is the one with a 26.1.2 jar.) Put the tree at:
```
config/paxi/datapacks/puffish-skills/
  pack.mcmeta
  data/puffish_skills/...   # (or however the tree is namespaced)
```
A datapack needs `pack.mcmeta` (pack_format matching the MC version) plus the tree JSON.

## Tree structure (one category = 5 files)
Each skill category is a folder of JSON files:
- `category.json` — `unlocked_by_default`, `title`, `description`, `icon` (item ID or texture),
  **`background`** (REQUIRED), `starting_points`.
- `connections.json`, `definitions.json`, `skills.json`, `experience.json`.

**`background` is mandatory and Puffish ships NO frame textures.** Use a vanilla tile:
```json
"background": {
  "texture": "minecraft:textures/gui/options_background.png",
  "width": 16, "height": 16, "position": "tile"
}
```
Missing `background` → boot error `Expected background to exist` per category.

## XP sources per category (`experience.json`)
`experience.json` holds the `experience_per_level` curve (shared) and a `sources` list. The
curve is an expression:
```json
"experience_per_level": {"type": "expression", "data": {"expression": "100 * level"}}
```
**Named source event types that work** (each is `{"type": "<event>", "data": {…}}`):
- **Melee damage/kills** — `deal_damage` with `"expression": "damage * 0.5"`; `kill_entity` with
  `"expression": "dropped_xp * 2"`.
- **Ranged vs melee split** — `deal_damage`/`kill_entity` both accept a `variables` filter on the
  damage-type tag. Give ranged the bow/crossbow hits and melee the rest by adding an
  `is_projectile` variable:
  ```json
  "is_projectile": {"operations": [
    {"type": "get_damage_source"}, {"type": "get_type"},
    {"type": "puffish_skills:test", "data": {"damage_type": "#minecraft:is_projectile"}}
  ]}
  ```
  then ranged: `{"condition": "is_projectile", "expression": "damage * 0.5"}`; melee:
  `{"condition": "!is_projectile", ...}`. `#minecraft:is_projectile` is a vanilla damage-type tag.
  (Exact syntax from Evo 2's `ranged/experience.json` + `melee/experience.json`.)
- **Mining ores** — `mine_block` with a block tag: `"block": "#c:ores"`, `"experience": 8`
  (the `#c:ores` common tag is what modern tags use, NOT `#forge:ores` on 26.x).
- **Athletics** — `increase_stat` on vanilla custom stats, e.g.
  `"stat": "minecraft.custom:minecraft.jump"` → 2, `sprint_one_cm` → 0.05, `swim_one_cm` → 0.1,
  `climb_one_cm` → 0.1. (These are vanilla scoreboard criteria names.)
- **Mod-specific triggers** — `criterion` with a mod's custom criterion, e.g.
  `"criterion": "arsmagicalegacy:level_change"` → 60 XP per level-up.
- **Defense** — `take_damage` with `"expression": "damage"`.

Always end the JSON with the `sources` array; a category with no `sources` silently grants nothing.

## Mod attribute namespaces for skill rewards
- Puffish built-ins: `puffish_attributes:*`. Full verified 0.8.2 attribute list (extract the jar and
  grep its `.class` files — `grep -rhoaE '(melee|ranged|magic|mining|...)[a-z_]*' <dir> --include='*.class'`):
  `melee_damage`, `melee_resistance`, `melee_resistance_shred`, `ranged_damage`, `ranged_resistance`,
  `ranged_resistance_shred`, `magic_damage`, `magic_resistance`, `magic_resistance_shred`,
  `resistance`, `resistance_shred`, `sword_damage`, `axe_damage`, `axe_speed`, `mining_speed`,
  `pickaxe_speed`, `shovel_speed`, `breaking_speed`, `fortune`, `sprinting_speed`, `stamina`, `jump`,
  `fall_reduction`, `mount_speed`, `consuming_speed`, `natural_regeneration`, `healing`, `life_steal`,
  `knockback`, `damage_reflection`, `repair_cost`, `tamed_damage`, `tamed_resistance`,
  `bow_projectile_speed`, `crossbow_projectile_speed`.
  **Verify every attribute against the mod's own jar** — a typo'd attribute is silently
  non-functional (no error/warning), so grepping the jar is the only reliable oracle. Don't guess.
- Ars Magica: `arsmagicalegacy:max_mana`, `mana_regeneration`, `max_burnout`, `burnout_regeneration`.
- Combat Roll: `combat_roll:count` (extra roll), `combat_roll:distance`, `combat_roll:recharge`.

## Combat Roll integration
`combat_roll-neoforge-3.0.1+26.1.2.jar`. Hard deps: `player_animation_library` + `cloth_config`
(both usually already present); `tiny_config` is **JiJ-bundled inside the jar** so no separate
download. Hook it into the Puffish tree as ordinary attribute skills (`combat_roll:count +1`,
`distance +1`, `recharge +0.5`, all `addition` ops).

## Thaumaturge portal rarity
`crimsonPortalRarity` lives in `config/thaumaturge-common.toml`. Mod default 500, FTB Evo 2 ships
5000. Ruben's preference is **10000** (make portals genuinely rare). Value = average chunks per
portal spawn (higher = rarer).

## Pitfall: `"condition": ""` is invalid — omit the field, don't blank it
In an XP source's `experience` array, `{"condition": "", "expression": "..."}` is a hard error
(`Invalid expression at condition` → the WHOLE `puffish_skills` datapack fails to load). For an
unconditional source, emit `{"expression": "..."}` with NO `condition` key at all.

## CRITICAL pitfall: do NOT reuse a kitchen-sink pack's Puffish tree
Copying another pack's tree (e.g. FTB Evolution 2's) into a lean pack produces **hundreds of
`Unknown item/attribute` warnings** and a broken tree — the source tree is hard-wired to mods you
don't ship (Apotheosis, Paraglider, Artifacts, Reliquary, Irons guns, Neovitae, Anima, Witchery,
Occultism, Roots, and custom `ftb:*` attributes) plus a `ftbevolution` texture pack for frames and
an `ftb` lang datapack for names. **Build the tree fresh** using only vanilla + the attributes
that are actually in your pack.

## Verification (boot log)
- `[puffish_skills] Data pack puffish_skills loaded successfully!`
- **Zero** `Unknown item/attribute` lines — any of these = a dangling reference to an absent
  mod/attribute/tag.
- No `Expected background to exist` per category.
- Thaumaturge rebuilds `config/thaumaturge/aspect_index.json` on first load (~6100 items, ~3.6 MB).
