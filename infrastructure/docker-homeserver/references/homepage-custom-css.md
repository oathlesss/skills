# Homepage Custom CSS — Class Reference & Theming Guide

Last updated: 2025-06-25

## How to Find the Actual CSS Classes

**Do NOT guess at class names.** Homepage uses Tailwind, but the specific `dark:` variant classes are critical. The wrong class selector = the CSS silently does nothing.

**Investigation method:**
1. Go to `https://github.com/gethomepage/homepage/blob/dev/src/components/`
2. Read the JSX source files — they contain the exact `className` strings
3. Key files:
   - `services/item.jsx` — service tiles (`.service-card`, `dark:bg-white/5`)
   - `bookmarks/item.jsx` — bookmark links (`.bookmark a`, `dark:bg-white/5`)
   - `widgets/widget/container.jsx` — info widgets (`.widget-container`, `dark:bg-white/5`)
   - `pages/index.jsx` — page layout, header styles, wrapper structure
   - `bookmarks/group.jsx` — group headers (`.bookmark-group-name`, `dark:text-theme-300`)

Note: Tailwind `dark:` is a **prefix** applied at runtime — the JSX only shows the dark variant class string, not two separate light/dark sets. When the `theme: dark` setting is active, the `<html class="dark">` selector activates all `dark:`-prefixed classes.

## Actual CSS Classes Used by Homepage (Dark Mode)

| Element | Component Class | Dark Background | Dark Text | Hover Background |
|---------|----------------|-----------------|-----------|-----------------|
| Service tile | `.service-card` | `dark:bg-white/5` | `dark:text-theme-200` | `dark:hover:bg-white/10` |
| Bookmark link | `.bookmark a` | `dark:bg-white/5` | `dark:text-theme-200` | `dark:hover:bg-white/10` |
| Info widget | `.widget-container` | `dark:bg-white/5` | varies | varies |
| Group header | `.bookmark-group-name` | — | `dark:text-theme-300` | — |
| Tab bar | `#tabs ul` | `dark:bg-white/5` | — | — |
| Header (boxed) | `#information-widgets` | `dark:bg-white/5` | — | — |
| Header (boxedWidgets) | `#information-widgets` | no bg | — | — |
| Page body | `body` | inline style (JS) | — | — |
| Search input | `input` | no class | — | — |
| Status dots | — | — | `text-green-500` etc | — |

**Critical insight:** `dark:bg-white/5` means `background-color: rgba(255, 255, 255, 0.05)` — a barely-visible 5% white overlay on whatever background is behind it. It is NOT a solid color like `bg-gray-800`. This is why class selectors like `[class*="bg-gray-800"]` never match — that class string does not exist in Homepage's output.

## Working Rose Pine custom.css (Static Background)

```css
/* ── Rose Pine theme for Homepage ── */

/* ── Page background ──
   ⚠️ PITFALL: Targeting `body` alone does NOT work. Homepage's JS clears inline
   body background styles and applies the theme background to `html.dark`,
   `#page_wrapper`, and `#inner_wrapper`. Target ALL of them. */
html.dark,
html.dark body,
#page_wrapper,
#inner_wrapper {
  background: linear-gradient(135deg, #191724 0%, #1f1d2e 40%, #191724 100%) !important;
  background-attachment: fixed !important;
}

/* ── Cards (services, bookmarks, info widgets) ── */
.dark .service-card,
.dark .bookmark a,
.dark .widget-container {
  background-color: #1f1d2e !important;
  border: 1px solid #26233a !important;
  color: #e0def4 !important;
  transition: background-color 0.15s ease, border-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
}

.dark .service-card:hover,
.dark .bookmark a:hover,
.dark .widget-container:hover {
  background-color: #26233a !important;
  border-color: #6e6a86 !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
}

/* ── Group headers ── */
.dark .bookmark-group-name,
.dark h2 {
  color: #c4a7e7 !important;
}

/* ── Header/info widgets area (boxedWidgets has no bg, but boxed does) ── */
.dark #information-widgets[class*="bg-"] {
  background-color: #1f1d2e !important;
}

/* ── Links ── */
.dark a {
  color: #9ccfd8 !important;
}
.dark a:hover {
  color: #ebbcba !important;
}

/* ── Search input ── */
.dark input {
  background-color: #26233a !important;
  color: #e0def4 !important;
  border-color: #6e6a86 !important;
}
.dark input::placeholder {
  color: #6e6a86 !important;
}

/* ── Status indicators ── */
.dark .text-green-500,
.dark .text-green-400 {
  color: #31748f !important;
}
.dark .text-red-500,
.dark .text-red-400 {
  color: #eb6f92 !important;
}
.dark .text-yellow-500 {
  color: #f6c177 !important;
}

