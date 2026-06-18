# ZenNotes Internals — Architecture for Extending

Captured from codebase exploration (GitHub: `ZenNotes/zennotes`, v2.3.0, repo id 1207965399).

## Tech Stack

- **Frontend**: React 18.3 + TypeScript + Vite
- **State**: Zustand 5.0 (single store at `packages/app-core/src/store.ts`, ~6000 lines)
- **Styling**: Tailwind CSS
- **Editor**: CodeMirror 6 (with Vim mode via `@replit/codemirror-vim`)
- **Diagrams**: Mermaid 11.4, function-plot, jsxgraph
- **Math**: KaTeX
- **Markdown**: unified/remark/rehype pipeline
- **No graph visualization library** currently in dependencies

## Monorepo Structure

```
apps/
  desktop/      # Electron desktop wrapper
  server/       # Backend (Express/Node)
  web/          # Browser client (Vite SPA)
packages/
  app-core/     # React app — components, store, lib, styles
  bridge-contract/  # TypeScript interfaces for frontend<->backend IPC
  shared-domain/    # Shared types: IPC models, databases, tasks, tags, etc.
  shared-ui/    # Shared UI components
```

The web app is the one running in Docker (`notes.oathless.dev` → `zennotes:7878`). The Docker image is a bundled Node.js app (minimal OS — no `ls`, `cat`, etc. in the container).

## Data Model

### NoteMeta (the core note record)

```typescript
export interface NoteMeta {
  path: string          // Vault-relative POSIX path (e.g. "inbox/My Note.md")
  title: string         // File name without extension
  folder: NoteFolder    // 'inbox' | 'quick' | 'archive' | 'trash'
  siblingOrder: number
  createdAt: number
  updatedAt: number
  size: number
  tags: string[]        // Extracted #tags
  wikilinks: string[]   // Outbound [[wikilink]] targets, unique
  hasAttachments: boolean
  excerpt: string       // First ~200 chars stripped of markdown
  isSymlink?: boolean
}
```

**Key for graph feature**: `wikilinks: string[]` is already populated per-note. No parsing step needed — the data pipeline exists.

### NoteContent extends NoteMeta

```typescript
export interface NoteContent extends NoteMeta {
  body: string  // Raw markdown including frontmatter
}
```

## Wikilink Resolution

The `packages/app-core/src/lib/wikilinks.ts` library handles all wikilink parsing and resolution:

- `extractWikilinkTargets(body)` — parses `[[target]]` from markdown, skips fenced code blocks and inline code
- `resolveWikilinkTarget(notes, target)` — resolves targets against the note index
- `isPathLikeWikilinkTarget(target)` — detects path-style vs title-style wikilinks
- Supports explicit paths (`/path/to/note`), folder-prefixed (`inbox/note`), title matching, and path suffix matching

### ConnectionsPanel

`packages/app-core/src/components/ConnectionsPanel.tsx` already shows:
- **Outgoing links**: notes this note links TO (via `wikilinks`)
- **Backlinks**: notes that link TO this note (via scanning all notes' wikilinks)
- **Mentions**: notes that mention this note's title in body text (not `[[wikilinks]]`)
- Hover previews via `LazyNoteHoverPreview`
- Keyboard navigation (j/k, Enter to open)

## View System

### Virtual Tab Pattern

Views like Tags, Tasks, Help, Trash, Archive use `zen://` scheme virtual paths:

```typescript
export const TAGS_TAB_PATH = 'zen://tags'
export const HELP_TAB_PATH = 'zen://help'
export const TASKS_TAB_PATH = 'zen://tasks'
export const TRASH_TAB_PATH = 'zen://trash'
```

A graph view would follow the same pattern: `zen://graph`.

Views are opened/closed via store methods (`openTagView`, `closeTagView`, etc.) that add/remove tabs from the pane layout tree. Each leaf pane holds a tab list + active tab.

### Store Structure (Key Fields for Graph)

```typescript
interface Store {
  notes: NoteMeta[]           // All notes in the vault (with wikilinks!)
  noteContents: Record<string, NoteContent>  // Loaded note bodies
  selectNote: (path: string) => void         // Navigate to a note
  paneLayout: PaneLayout                     // Split pane tree
  activePaneId: string
  // ... many more fields
}
```

## Graph Feature Feasibility

### Already Done (no code needed)
- Wikilink extraction and resolution
- Backlink/mention computation (in ConnectionsPanel)
- Note navigation (selectNote)
- Hover previews (LazyNoteHoverPreview)
- Virtual tab infrastructure (zen:// scheme)

### What to Build
1. **Layout**: Force-directed graph with d3-force (~9KB gzipped, fits the stack)
2. **Rendering**: Canvas (performance) or SVG (easier interaction)
3. **Component**: New `GraphView` component + `zen://graph` tab registration
4. **Store integration**: Read `notes[]` → build adjacency map from `wikilinks` → run force simulation

### Integration Points
- Add `zen://graph` virtual tab path in shared-domain (like tags.ts)
- Add `openGraphView` / `closeGraphView` store methods
- Wire into command palette and sidebar
- Keyboard shortcut (e.g., Ctrl+G)

### Dependencies to Consider
- `d3-force` — ~9KB gzipped, force simulation only (you do the rendering)
- `cytoscape.js` — ~150KB, full graph toolkit (overkill for v1)
- No C++/WASM dependencies needed — existing Vite bundler handles everything

## ZenNotes Docker Container

- Image: `ghcr.io/zennotes/zennotes` (built from `ZenNotes/zennotes`)
- Base: minimal (no shell tools inside — `docker exec zennotes ls` fails)
- Vault mount: `/workspace` inside container = `/home/ruben/obsidian-vault` on host
- Auth: Bearer token via `ZENNOTES_AUTH_TOKEN` env var, session cookie after first login
- Port: 7878 internally, proxied through Caddy at `notes.oathless.dev`
