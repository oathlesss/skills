# agent-browser — command reference (condensed)

Ref-based model: `snapshot` prints an accessibility tree; every element gets a `@eN` ref
that you pass straight to `click`/`fill`/`type`/`get`. Deterministic, no selectors.

## Navigation & session
- `agent-browser open [url]` — launch (about:blank if no url) or navigate (aliases `goto`, `navigate`)
- `agent-browser read [url]` — agent-readable text of page, or rendered DOM of active tab
- `agent-browser snapshot` — accessibility tree with refs
- `agent-browser close`
- `agent-browser back` / `forward` / `reload`

## Interaction
- `agent-browser click <sel|@ref>` (`--new-tab` to open in new tab)
- `agent-browser dblclick <sel>`
- `agent-browser focus <sel>`
- `agent-browser type <sel> <text>` — type without clearing
- `agent-browser fill <sel> <text>` — clear + fill
- `agent-browser press <key>` — `Enter`, `Tab`, `Control+a`
- `agent-browser get text <@ref>` / `get url` / `get title` / `get html`
- `agent-browser find role button click --name "Submit"` — role-based selection
- `agent-browser find text "foo"` — locate by visible text

## Observation
- `agent-browser screenshot [path.png]` — headless mode hides native scrollbars by default (`--hide-scrollbars false` to keep)
- `agent-browser record` / video / streaming / profiler / diff (debugging tools)

## Selectors
- Refs from snapshot: `@e1`, `@e2`…
- Traditional CSS: `#id`, `.class`
- Coverage guard: click fails if another element overlaps the target point — dismiss the cover (banner/modal), re-snapshot, retry.

## Modes
- CLI is the primary interface (drive from `terminal`).
- MCP mode exists (`--mcp`, tool profiles `--tools core|all|network,react`). CLI is preferred — MCP re-adds the token overhead the tool exists to avoid.
