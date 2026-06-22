# TC6 API Architecture — Reference for Mod Design

Extracted from the decompiled TC6 source code at `github.com/TheDarkTower314/Thaumcraft-6-Source-Code`. This documents Azanor's API design patterns for building a data-driven, mod-compatible magic mod.

Source repos:
- `github.com/TheDarkTower314/Thaumcraft-6-Source-Code` — full TC6 source (decompiled), `thaumcraft.api.*` package is the reference layer
- `github.com/alegian/thavma` — a modern NeoForge reimagining (early stage, 4 Java files, mostly 3D models and WIP — not yet useful as reference)

## Package Split

```
thaumcraft.api.*    — public API surface for other mods
thaumcraft.client.* — rendering, particles, GUI
thaumcraft.common.* — implementation (not in decompiled version)
```

The API layer is self-contained: other mods only need `thaumcraft.api.*` at compile time.

## Aspect System

### Aspect (base class)
```java
public class Aspect {
    String tag;                    // unique ID (e.g. "aer", "ordo")
    Aspect[] components;           // null for primals, 2-element array for compounds
    int color;                     // hex color
    ResourceLocation image;        // 32x32 icon texture
    int blend;                     // GL blend mode (1=normal, 771=additive)

    static HashMap<Integer, Aspect> mixList;  // compound lookup by hash of component pair
}
```

Key patterns:
- Compound aspects stored as two-component decomposition (not arbitrary N-component)
- `mixList` is a HashMap keyed by `(compA.tag + compB.tag).hashCode()` — fast reverse-lookup to find which compound two primals make
- Primals constructed with `components=null`
- Each aspect auto-registers as a `ScanAspect` so it's scannable by the Thaumometer

### AspectList
```java
public class AspectList {
    LinkedHashMap<Aspect, Integer> aspects;  // ordered map
    int visSize;                              // total vis stored
}
```
Operations: `merge()`, `remove()`, `reduce()`, `add()`, `copy()`. Used everywhere — crucible recipes, infusion recipes, research point costs, wand vis, golem materials.

### AspectEventProxy & AspectRegistryEvent
Registration is event-based, fired during init. Other mods subscribe to add aspects to their items. Avoids hardcoding and supports mod compatibility.

## Research System

### ResearchEntry (JSON-loaded)
```java
public class ResearchEntry {
    String key;                    // unique ID
    String category;               // parent category key
    String name;                   // localizable display name
    String[] parents;              // prerequisite research keys
    String[] siblings;             // auto-unlocked when this completes
    int displayColumn, displayRow; // position in Thaumonomicon grid
    Object[] icons;                // display icons
    EnumResearchMeta[] meta;       // ROUND, SPIKY, REVERSE, HIDDEN, AUTOUNLOCK, HEX
    ResearchStage[] stages;        // progressive stages (each has text, requirements, knowledge rewards)
    ResearchAddendum[] addenda;    // extra pages unlocked by conditions
    ItemStack[] rewardItem;        // physical rewards
    Knowledge[] rewardKnow;        // observation knowledge rewards
}
```

### ResearchCategory
```java
public class ResearchCategory {
    String key;                    // unique ID
    String researchKey;            // prerequisite research to show this tab
    AspectList formula;            // aspects required for theorycrafting in this category
    ResourceLocation icon, background, background2;  // tab icons
    LinkedHashMap<String, ResearchEntry> research;    // entries in this category
}
```

### Theorycraft System (research minigame)
TC6 uses a card-based system — players play theorycraft cards at a research table to generate theories:
- `TheorycraftCard` — base class for card types (Analyze, Balance, Experimentation, Inspired, Notation, Ponder, Reject, Rethink, Study)
- `ResearchTableData` — tracks the state (inspiration, theory progress, cards in hand)
- `ITheorycraftAid` — blocks near the research table that provide bonuses (bookshelves = `AidBookshelf`)

### ResearchEvent
```java
public class ResearchEvent extends Event {
    public static class Knowledge extends ResearchEvent { /* fires when player gains knowledge */ }
    public static class ResearchCompleted extends ResearchEvent { /* fires when entry completed */ }
}
```
Event-driven so other mods can react to research progress.

## Crafting Systems

### CrucibleRecipe
```java
public class CrucibleRecipe implements IThaumcraftRecipe {
    ItemStack recipeOutput;
    Ingredient catalyst;           // item that triggers the craft (right-click with it)
    AspectList aspects;            // required essentia minimums
    String research;               // gating research key (null = no gate)

    boolean matches(AspectList itags, ItemStack cat) {
        if (!catalyst.apply(cat)) return false;
        for (Aspect tag : aspects.getAspects())
            if (itags.getAmount(tag) < aspects.getAmount(tag)) return false;
        return true;
    }
}
```
**LOOSE matching** — checks minimums, not exact amounts. Excess essentia is consumed and wasted (generating flux).

### InfusionRecipe
```java
public class InfusionRecipe implements IThaumcraftRecipe {
    AspectList aspects;             // essentia cost
    String research;                // gating research key
    NonNullList<Ingredient> components;  // items on pedestals
    Ingredient sourceInput;         // central item
    Object recipeOutput;
    int instability;

    boolean matches(List<ItemStack> input, ItemStack central, World world, EntityPlayer player) {
        if (!ThaumcraftCapabilities.getKnowledge(player).isResearchKnown(research)) return false;
        return sourceInput.apply(central) && RecipeMatcher.findMatches(input, components) != null;
    }
}
```
Research-gated. Uses `RecipeMatcher.findMatches()` for ingredient matching — the same utility vanilla uses for shapeless recipes.

