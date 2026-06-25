# Tab Completion

Command tab completion in a terminal website, using a `GET /api/commands` endpoint to fetch the available command list.

## Backend: Command List Endpoint

Expose the registry's command names at `GET /api/commands`:

```go
// In api.go
func (a *API) HandleCommands(w http.ResponseWriter, r *http.Request) {
    writeJSON(w, http.StatusOK, a.registry.Available())
}

// In commands.go — Available() returns all registered command names
func (r *Registry) Available() []string {
    names := make([]string, 0, len(r.commands))
    for k := range r.commands {
        names = append(names, k)
    }
    return names
}

// Route in main.go
mux.HandleFunc("GET /api/commands", api.HandleCommands)
```

## Frontend: Completion Logic

### Fetch on Mount

```js
const availableCommands = ref([])

onMounted(async () => {
  try {
    const res = await fetch('/api/commands')
    availableCommands.value = await res.json()
  } catch {
    // ponytail: fallback to empty, tab just won't work
  }
})
```

### Word Boundary Detection

Find the word under the cursor by scanning backward/forward for spaces:

```js
function doCompletion() {
  const input = hiddenInput.value
  const pos = input.selectionStart
  const val = inputValue.value

  // Find word boundaries around cursor
  let start = pos
  while (start > 0 && val[start - 1] !== ' ') start--
  let end = pos
  while (end < val.length && val[end] !== ' ') end++

  const partial = val.slice(start, end).toLowerCase()
  const matches = availableCommands.value.filter(c => c.startsWith(partial))
  // ...
}
```

### Three Outcomes

```js
// 1. No matches — dismiss silently
if (matches.length === 0) {
  showSuggestions.value = false
  return
}

// 2. Single match — autocomplete inline
if (matches.length === 1) {
  const before = val.slice(0, start)
  const after = val.slice(end)
  inputValue.value = before + matches[0] + after
  nextTick(() => {
    // ponytail: setTimeout for cursor after Vue reactivity
    input.setSelectionRange(start + matches[0].length, start + matches[0].length)
  })
  showSuggestions.value = false
  return
}

// 3. Multiple matches — show dropdown, cycle on repeated Tab
if (showSuggestions.value && suggestions.value.length === matches.length) {
  // Same match set as last time → cycle selection
  selectedSuggestion.value = (selectedSuggestion.value + 1) % matches.length
  return
}

// New or different match set → fresh suggestions
suggestions.value = matches
selectedSuggestion.value = 0
tabWordStart.value = start
showSuggestions.value = true
```

### Suggestion Selection

When user picks a suggestion (Tab with dropdown visible, or click):

```js
function selectSuggestion(cmd) {
  const val = inputValue.value
  const start = tabWordStart.value
  const input = hiddenInput.value
  let end = input ? input.selectionStart : val.length
  while (end < val.length && val[end] !== ' ') end++

  inputValue.value = val.slice(0, start) + cmd + val.slice(end)
  showSuggestions.value = false
  nextTick(() => {
    if (input) input.setSelectionRange(start + cmd.length, start + cmd.length)
    focusInput()
  })
}
```

### Key Handling Order

Suggestion navigation must be checked FIRST in `handleKeydown`, before history arrows:

```js
function handleKeydown(e) {
  if (showSuggestions.value) {
    if (e.key === 'ArrowDown') { /* cycle down */ return }
    if (e.key === 'ArrowUp')   { /* cycle up */   return }
    if (e.key === 'Escape')    { dismiss();        return }
    if (e.key === 'Tab')       { select current;   return }
    dismissSuggestions()  // any other key dismisses
  }
  // ... normal Enter, history arrows, Tab trigger, Ctrl+L
}
```

### Suggestion Dropdown Template

Absolute-positioned div below the input, matching terminal colors:

```html
<div
  v-if="showSuggestions && suggestions.length"
  class="absolute left-0 mt-1 z-20 rounded border"
  :style="{
    background: 'var(--rp-surface)',
    borderColor: 'var(--rp-overlay)',
    minWidth: '200px'
  }"
>
  <div
    v-for="(s, idx) in suggestions"
    :key="s"
    class="px-3 py-1 cursor-pointer font-mono text-sm"
    :class="{ 'bg-[var(--rp-overlay)]': idx === selectedSuggestion }"
    :style="{ color: idx === selectedSuggestion ? 'var(--rp-text)' : 'var(--rp-subtle)' }"
    @mousedown.prevent="selectSuggestion(s)"
  >
    {{ s }}
  </div>
</div>
```

Use `@mousedown.prevent` (not `@click`) to prevent the input from losing focus before the selection fires.

## Pitfalls

- **Cursor position after autocomplete**: Vue reactivity may not have flushed the DOM update when you call `setSelectionRange`. Wrap in `nextTick()`.
- **`mousedown` vs `click`**: `@click` loses focus to the clicked element before the handler runs, so the input blurs. `@mousedown.prevent` keeps focus.
- **Key order**: The suggestion-blocking keys (ArrowUp/Down, Esc, Tab) must be checked before the history-ArrowUp handler, or suggestions get dismissed when the user tries to navigate them.
