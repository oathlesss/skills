#!/usr/bin/env python3
"""Minecraft Mod Asset Validator — checks all registered blocks/items have model
JSONs and that every texture reference in those models points to a real PNG file.

Usage: python3 scripts/validate-assets.py
Exit 0 if clean, 1 if issues found.

Adapt for your mod by updating REGISTERED_BLOCKS and REGISTERED_ITEMS below,
or replace the hardcoded lists with source-code parsing for your specific
registration patterns.
"""

import json, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ASSETS = PROJECT / "src/main/resources/assets/thau"
MODID = "thau"
TEXTURES = ASSETS / "textures"
MODELS = ASSETS / "models"
BLOCKSTATES = ASSETS / "blockstates"

# ── Known registered IDs (all blocks + items from registrations) ──
# Extracted from source — update when adding new blocks/items
REGISTERED_BLOCKS = {
    # com.thau.core.block.ThauBlocks (registerBlockAndItem)
    "arcane_workbench", "infusion_altar", "infusion_pedestal", "essentia_jar",
    "recharge_pedestal", "research_table", "vis_node", "golemancer_table",
    "crucible", "infused_stone", "arcane_stone_block", "arcane_bricks",
    "arcane_tiles", "arcane_pillar",
    "silverwood_log", "silverwood_leaves", "silverwood_sapling",
    "silverwood_planks", "silverwood_stairs", "silverwood_slab",
    "silverwood_fence", "silverwood_fence_gate",
    "greatwood_log", "greatwood_leaves", "greatwood_sapling",
    "greatwood_planks", "greatwood_stairs", "greatwood_slab",
    "greatwood_fence", "greatwood_fence_gate",
    # com.thau.core.block.essentia.ThauBlocks (register)
    "alembic", "centrifuge", "focal_manipulator", "warded_block",
    "hungry_chest", "infernal_furnace", "arcane_bore", "essentia_tube",
}

REGISTERED_ITEMS = {
    # From ThauItems.java ITEMS.register
    "thaumonomicon", "thaumometer", "arcane_stone", "thaumium_ingot",
    "brass_ingot", "void_metal_ingot", "nitor", "alumentum",
    "wooden_wand", "greatwood_wand", "silverwood_wand",
    "iron_cap", "gold_cap", "thaumium_cap",
    "wand_core_greatwood", "wand_core_silverwood", "wand_core_blaze",
    "focus_fire", "focus_excavation", "focus_shock", "focus_frost",
    "focus_portable_hole", "focus_warding", "focus_equal_trade",
    "golem_straw", "golem_wood", "golem_clay", "golem_thaumium",
    "golem_core_gather", "golem_core_sort", "golem_core_guard",
    "golem_upgrade_air", "golem_upgrade_fire", "golem_upgrade_water",
    "tainted_soil", "fibrous_taint", "ethereal_bloom",
    "void_seed", "primordial_pearl", "eldritch_eye", "staff_primal",
    "goggles_of_revealing", "boots_of_the_traveller",
    "thaumostatic_harness", "magic_mirror", "arcane_lamp",
    "axe_of_the_stream", "pickaxe_of_the_core",
    "sword_of_the_zephyr", "shovel_of_the_earthmover",
    # From ThauSeals.java SEALS.register
    "seal_gather", "seal_store", "seal_use", "seal_butcher",
    "seal_fill", "seal_empty", "golem_bell",
    # Crystal/shards items
    "aer_crystal", "aqua_crystal", "ignis_crystal",
    "terra_crystal", "ordo_crystal", "perditio_crystal",
    "air_shard", "fire_shard", "water_shard",
    "earth_shard", "order_shard", "entropy_shard",
}


def extract_texture_refs(model_path):
    """Extract all texture references from a model JSON."""
    try:
        data = json.loads(model_path.read_text())
    except Exception:
        return []
    refs = []
    textures = data.get("textures", {})
    for val in textures.values():
        if isinstance(val, str) and val.startswith(f"{MODID}:"):
            refs.append(val.split(":", 1)[1])
        elif isinstance(val, dict):
            for v in val.values():
                if isinstance(v, str) and v.startswith(f"{MODID}:"):
                    refs.append(v.split(":", 1)[1])
    return refs


def check_model(model_path):
    """Returns list of missing texture PNG refs."""
    refs = extract_texture_refs(model_path)
    missing = []
    for ref in refs:
        png = TEXTURES / f"{ref}.png"
        if not png.exists():
            missing.append(f"{ref}.png")
    return missing


def main():
    issues = []

    # ── Check every registered block ──
    for bid in sorted(REGISTERED_BLOCKS):
        bs = BLOCKSTATES / f"{bid}.json"
        bm = MODELS / "block" / f"{bid}.json"
        im = MODELS / "item" / f"{bid}.json"
        if not bs.exists():
            issues.append(f"[block] {bid}: MISSING blockstate JSON")
        else:
            for t in check_model(bs):
                issues.append(f"[block] {bid}: blockstate refs missing texture {t}")
        if not bm.exists():
            issues.append(f"[block] {bid}: MISSING block model JSON")
        else:
            for t in check_model(bm):
                issues.append(f"[block] {bid}: block model refs missing texture {t}")
        if not im.exists():
            issues.append(f"[block] {bid}: MISSING item model JSON (no inventory appearance)")
        else:
            for t in check_model(im):
                issues.append(f"[block] {bid}: item model refs missing texture {t}")

    # ── Check every registered item ──
    for iid in sorted(REGISTERED_ITEMS):
        im = MODELS / "item" / f"{iid}.json"
        if not im.exists():
            issues.append(f"[item] {iid}: MISSING item model JSON")
        else:
            for t in check_model(im):
                issues.append(f"[item] {iid}: item model refs missing texture {t}")

    # ── Report ──
    if not issues:
        print("✓ All registered blocks and items have valid models with all textures present.")
        sys.exit(0)

    print(f"❌ {len(issues)} asset issue(s):\n")
    for issue in issues:
        print(f"  • {issue}")

    missing_models = [i for i in issues if "MISSING" in i]
    missing_textures = [i for i in issues if "texture" in i]
    if missing_models:
        print(f"\n  Missing model JSONs: {len(missing_models)}")
    if missing_textures:
        print(f"  Missing texture PNGs: {len(missing_textures)}")

    sys.exit(1)


if __name__ == "__main__":
    main()
