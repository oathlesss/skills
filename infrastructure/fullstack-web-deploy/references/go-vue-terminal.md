# Go + Vue Terminal Website Reference

Full implementation details for the oathless.dev terminal website (oathless-terminal).

## Architecture

```
Browser → Vue 3 SPA → POST /api/command → Go backend → Command Registry → JSON response
```

**Frontend**: Custom Vue 3 terminal component (not xterm.js). Handles keyboard input, command history, and theme switching client-side.

**Backend**: Go HTTP server with:
- `POST /api/command` — accepts `{"command": "..."}`, returns `{"output": "...", "type": "text|error|clear|theme:<name>"}`
- `/*` — serves embedded Vue SPA (index.html fallback for all non-API routes)

## Vue Terminal Component

Key patterns in `Terminal.vue`:

```
- Hidden <input> overlaid on the visible prompt span (captures all keystrokes)
- Command history: up/down arrow navigates history array
- Ctrl+L clears screen (handled client-side, no API call)
- `clear` command clears lines array client-side
- `theme` command receives `type: "theme:rose-pine"` from API — theme switch future hook
- Loading state blocks input during API calls
- Auto-scroll via `scrollIntoView` on a bottom ref element
- Initial banner shown only when `lines.length === 0`
```

**⚠️ PITFALL: Input loses focus after `v-if` re-mount.** When the input line uses `v-if="!loading"`, the hidden `<input>` is removed from the DOM during API calls. When `loading` becomes `false` and Vue re-creates the element, the browser has nothing focused — the user has to click to type again. **Fix:** call `focusInput()` after `nextTick()` in the `finally` block:

```js
} finally {
    loading.value = false
    inputValue.value = ''
    await nextTick()
    focusInput()          // re-focus after DOM re-creation
}
```

Without `nextTick`, the focus call fires before Vue has mounted the new input element, so it silently does nothing.

## Go Command Registry Pattern

```go
type Registry struct {
    commands map[string]func(args []string) Response
}

type Response struct {
    Output string `json:"output"`
    Type   string `json:"type"` // "text", "error", "clear", "theme:<name>"
}

func (r *Registry) Execute(name string, args []string) Response {
    cmd, ok := r.commands[name]
    if !ok {
        return Response{Output: "command not found: " + name, Type: "error"}
    }
    return cmd(args)
}
```

Commands are registered in `registerBuiltins()` via `r.register("name", handler)`.

## Rose Pine Theme Colors

```
Base:    #191724  (background)
Surface: #1f1d2e  (cards, panels)
Text:    #e0def4  (primary text)
Subtle:  #908caa  (secondary text, output)
Love:    #eb6f92  (errors, delete)
Gold:    #f6c177  (warnings, loading)
Rose:    #ebbcba  (banner, headings)
Pine:    #31748f  (links, info)
Foam:    #9ccfd8  (highlights, code)
Iris:    #c4a7e7  (prompt, accent)
```

In Tailwind: reference via `var(--rp-iris)` in inline styles. CSS custom properties are scoped to `:root`.

## Deployed Service State

- **Container**: `oathless-terminal` in `/home/ruben/homeserver/docker-compose.yml`
- **Image**: `oathless-terminal:local` (20.8 MB)
- **Caddy**: `oathless.dev` + `www.oathless.dev` → `reverse_proxy oathless-terminal:8080`
- **Uptime Kuma**: HTTP monitor for `https://oathless.dev`
- **Repo**: `github.com/oathlesss/oathless-terminal`
- **Source**: `/home/ruben/oathless-terminal/`

## Rebuilding After Changes

```bash
cd /home/ruben/homeserver
docker compose build oathless-terminal
docker compose up -d oathless-terminal
docker compose restart caddy
```
