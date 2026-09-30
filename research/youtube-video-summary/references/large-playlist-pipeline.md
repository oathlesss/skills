# Large Playlist / Full-Series Summarization Pipeline

Proven on a 24-episode modpack series (~800K chars total transcript). Use whenever a user
drops a full playlist and wants a synthesized deliverable (e.g. a step-by-step progression guide).

## Phase 0 — Resolve the playlist (handles truncated/shared URLs)

The URL may arrive truncated (Discord cuts long URLs) or with `watch?v=...&list=...`. Both work:

```bash
# Enumerate every video: id + title. Skip the hidden/unavailable entry (shows as "NA").
yt-dlp --flat-playlist --print "%(id)s ||| %(title)s" '<PLAYLIST_URL>' 2>/dev/null

# Channel/uploader name (flat mode omits it):
yt-dlp --playlist-items 1 --print "%(uploader)s ||| %(channel)s" '<PLAYLIST_URL>' 2>/dev/null
```

## Phase 1 — Download all captions in parallel (NO shell `&`)

Hermes' terminal tool rejects `&` backgrounding in foreground mode. Use `xargs -P`:

```bash
grep -v 'NA' ids.txt | xargs -P 8 -I{} bash -c \
  'yt-dlp --skip-download --write-auto-subs --sub-lang en --output "/tmp/dir/{}" "https://youtu.be/{}" >/dev/null 2>&1'
```

`-P 8` balances speed vs. YouTube rate-limiting. Always `--write-auto-subs` (ChosenArchitect-style
content has no manual subs; auto-captions are the only option).

## Phase 2 — Bulk-parse all VTTs to deduplicated text

One Python pass over every `.vtt`, applying the standard parse rules (strip WEBVTT/headers/timestamps,
strip `<...>` tags, dedup consecutive lines). Write each result as `<id>.txt` and print char counts so
you can spot any 0-char failures. Key pitfall: auto-caption VTTs repeat every line twice — dedup is mandatory.

## Phase 3 — Wrap for reading

Parsed output is single-line and `read_file` truncates single-line files. Wrap each:

```bash
fold -w 110 -s <id>.txt > <id>_wrapped.txt
```

This is essential for subagents too — tell them explicitly to `fold` first, or they waste
calls re-discovering the truncation.

## Phase 4 — Parallel summarization via delegate_task

Batch the episodes (4 per subagent is a sweet spot ≈ ~140K chars ≈ ~35K tokens input per worker).
Max 3 concurrent tasks per user. Two waves for 24 episodes.

Per-task context must be SELF-CONTAINED (subagents have no memory of your conversation):
- Exact file paths + episode number + title for each of the 4 transcripts.
- Explicit instruction: `fold -w 110 -s <file> > <file>_wrapped.txt` first, then read.
- The series name / pack context (e.g. "ATM10 Aeronautics — ChosenArchitect playthrough").
- Output schema (per episode): title, main goals/builds, key mods & items, progression
  milestones, techniques/tips, garbled-caption corrections.

Per-task goal: "Read N transcripts, produce structured progression-focused summary of each."

## Phase 5 — Synthesize

The workers return per-episode summaries. You stitch them into a stage/phase-structured
deliverable. Group episodes into thematic phases (early game → power → storage → automation → endgame),
not a flat per-episode list. End with a one-line "whole progression in one line" recap.

## Garbled-caption handling

Auto-captions mangle mod/item names badly. Instruct workers to flag + best-guess correct terms.
Common families to pre-seed in the instruction context:
- "Ender Corey" → Ender Quarry; "theodium" → Allthemodium; "mechanism" → Mekanism;
  "Ore Attack/Ore Tech" → Oritech; "excessive utilities" → Extra Utilities 2 / Excess Utilities;
  "star bunkles" → Starbuncles; "Celesti gym" → Celestigem; "ours Novo" → Ars Nouveau.
