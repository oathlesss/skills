---
name: minecraft-modpack-creation
category: minecraft
description: "Design and assemble a custom Minecraft modpack from scratch (wishlist → verified mod list → distribution format → server+client perf stack) for Ruben's private/friends servers. Trigger on 'create/build a modpack', 'custom modpack', 'pack for friends', 'pick mods for a server', or a mod wishlist needing curation + version verification."
---

# Minecraft Modpack Creation (from-scratch curation)

Design a curated pack from a wishlist. Distinct from `minecraft-server-ops` (administering an
EXISTING itzg server) and `minecraft-modpack-guide` (writing player guides). This skill owns
the *selection → verification → assembly* pipeline.

## When to use
- User gives a mod wishlist and wants a pack built (vs. a guide written).
- "create a modpack for friends" / "leaner custom pack" / "should I include X?".
- Version/loader feasibility of a mod list needs verifying before building.

## Workflow

1. **Pin the target before anything else** — version + loader + platform. Ruben's default is
   **1.21.1 NeoForge** (matches ATM10aero; the whole tech-magic ecosystem has builds here).
   NOTE: Minecraft moved to a new versioning scheme in 2026 — "26.x" releases exist and most
   mods' *latest* builds now target 26.x, but AE2 / Productive Bees / Dyson Cube / Distant
   Horizons are NOT fully there yet. 1.21.1 NeoForge remains the safe sweet spot for
   tech-magic packs. Confirm with the user; also confirm scope (fresh pack vs. extend an
   existing server) — it changes everything.

2. **Map wishlist → real mod names.** Disambiguate (see pitfalls: Dyson Cube vs Dyson Sphere
   Project; Create Aeronautics needs Sable).

3. **Verify every uncertain mod** via Modrinth API (below). Trust only the facet-filtered
   query — NOT the "latest" version.

4. **Decide distribution format by platform exclusivity:**
   - Core mods are CurseForge-only (AE2, Flux Networks, Productive Bees/Trees, Dyson Cube,
     Distant Horizons, Twilight Forest, FerriteCore, LaserIO, Advanced AE, MEGA Cells, Applied
     Flux, AE2 Things, Embeddium Extras, Connectivity, Cupboard) → **CurseForge-format
     self-contained zip** (every jar bundled; friends need no CF API key). Reuse
     `minecraft-server-ops` refs: `shareable-modpack-export.md` + `full-self-contained-zip.md`.
   - Modrinth-native-only mods (Create Aeronautics, Sable) go into `overrides/` for a CF zip;
     a `.mrpack` only makes sense if NO core mod is CF-only.

5. **Bundle the perf stack** — server + client (see reference). Shaders are OPT-IN, not forced
   (FPS killer on low-end machines). The server perf stack can be copied jar-for-jar from
   ATM10aero (already 1.21.1 NeoForge, version-matched).

## Version/loader verification (Modrinth API, no key)

```bash
# EXISTS? search
curl -s "https://api.modrinth.com/v2/search?query=<q>&facets=[[%22project_type:mod%22]]"
# IS THERE a 1.21.1 NeoForge build? facet-filtered — this is the reliable query
curl -s "https://api.modrinth.com/v2/project/<slug>/version?game_versions=%5B%221.21.1%22%5D&loaders=%5B%22neoforge%22%5D"
```

⚠️ Reading the `/version` list's `data[0]` (latest) is MISLEADING: since Minecraft 26.x, the
latest release targets the new MC. A mod whose latest "fails" (e.g. enderio v9.0.6-alpha shows
26.1.2; oculus latest shows 1.19.2) still has a valid 1.21.1 build further down the list.
ALWAYS facet-filter by game_versions + loaders.

A `404` on `/project/<slug>` = NOT on Modrinth → CurseForge-only (or distributed elsewhere,
e.g. Distant Horizons via GitLab/CF). Confirm on CurseForge via the API (classId=6) or
cfwidget (no key).

## Does a specific PACK include mod X? (Modpack Index curl)

When the question is "which packs include/avoid mod X" (e.g. "ATM10-like but no Apotheosis"),
don't trust search snippets or pack descriptions. Query Modpack Index — its pack pages are
server-rendered, so a plain curl + grep is authoritative, no browser or web-extract backend:

```bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
curl -sL "https://www.modpackindex.com/modpack/<id>/<slug>" -A "$UA" -o /tmp/p.html
grep -io '<modname-prefix>[a-z]*' /tmp/p.html | sort | uniq -c   # 0 matches = absent
```

