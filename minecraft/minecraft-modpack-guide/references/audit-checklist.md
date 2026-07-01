# Guide Audit Procedure

Use this when the user asks to review/audit existing standalone guides for quality.

## Quick Triage: File Size

Run `du -k` on all guides. Anything under 10KB is almost certainly a reference sheet, not a build-along manual. Guides at 20KB+ are candidates for passing — but size alone doesn't guarantee quality (see CC Tweaked at 16KB with zero requirements met).

```bash
cd <vault>/inbox
for f in *"Standalone Guide.md" *"Survival Guide.md"; do
  [ -f "$f" ] && printf "%-55s %6d KB\n" "$f" "$(du -k "$f" | cut -f1)"
done
```

## Requirement Scan: Grep Patterns

Score each guide against the 7 non-negotiable requirements. Run this for each guide:

```bash
f="Guide Name.md"
echo "--- $f ---"
echo -n "Stage headings: "; grep -c '^## Stage' "$f" || echo 0
echo -n "Shopping List: "; grep -ci 'Shopping List\|shopping list' "$f" || echo 0
echo -n "Build-along: "; grep -ci 'Step-by-Step\|Build-Along\|Build-along\|step-by-step' "$f" || echo 0
echo -n "Common Mistakes: "; grep -ci 'Common Mistakes\|common mistakes' "$f" || echo 0
echo -n "Checklist: "; grep -c '\- \[ \]' "$f" || echo 0
echo -n "Pipe/Logistics: "; grep -ci 'Pipe.*Logistics\|transport.*comparison\|Pipez.*LaserIO' "$f" || echo 0
echo -n "ASCII diagrams: "; grep -c '```' "$f" || echo 0  # proxy; spot-check for actual layouts
```

Interpretation:
- **All zeros** → reference sheet. The guide explains what things are but has no build-along structure.
- **Has some hits but not all** → partial. Spot-read to confirm format quality.
- **All 6+ non-zero** → candidate for passing. Spot-read to verify the content is real build-along, not just headers.
- Pipe/Logistics is optional (only for automation mods) — a guide without automation can explicitly note "not applicable."

## Spot-Read Passed Candidates

For guides with non-zero grep hits, read the first 60 lines to verify:
1. Stages are time-tagged (e.g. "Stage 1: Early Game (Hours 0-5)")
2. Shopping lists have exact quantities (not "some Productivity Upgrades" — "4-16 Productivity Upgrades (Basic)")
3. ASCII art is spatial layout (farm diagrams, pipe routing), not just code blocks or informational tables
4. Steps are imperative and sequential

## Duplicate Detection

Check for multiple guides covering the same mod with different filenames (e.g. `AE2 — ATM10 Standalone Guide.md` vs `applied-energistics-2-atm10-standalone-guide.md`). Flag the smaller/older one as superseded. The better-quality guide often has a longer, more specific filename.

## Report Format

Produce a tiered table:

**PASS** — build-along manuals meeting requirements:
| Guide | Size | Stages | Shopping Lists | Build-Along | Mistakes | Checklists | Logistics |

**FAIL** — reference sheets (all zeros on requirements):
| Guide | Size | Content Present? | Problem |

Group by size tier (8KB / 12KB / 16KB+) to make patterns visible.

## Common Audit Findings

### "Has ASCII but they're tables, not layouts"
Guides like Apotheosis score high on the ASCII grep check but the diagrams are informational tables (spawner upgrade tiers, material comparisons), not spatial block-placement layouts. The grep check is a proxy — always spot-read to confirm.

### "Duplicate guide at different quality levels"
AE2 existed as both "AE2 — ATM10 Standalone Guide.md" (12KB, reference) and "applied-energistics-2-atm10-standalone-guide.md" (44KB, build-along). The good one has a less obvious filename. Check for duplicates when you see both a short-name and long-name version of the same mod.

### "16KB but 0/7 scores"
CC Tweaked was 16KB (355 lines) with zero stage headings, shopping lists, or checklists. It was a Lua API reference, not a build-along. Size alone is not a reliable proxy — grep the sections.

### "All 12KB guides are reference sheets"
Experience from ATM10 audit: every guide at exactly 12KB had zero stages, zero shopping lists, zero checklists. They were the exact same reference format produced in a batch. The 12KB tier is consistently reference-only; the 20KB+ tier is where build-alongs begin.