### IThaumcraftRecipe interface
```java
public interface IThaumcraftRecipe {
    String getResearch();
    String getGroup();     // for recipe book grouping
}
```
All Thaumcraft recipes implement this — research gating is a first-class concept.

### ShapedArcaneRecipe / ShapelessArcaneRecipe
Extend vanilla `ShapedRecipe`/`ShapelessRecipe` with vis cost:
```java
public class ShapedArcaneRecipe extends ShapedRecipe {
    String research;
    int vis;                         // vis cost (total, not per-aspect in TC6)
    String group;
}
```

### Fake Recipe Catalog
TC6 maintains a separate `craftingRecipeCatalogFake` HashMap for display-only recipes:
```java
public static void addFakeCraftingRecipe(ResourceLocation registry, Object recipe)
```
Used for infusion enchantment recipes and runic infusion — they can't be crafted in a GUI but should show in JEI/Thaumonomicon. **This pattern is worth adopting.**

## Wand / Focus System (Casters)

TC6's wand system is entirely different from TC4 — it's a node-based spell-crafting system:

### FocusNode hierarchy
```
FocusNode (base, has NodeSetting[])
├── FocusEffect (leaf — what the spell does)
├── FocusMedium (branch — how effect travels: bolt, beam, touch, projectile, self)
│   └── FocusMediumRoot (entry point for a wand, defines casting interface)
├── FocusMod (modifier — add properties: damage, range, split, mine, silk touch)
│   └── FocusModSplit (splits the spell into multiple outputs)
└── FocusPackage (container — holds a sub-spell)
```

### Key interfaces
- `ICaster` — anything that can cast a spell (wand, staff, gauntlet)
- `IFocusElement` — any node that can be part of a spell chain
- `IFocusBlockPicker` — focus nodes that need to select blocks
- `IInteractWithCaster` — allows focus to interact with the caster entity
- `Trajectory` — handles projectile path with gravity

### FocusEngine
Evaluates the spell node tree:
1. Start at `FocusMediumRoot` (the wand tip)
2. Walk through `FocusMedium` nodes to reach target
3. Apply `FocusMod` nodes for modifications
4. Execute `FocusEffect` nodes at the target

### CasterTriggerRegistry
```java
public static void registerTrigger(ResourceLocation key, ICasterTriggerManager trigger)
```
Manages projectile hit/impact callback registration.

## Golem System

### Modular parts
```java
GolemMaterial   // body material (straw, wood, clay, thaumium, void)
GolemHead       // head (determines animation/expression)
GolemArm        // arms (determine interaction capability)
GolemLeg        // legs (determine speed/step height)
GolemAddon      // optional upgrades (air ring, earth ring, etc.)
```

### GolemProperties
```java
public interface IGolemProperties {
    GolemMaterial getMaterial();
    GolemHead getHead();
    GolemArm getArms();
    GolemLeg getLegs();
    List<GolemAddon> getAddons();
    EnumGolemTrait getTraits();  // bitmask: SMART, FLYING, FIREPROOF, etc.
}
```

### Seals (behavior programming)
```java
public interface ISeal {
    String getKey();
    void tickSeal(World world, ISealEntity sealEntity);
    // Optional config interfaces:
    // ISealConfigArea — area selection
    // ISealConfigFilter — item/block filtering
    // ISealConfigToggles — on/off toggles
    // ISealGui — custom GUI
}
```
A seal is a block that golems path to. Each seal type defines behavior. The seal persists as a block entity. Golems read seal config to determine their task.

### Task System
```java
public class Task {
    long startTime;
    short priority;
    ITaskType type;       // GET, STORE, USE, FIGHT, GUARD, etc.
    SealPos destination;
}
```

## Capabilities

TC6 uses Forge capabilities (the 1.12 equivalent of NeoForge attachments):

```java
IPlayerKnowledge    — known research, theories, research points
IPlayerWarp         — warp level, temporary/permanent warp
```

### IPlayerKnowledge
```java
boolean isResearchKnown(String key);
boolean isResearchComplete(String key);
int getResearchStage(String key);
boolean addKnowledge(String key, ResearchStage.Knowledge type);
```

## Particle / FX System

TC6 has an elaborate custom particle system for magic effects:
- `FXDispatcher` — central dispatcher
- Beams: `FXArc`, `FXBolt` (lightning-style), `FXBoreStream`, `FXEssentiaStream`
- Particles: `FXVisSparkle`, `FXBoreSparkle`, `FXSwarm`, `FXSwarmRunes`, `FXBlockRunes`, `FXShieldRunes`
- Projectiles: `FXSonic`, `FXVoidStream`

## Key Design Patterns to Adopt

1. **API/Impl split**: `lib/` for other mods, `core/` for implementation
2. **Loose recipe matching**: minimums-based (Crucible), not exact-match
3. **Fake recipe catalog**: separate display-only recipe list for JEI
4. **Research gating on recipes**: `IThaumcraftRecipe.getResearch()` on every recipe type
5. **Event-driven registrations**: `AspectRegistryEvent`, `ResearchEvent` — allows mod compat
6. **Modular golem parts**: material/head/arm/leg/addon all separate registries
7. **Seal-based golem AI**: behavior is a block, not hardcoded
8. **Capabilities for player state**: `IPlayerKnowledge`, `IPlayerWarp` — extensible by other mods
9. **Theorycraft cards**: research minigame is data-driven, cards are registrable
10. **FocusNode tree**: spell-crafting system uses a composable node graph