Find the `<id>/<slug>` via `web_search "<pack name> modpackindex"`. Two gotchas:
- An invalid slug returns `404`, but a *stale* slug can silently redirect to a DIFFERENT pack's
  page (seen: `enigmatica-10` → `Odystria II`). Always confirm the returned `<title>` matches
  the pack you asked about before trusting the grep.
- The GitHub-repo `modlist.html` for some packs (e.g. bigchadguys) is another curl-able source,
  but watch the loader — the main repo may list the Fabric/Cobblemon variant, not the NeoForge
  "Non-Cobblemon" one. Cross-check the title/loader.

## Pitfalls
- **Only ship what the user explicitly asked for — don't pad the pack.** Every mod must trace to
  the wishlist (or an explicitly requested add, e.g. Building Gadgets). Unrequested additions get
  rejected — Apotheosis/Apothic suite + Occultism/Modonomicon/Ars Ocultas were pulled after the user
  objected "you added a lot of mods without my input". Suggested-but-unrequested mods belong in a
  *proposal list* for the user to approve, never in the assembled pack.
- **Loader version pins get ignored by Prism** — a self-contained pack pinned to `neoforge-21.1.250`
  still installs the LATEST NeoForge on the client, causing "Incompatible client! Please use NeoForge
  X" + cascading channel errors (e.g. glitchcore:sync_config). See `minecraft-server-ops` pitfall
  "Incompatible client! Please use NeoForge" for the fix (bump server to latest 21.1.x or pin client).
- **Dyson Cube Project** (Buuz135, CurseForge, 1.21.1 NeoForge, "build a Dyson sphere around the
  sun") ≠ **The Dyson Sphere Project** (Modrinth, 1.20.1 Forge only). When a user says "Dyson",
  confirm which.
- **Create: Aeronautics** requires **Sable** (physics library) as a hard dependency. Sable's
  Modrinth "latest" is Fabric — grab the NeoForge 1.21.1 jar matching Aeronautics' requirement,
  don't copy from latest.
- **EnderIO on 1.21.1 is alpha-quality** (v8/v9.x alpha). Works but rough edges; Pipez/LaserIO/
  XNet cover the same ground if it breaks.
- **Radium (Lithium port) clashes with C2ME** — pick Radium for tick-loop perf and skip C2ME
  (Chunky pregen covers worldgen lag). Don't ship both.
- **Embeddium + Oculus + Distant Horizons must be version-aligned** or you get client crashes /
  "network protocol error" disconnects. Pin one compatible set.
- **Shaders on low-end machines** tank FPS. Ship Oculus + shaderpack opt-in (off by default);
  low-end friends run Embeddium + DH with shaders disabled — DH is the cheap-render-distance
  answer.
- **Overlapping recipes** (Create + AE2 + EnderIO + Mekanism all add ingots/crafting) → always
  include Polymorph + Almost Unified.
- **Apotheosis is near-universal in 1.21 kitchen-sinks — verify before assuming a pack skips it.**
  ATM10, FTB Evolution, Craftoria, Enigmatica 10, TNP Limitless 8, Spellbound Engineering,
  Tecnomancia, and Firmament Industry ALL ship Apotheosis (+ the "Apothic" family: Apothic
  Attributes, Apothic Enchanting, Apothic Spawners, Apothic Attractions, + Placebo lib). To get an
  ATM10-scale pack without it you must strip it or nerf it — see
  `references/apotheosis-free-pack-options.md` for the jar list, strip/nerf recipe, and verified
  per-pack inclusion status. Ties into the "don't pad the pack" rule: Ruben has now pushed back on
  Apotheosis twice (removed it from his own pack, then asked for an Apotheosis-free ATM10
  alternative) — treat Apotheosis as opt-in, default OFF.

## Reference files
- `references/1.21.1-neoforge-mod-availability.md` — verified availability/loader matrix for
  common tech-magic wishlist mods (CF-only vs Modrinth vs both), confirmed 1.21.1 NeoForge
  version pins, and the low-end client + server perf stack with verified slugs.
- `references/apotheosis-free-pack-options.md` — the "Apothic" family jar list, strip/nerf recipe,
  and verified per-pack Apotheosis inclusion status for 1.21 kitchen-sinks. Use when the user asks
  for "ATM10-like but no Apotheosis" or any "which packs avoid mod X" question.
