# YouTube-Specific Extension Patterns

YouTube is the #2 search engine and a common extension target. Its SPA architecture uses custom navigation events rather than standard `history.pushState`, and its page structure embeds rich data (captions, chapter markers, channel metadata) in inline JSON.

## SPA Navigation Detection

YouTube fires a custom event on navigation — use this instead of MutationObserver for video-to-video transitions:

```javascript
// Primary: YouTube's own navigation event
document.addEventListener('yt-navigate-finish', () => {
  cleanupUI();
  detectVideo();
});

// Fallback: URL polling via MutationObserver
let lastUrl = window.location.href;
new MutationObserver(() => {
  if (window.location.href !== lastUrl) {
    lastUrl = window.location.href;
    cleanupUI();
    detectVideo();
  }
}).observe(document.body, { childList: true, subtree: true });
```

## Video & Channel Detection

Extract video ID from URL params, wait for the `<video>` element to be ready with duration:

```javascript
function detectVideo() {
  const videoId = new URL(window.location.href).searchParams.get('v');
  if (!videoId) return; // Not a watch page
  waitForPlayer().then(onVideoLoaded);
}

function waitForPlayer() {
  return new Promise(resolve => {
    const check = () => {
      const video = document.querySelector('video');
      if (video?.duration) resolve(video);
      else setTimeout(check, 500);
    };
    check();
  });
}

// Channel ID extraction
function extractChannelId() {
  const link = document.querySelector('ytd-channel-name a');
  const match = link?.getAttribute('href')?.match(/\/(@[\w-]+|channel\/[\w-]+)/);
  return match?.[1] || null;
}
```

## Transcript / Caption Extraction

YouTube embeds caption data in `ytInitialPlayerResponse` on the watch page HTML. Fetch from the background worker (CORS bypass):

```javascript
// background.js
async function handleTranscript(videoId) {
  const resp = await fetch(`https://www.youtube.com/watch?v=${videoId}`, {
    headers: { 'Accept-Language': 'en-US,en;q=0.9' },
  });
  const html = await resp.text();

  const match = html.match(/ytInitialPlayerResponse\s*=\s*(\{.+?\});/);
  const playerResponse = JSON.parse(match[1]);
  const captions = playerResponse?.captions?.playerCaptionsTracklistRenderer?.captionTracks;

  // Prefer English manual, fall back to English auto-gen, then first available
  let track = captions.find(t => t.languageCode === 'en' && t.kind !== 'asr')
    || captions.find(t => t.languageCode === 'en')
    || captions[0];

  const xmlResp = await fetch(track.baseUrl);
  const xml = await xmlResp.text();

  // Parse TimedText XML
  return [...xml.matchAll(/<text[^>]*>([^<]*)<\/text>/g)]
    .map(m => m[1].replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').trim())
    .filter(Boolean)
    .join(' ');
}
```

The content script can also attempt direct extraction (same regex on inline `<script>` tags) as a faster first attempt before falling back to the background proxy.

## SponsorBlock Integration

Public API at `sponsor.adorable.space` — no auth needed. Request segments by video ID:

```javascript
// background.js
async function handleSponsorBlock(videoId) {
  const url = `https://sponsor.adorable.space/api/skipSegments?videoID=${videoId}&categories=["sponsor","selfpromo","interaction"]`;
  const resp = await fetch(url);
  return { segments: await resp.json() };
}
```

Track current time against segments in content script. Auto-skip with `video.currentTime = segment.segment[1]`. Show a skip badge when inside a segment — use a polling interval (~250ms) rather than `timeupdate` events for reliability.

Segment format: `{ category: "sponsor", segment: [startSeconds, endSeconds], UUID: "..." }`

## Per-Creator Speed Preferences

Store a `{ channelId: speed }` map in `chrome.storage.sync`. Apply on video load, save on user speed change:

```javascript
// On video load — apply preference
const preferred = settings.creatorSpeeds[currentChannelId];
if (preferred) document.querySelector('video').playbackRate = preferred;

// On user speed change — save preference
settings.creatorSpeeds[currentChannelId] = speed;
chrome.storage.sync.set({ creatorSpeeds: settings.creatorSpeeds });
```

Display the saved preferences in the popup for user visibility and clearing.

## Chapter Marker Extraction

Two methods, tried in order:

1. **YouTube's chapter renderer** — query `ytd-macro-markers-list-item-renderer` elements, extract time + title
2. **Description fallback** — parse timestamp lines (`MM:SS Title`) from the video description

Chapter seek: `video.currentTime = chapter.timeSeconds`. Highlight the active chapter by polling current time against chapter boundaries every second.

## AI Video Summary Pattern

1. Extract transcript via the method above
2. Build a prompt: `Title: ${title}\n\nTranscript:\n${transcript.slice(0, 12000)}`
3. Route through the standard AI proxy pattern (background worker → LLM API)
4. Request structured output: TL;DR, key points, topics, verdict
5. Render markdown response in a slide-out panel
