---
name: youtube-video-summary
description: Extract and summarize any YouTube video from its captions (manual or auto-generated). Use when the user asks to summarize a YouTube video, "what's in this video", or drops a YouTube link wanting a recap.
tags: [youtube, video, summarization, transcript, yt-dlp]
---

# YouTube Video Summarization

Extract captions from a YouTube video and produce a structured summary without watching the video.

## Triggers

- "Summarize this video"
- "What's in this YouTube video?"
- User drops a `youtube.com` or `youtu.be` link asking for a recap
- Any request to extract information from a YouTube video by URL

## Finding Videos

When the user asks for "more videos like this" or "find other videos about X":

```bash
# Search YouTube and get structured results
yt-dlp --flat-playlist --dump-json 'ytsearch10:ATM 10 early game tips' 2>/dev/null | python3 -c "
import json, sys
for line in sys.stdin:
    v = json.loads(line)
    dur = v.get('duration', 0) or 0
    if 0 < dur < 5400:  # Under 90 minutes
        print(f\"{v['id']}|{v['title']}|{v.get('uploader','?')}|{int(dur)//60}m\")
"
```

Filter results by relevance (skip Let's Plays if user wants tip videos, skip already-seen videos, skip excessively long ones).

## Workflow

### 1. Install yt-dlp if needed

```bash
uv pip install yt-dlp
```

### 2. Get video metadata (title, duration, uploader, date)

```bash
yt-dlp --print title --print duration --print uploader --print upload_date '<URL>'
```

If the URL has query parameters (e.g. `?si=...`), strip them or include them — yt-dlp handles both.

### 3. Check available subtitles

```bash
yt-dlp --list-subs '<URL>'
```

Look for:
- **Manual subtitles** (no language suffix like `en-orig`) — highest quality, preferred
- **Auto-generated captions** (`en` in the auto-captions section) — lower quality but usable
- If none exist, tell the user the video has no captions and cannot be summarized without watching it.

### 4. Download the best available English captions

For auto-generated captions:
```bash
yt-dlp --skip-download --write-auto-subs --sub-lang en --output '/tmp/video_subs' '<URL>'
```

For manual subtitles:
```bash
yt-dlp --skip-download --write-subs --sub-lang en --output '/tmp/video_subs' '<URL>'
```

This produces a `.vtt` file (or `.srt` if `--convert-subs srt` is used with ffmpeg available). VTT is plain text and can be parsed directly — no ffmpeg needed.

### 5. Parse the VTT file

Auto-generated VTT files have a specific quirk: **every caption appears twice** — once with word-level timing tags (`<00:00:00.400><c> word</c>`) and once as clean text on the next "cue." You MUST deduplicate consecutive identical lines.

Use this Python pattern:

```python
import re

with open('/tmp/video_subs.en.vtt') as f:
    content = f.read()

lines = content.split('\n')
text_lines = []
for line in lines:
    line = line.strip()
    if not line or line == 'WEBVTT' or line.startswith('Kind:') or line.startswith('Language:'):
        continue
    if '-->' in line or line.startswith('align:'):
        continue
    # Strip HTML/XML tags (word-level timing)
    line = re.sub(r'<[^>]+>', '', line).strip()
    if line and not re.match(r'^\d{2}:', line):
        text_lines.append(line)

# Deduplicate consecutive lines (auto-caption quirk)
deduped = []
for line in text_lines:
    if not deduped or line != deduped[-1]:
        deduped.append(line)

with open('/tmp/video_text.txt', 'w') as f:
    f.write(' '.join(deduped))
```

### 6. Chunk and read

Long videos (30+ min) produce 50K+ characters of text. Chunk into ~15K character pieces:

```python
with open('/tmp/video_text.txt') as f:
    text = f.read()

chunk_size = 15000
for i, start in enumerate(range(0, len(text), chunk_size)):
    with open(f'/tmp/video_chunk_{i}.txt', 'w') as out:
        out.write(text[start:start+chunk_size])
```

Read each chunk with `read_file`, then synthesize a summary.

### 7. Structure the summary

Produce a clear, scannable summary:
- **Title, creator, duration, date** at the top
- **TL;DR** — one-sentence thesis
- **Key sections** with emoji headers for scannability
- **Bullet points** under each section for specific tips/claims
- Don't just list every point — group related ones and highlight the most actionable

## Pitfalls

- **VTT duplication**: Auto-generated captions repeat every line twice. If you don't deduplicate, the summary will read like gibberish with doubled text.
- **No subtitles at all**: Some videos have no captions. Tell the user plainly — don't try to fabricate a summary from metadata alone.
- **JS runtime warning**: yt-dlp may warn about missing JavaScript runtime. This is safe to ignore for subtitle-only extraction.
- **ffmpeg missing**: yt-dlp may warn about ffmpeg not found. Only matters for format conversion (SRT). VTT is fine as-is.
- **Long videos**: A 45-minute video produces ~500KB of VTT and ~58K chars of deduplicated text. Always chunk.
- **Auto-caption quality**: YouTube's speech-to-text makes errors, especially with mod names, technical terms, and fast speech. Flag uncertainty when the transcript seems garbled.
- **Modpack videos may show mods not in the pack**: YouTubers often manually add mods to their instance and present tips as if they're vanilla-pack features. When summarizing a video about a specific modpack, cross-check named mods against the pack's official modlist (GitHub repo, CurseForge/Modrinth manifest) before presenting those mods as part of the pack. Failing to do this produces misleading summaries that erode user trust.
- **Language selection**: Default to `en`. If the user asks for another language, use that language code instead.

### 8. Batch processing (multiple videos)

When the user wants several videos summarized, download all captions in parallel:

```bash
cd /tmp && for vid in VID_ID1 VID_ID2 VID_ID3; do
  yt-dlp --skip-download --write-auto-subs --sub-lang en --output \"/tmp/\${vid}\" \"https://youtu.be/\${vid}\" 2>&1 | grep -E '(Downloading|ERROR|Writing|has no)'
done
```

Process each VTT with the same parse→deduplicate→chunk→read pipeline. Videos under 20 minutes can usually be read in one pass without chunking.

## Verification

- The summary should capture the main thesis and structure of the video
- Technical terms and proper nouns should be preserved even if the auto-captions garbled them
- Group related points — a video with "50 tips" should group them by theme, not list all 50
