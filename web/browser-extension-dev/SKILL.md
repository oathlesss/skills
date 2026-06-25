---
name: browser-extension-dev
description: Scaffold, build, and test Chrome/Firefox browser extensions (Manifest V3). Use for any extension that injects UI into pages, proxies API calls, or enhances browsing with a popup settings panel.
triggers:
  - "chrome extension"
  - "browser extension"
  - "manifest v3"
  - "content script"
  - regex: /(?:build|create|scaffold|write) (?:a |an )?(?:chrome|browser|firefox) extension/i
---

# Browser Extension Development

Pattern for building Chrome/Chromium extensions with Manifest V3. Pure vanilla JS — no frameworks, no build step, no bundler.

## Architecture

Three components that work together:

```
┌─────────────────┐     message      ┌──────────────────┐     fetch      ┌─────────────┐
│  content.js     │ ──────────────→  │  background.js   │ ───────────→  │  API/LLM    │
│  (page context) │ ←──────────────  │  (service worker) │ ←───────────  │  endpoint   │
└─────────────────┘     response     └──────────────────┘               └─────────────┘
       │
       │ chrome.storage.sync
       ▼
┌─────────────────┐
│  popup.html/js  │
│  (settings UI)  │
└─────────────────┘
```

- **Content script** — injected into pages. Adds UI elements (buttons, search bars, toggles). Communicates with background worker via `chrome.runtime.sendMessage`. Reads/writes settings via `chrome.storage.sync`.
- **Background service worker** — proxies API calls that content scripts can't make directly (CORS bypass). Listens for messages, makes `fetch` calls, returns results.
- **Popup** — settings UI shown when user clicks the extension icon. Saves to `chrome.storage.sync`. Changes are picked up by content scripts via `chrome.storage.onChanged`.

## Project structure

```
my-extension/
├── manifest.json      # Manifest V3 — permissions, content_scripts, background, action
├── content.js         # Injected into pages — UI injection, user interaction
├── content.css        # Styles for injected elements (referenced in manifest)
├── background.js      # Service worker — API proxying, long-lived state
├── popup.html         # Popup UI
├── popup.js           # Popup logic — load/save settings
├── icons/             # icon16.png, icon48.png, icon128.png
├── README.md
└── .gitignore
```

## Manifest V3 template

```json
{
  "manifest_version": 3,
  "name": "...",
  "version": "0.1.0",
  "description": "...",
  "permissions": ["storage", "activeTab"],
  "host_permissions": ["https://api.example.com/*"],
  "action": {
    "default_popup": "popup.html",
    "default_title": "..."
  },
  "content_scripts": [{
    "matches": ["<all_urls>"],
    "js": ["content.js"],
    "css": ["content.css"],
    "run_at": "document_end"
  }],
  "background": {
    "service_worker": "background.js",
    "type": "module"
  },
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

Key Manifest V3 notes:
- `background.service_worker` replaces Manifest V2's `background.scripts`
- `host_permissions` are required for fetch in background workers
- `"type": "module"` enables ES module syntax in the service worker
- `"run_at": "document_end"` ensures DOM is ready before content script runs

## Content script patterns

### Injecting UI elements

Always guard with an ID check to avoid duplicates on SPA navigations:

```javascript
if (document.getElementById('my-extension-widget')) return;
const el = document.createElement('div');
el.id = 'my-extension-widget';
document.body.appendChild(el);
```

### Watching for dynamic content

Use MutationObserver for SPAs that load content after initial render:

```javascript
const observer = new MutationObserver(() => {
  if (document.querySelectorAll('pre:not(.my-ext-processed)').length > 0) {
    addCopyButtons();
  }
});
observer.observe(document.body, { childList: true, subtree: true });
```

### Communicating with background worker

Content scripts can't make cross-origin fetch calls. Route through the background worker:

```javascript
// content.js
chrome.runtime.sendMessage(
  { type: 'api-call', endpoint, headers, body },
  (response) => { /* handle result */ }
);
// Must return true to keep the port open for async response
```

```javascript
// background.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'api-call') {
    handleCall(message).then(sendResponse);
    return true; // Keep channel open for async
  }
});
```

### Settings via chrome.storage

```javascript
// Load on init
chrome.storage.sync.get({ key: 'default' }, (items) => { /* use items */ });