/* ── Resource usage bars ── */
.dark [class*="bg-green-"] {
  background-color: #31748f !important;
}
.dark [class*="bg-amber-"],
.dark [class*="bg-yellow-"] {
  background-color: #f6c177 !important;
}
.dark [class*="bg-red-"] {
  background-color: #eb6f92 !important;
}
```

## Animated Background Variant

Replace the static `/* Page background */` block above with this for a slowly shifting gradient:

```css
@keyframes rpShift {
  0%   { background-position: 0% 50%; }
  25%  { background-position: 50% 100%; }
  50%  { background-position: 100% 50%; }
  75%  { background-position: 50% 0%; }
  100% { background-position: 0% 50%; }
}

html.dark,
html.dark body,
#page_wrapper,
#inner_wrapper {
  background: linear-gradient(135deg, #191724, #1f1d2e, #232136, #191724);
  background-size: 400% 400%;
  animation: rpShift 20s ease infinite;
  background-attachment: fixed !important;
}
```

## Per-Group Header Colors

When different accent colors are wanted per service group (e.g. Infrastructure in iris, Services in foam):

```css
/* Infrastructure tab — first group → iris (purple) */
#services > div:first-child h2,
#layout-groups > div:first-child h2 {
  color: #c4a7e7 !important;
}

/* Services tab — second group → foam (teal) */
#services > div:nth-child(2) h2,
#layout-groups > div:nth-child(2) h2 {
  color: #9ccfd8 !important;
}
```

Note: nth-child selectors depend on DOM order. When tabs are used, groups render inside `#layout-groups` not `#services`. When tabs are NOT used, they render inside `#services`. Target both to be safe.

## Tab Bar Styling

```css
.dark #tabs ul {
  background-color: #1f1d2e !important;
  border: 1px solid #26233a !important;
}
```

## Rose Pine Palette Reference

| Token | Hex | Usage |
|-------|-----|-------|
| Base | `#191724` | Page background |
| Surface | `#1f1d2e` | Card backgrounds |
| Overlay | `#26233a` | Card hover, search input bg |
| Text | `#e0def4` | Body text on cards |
| Subtle | `#908caa` | Secondary text |
| Muted | `#6e6a86` | Borders, placeholder text |
| Iris | `#c4a7e7` | Group headers |
| Foam | `#9ccfd8` | Links |
| Rose | `#ebbcba` | Link hover |
| Love | `#eb6f92` | Red status dots, danger |
| Gold | `#f6c177` | Yellow/warning |
| Pine | `#31748f` | Green status dots, resource bars |

## Common Pitfalls

1. **`dark:bg-white/5` is a 5% white overlay, not a solid color** — overriding it requires `background-color: <color> !important`, not just `background:` (the shorthand doesn't always win specificity against Tailwind atomic classes)

2. **`!important` is almost always necessary** — Homepage's Tailwind atomic classes have high specificity

3. **`body` alone does NOT work for page background** — Homepage's JS clears inline `body.style.background*` in a `useEffect`. The actual background element is `html.dark` (with `scheme-dark` and `theme-slate` classes), plus wrapper divs `#page_wrapper` and `#inner_wrapper`. Always target all four: `html.dark, html.dark body, #page_wrapper, #inner_wrapper`.

4. **`headerStyle: boxedWidgets` gives the header area NO background** — the individual widgets (`.widget-container`) each have their own backgrounds. Targeting `#information-widgets` for background only works with the `boxed` header style

5. **CSS changes require a container restart** — `docker compose restart homepage`. Homepage does NOT hot-reload custom.css from disk.

6. **Verify with hard refresh** — browser caching (especially of CSS files) can make it look like changes didn't take. Ctrl+Shift+R after restart.

## Forgejo Custom API Widget (Private Repos)

Private Forgejo repos return empty `[]` from unauthenticated API calls. A Forgejo API token with `read:repository` scope is required:

1. Generate token at `git.oathless.dev` → Settings → Applications → Generate Token
2. Add as a Homepage custom API widget in `widgets.yaml`:

```yaml
- customapi:
    url: https://git.oathless.dev/api/v1/users/oathless/events?limit=1
    headers:
      Authorization: "token <forgejo-token>"
    mappings:
      - field: "0.payload.commits.0.message"
        label: "Latest commit"
        format: text
      - field: "0.repo.name"
        label: "Repo"
        format: text
      - field: "0.created_at"
        label: "When"
        format: relativeDate
```

The `relativeDate` format shows "3 hours ago" style timestamps. For a specific repo's latest commit instead of cross-repo events, use:
```
https://git.oathless.dev/api/v1/repos/oathless/<repo>/commits?limit=1
```
