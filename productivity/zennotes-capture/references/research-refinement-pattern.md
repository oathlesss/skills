# Research Refinement Pattern — Multi-Round Research → Progressive Notes

## The Pattern

Ruben often does research in rounds:

1. **Round 1: Overview.** Broad question → broad answer. Save a summary note.
2. **Round 2: Deep-dive.** "Extend this research, go into more detail." → detailed answer with code/examples. **Replace or expand the same note** — don't create a second one.

The same note file gets progressively enriched across rounds. This is correct behavior — one topic, one note, growing in depth.

## Example from This Session

```
Round 1: "Can you do research about creating minecraft modpacks and mods?"
  → Note: minecraft-modding-modpack-research-2026.md (6.5KB overview)

Round 2: "Extend this research, go into more detail of the process"
  → SAME note, replaced: minecraft-modding-modpack-research-2026.md (39KB deep-dive)
  
Round 3: "Research recreating Thaumcraft, separate note"
  → NEW note: recreating-thaumcraft-research-2026.md (24KB)
  
Round 4: "Work out a plan for this, use meta prompting"
  → NEW note: project-arcanum-plan.md (39KB project plan)
```

## When to Merge vs Split

- **Same topic, deeper dive** → replace the same note file (or patch it)
- **Distinctly different topic** → new note file
- **Sub-topic that branches into its own thing** → new note file (e.g., Thaumcraft recreation plan is a separate concern from general modding research)

## The Critical Failure Mode

The #1 failure: delivering research in chat but forgetting to write the note. The skill's self-check is designed to prevent this. If you use `delegate_task` or `web_search` and your answer is more than a paragraph, the note MUST be written before you send your final summary turn.