// Listen for changes from popup
chrome.storage.onChanged.addListener((changes) => {
  for (const [key, { newValue }] of Object.entries(changes)) {
    settings[key] = newValue;
  }
});

// Save from popup
chrome.storage.sync.set({ key: value });
```

## Dark mode injection

Two approaches:

**1. Filter-based (simplest, works on any site):**
```css
html.dark { filter: invert(0.88) hue-rotate(180deg); }
html.dark img, html.dark video { filter: invert(1) hue-rotate(180deg); }
```
- Pros: Works on every site, no per-site CSS needed
- Cons: Performance overhead on large pages, may look slightly off on some sites

**2. CSS variable injection (cleaner, needs per-site tuning):**
Inject a stylesheet that overrides `--bg`, `--text`, etc. Works best on sites that use CSS variables.

Use filter-based for MVP, CSS variables for polish.

## AI search pattern

The pattern for "AI-powered search over current page content":

1. Content script captures page context (URL, title, main content text)
2. User types query into injected search bar
3. Content script builds a prompt combining page context + user query
4. Sends to background worker via `chrome.runtime.sendMessage`
5. Background worker calls the LLM API (OpenAI/Anthropic/OpenRouter)
6. Result flows back to content script for display

Multi-provider support in the background worker:
```javascript
async function handleAIQuery(endpoint, headers, body) {
  const resp = await fetch(endpoint, { method: 'POST', headers, body });
  const data = await resp.json();
  // Parse OpenAI format: data.choices[0].message.content
  // Parse Anthropic format: data.content.filter(b => b.type === 'text')
  return { text: extractedText };
}
```

## Icons

Extension requires 16x16, 48x48, and 128x128 PNG icons. If no image tools are available, generate with pure Python — see `references/png-icon-generation.md`.

A ready-to-copy manifest template is at `templates/manifest-v3.json`.

For YouTube-specific patterns (SPA navigation, transcript extraction, SponsorBlock, per-creator preferences): see `references/youtube-patterns.md`.

## Installation & testing

1. Go to `chrome://extensions/`
2. Enable "Developer mode" (toggle top-right)
3. Click "Load unpacked" and select the extension directory
4. After changes: click the refresh icon on the extension card
5. Check "Errors" button on the extension card for console errors

To test programmatically: load the extension and visit any page. The content script fires automatically.

## Pitfalls

- **SPA navigations** — content scripts only fire on full page loads. Use MutationObserver or listen for `history.pushState` for SPA-routed pages. For YouTube specifically, listen for the `yt-navigate-finish` custom event (see `references/youtube-patterns.md`).
- **CORS in content scripts** — `fetch()` from content scripts is subject to the page's CORS policy. Always route API calls through the background worker.
- **Service worker lifecycle** — background workers are terminated after 30s of inactivity. Don't store state in memory; use `chrome.storage`.
- **Manifest host_permissions** — you need `host_permissions` (not just `permissions`) for `fetch()` in the background worker to work in Manifest V3.
- **Icon requirements** — Chrome requires exactly 16x16, 48x48, and 128x128 PNGs. Missing sizes = extension won't load.
- **content.css in manifest** — the `css` field in `content_scripts` injects styles before JS runs. Use it for base styles to avoid FOUC (flash of unstyled content). Dynamic styles can still be injected via JS.
- **Return true for async** — when using `sendResponse` asynchronously in `chrome.runtime.onMessage`, you MUST `return true` from the listener to keep the message port open. Forgetting this = response never arrives.
