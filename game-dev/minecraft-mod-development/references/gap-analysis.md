# Gap Analysis Framework for Mod Projects

Use this framework after large implementation sessions or when asked to verify completeness.

## Audit Steps

### 1. File Inventory
```bash
cd <project-root>
find src/main/java -name '*.java' | sort
find src/main/resources -name '*.json' | sort
git log --oneline -10
```

### 2. Cross-Reference Against Plan
- Pull up the original plan or meta-prompt
- For each promised feature, check: does a Java file exist? Is it a stub or functional?
- Check git history: `git show <commit> --stat` to see if files were deleted

### 3. Categorize Every Claimed System

| Icon | Meaning |
|------|---------|
| ✅ | Complete and functional — build passes, logic is non-trivial |
| ⚠️ | Partial/stub — registered but no working logic, or minimal placeholder |
| ❌ | Missing entirely — deleted, never written, or broken |

### 4. Key Questions for Each System
- **Blocks**: Are they registered? Do they have BlockEntities? Tickers? Model JSONs? Blockstates?
- **Entities**: Are they in ThauEntities? Do they have AI goals? Renderers?
- **Worldgen**: Configured features? Placed features? Biome modifiers? JSON files?
- **Recipes**: Recipe type registered? Serializer? Example JSON files?
- **GUI**: Screen class exists? Packet handling?
- **Networking**: Payload class? Handler registered?

### 5. Report Honestly
Never claim completion without the audit. Use the ✅/⚠️/❌ table format.
List what's missing explicitly — the user will notice if you don't.

## Common Failure Modes

1. **Files deleted during compile fix** — check git history to see what was removed
2. **Stub blocks with no tickers** — registered but never do anything
3. **Imports that don't resolve** — `com.thau.core.lib.aspect` vs `com.thau.lib.aspect`
4. **API signature assumptions** — methods that don't exist on real classes
5. **JEI/REI plugins without the dependency in build.gradle**

## Thaumcraft Project — Current Known Gaps (last audit: 2026-06-20)

| Gap | Status |
|-----|--------|
| Essentia tube networking | ⚠️ No transport logic |
| Eldritch structures (NBT templates) | ❌ Stubs only |
| Golem renderer/models | ❌ Vanilla rendering |
| Cultist mobs | ❌ Deleted (compile error) |
| Infusion enchantments | ❌ Deleted (API mismatch) |
| Custom particles | ❌ Deleted (deprecated API) |
| JEI plugin | ❌ No JEI dependency |
| Golemancer's Table GUI | ❌ Never built |
| Research entries from datapack | ⚠️ Hardcoded in code |
| Mirror magic (TC4) | ❌ Never implemented |
