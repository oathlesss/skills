# Vue Text Highlight Overlay

Technique for highlighting regex matches (or any text spans) inside an editable `<textarea>` — used in regex playgrounds, code editors, search-with-highlights UIs.

## The problem

`<textarea>` doesn't support child elements, so you can't wrap matches in `<mark>` tags directly. Solutions:
- **`contenteditable` div** — brittle, loses textarea-native behaviors (spellcheck, undo, form integration)
- **CodeMirror/Monaco** — heavy dependency for simple highlighting
- **Overlay** — the ponytail approach: stack a read-only highlight `<div>` behind a transparent `<textarea>`

## The overlay approach

```
┌─────────────────────────────┐
│  <div> (highlight layer)    │  ← z-index: 1, position: absolute
│  Text with <mark> spans     │     color: transparent on normal text
│  ┌───────────────────────┐  │
│  │ <textarea> (input)    │  │  ← z-index: 2, position: relative
│  │ bg: transparent       │  │     caret-color: <accent>
│  │ text: <visible color> │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

Both layers share the same `font-family`, `font-size`, `line-height`, `padding`, `white-space: pre-wrap`, and `word-break: break-all` so text aligns perfectly.

## Implementation (Vue 3)

```vue
<template>
  <div class="relative" ref="container" @scroll="syncScroll">
    <!-- Highlight layer (behind) -->
    <div
      v-if="parts.length"
      class="absolute inset-0 px-3 py-2 text-sm font-mono whitespace-pre-wrap break-all pointer-events-none"
      style="color: transparent; z-index: 1;"
    >
      <template v-for="(part, i) in parts" :key="i">
        <mark v-if="part.highlight" class="regex-highlight">{{ part.text }}</mark>
        <span v-else>{{ part.text }}</span>
      </template>
    </div>

    <!-- Input layer (front) -->
    <textarea
      v-model="text"
      @scroll="syncScroll"
      class="w-full bg-transparent ..."
      style="position: relative; z-index: 2; caret-color: #c4a7e7;"
    />
  </div>
</template>
```

### Building the parts array

```js
const parts = computed(() => {
  if (!text.value || !matches.value.length) return []
  const parts = []
  let lastEnd = 0

  // Sort and dedupe overlapping matches (ponytail: first match wins)
  const sorted = [...matches.value].sort((a, b) => a.index - b.index)
  const deduped = []
  for (const m of sorted) {
    if (m.index >= lastEnd) {
      deduped.push(m)
      lastEnd = m.index + m.text.length
    }
  }

  lastEnd = 0
  for (const m of deduped) {
    if (m.index > lastEnd) {
      parts.push({ text: text.value.slice(lastEnd, m.index), highlight: false })
    }
    parts.push({ text: m.text, highlight: true })
    lastEnd = m.index + m.text.length
  }
  if (lastEnd < text.value.length) {
    parts.push({ text: text.value.slice(lastEnd), highlight: false })
  }
  return parts
})
```

### Keeping layers in sync

Both layers must scroll together. Since the textarea's `@scroll` event bubbles, placing both inside the same container and using one scroll event handler keeps them aligned. No JS scroll sync needed — they're naturally stacked.

## Pitfalls

- **`white-space: pre-wrap`** is essential — without it, multi-line text wraps differently on each layer
- **`break-all`** prevents long strings (like base64) from breaking the alignment
- **`pointer-events: none`** on the highlight layer — otherwise clicks land on the wrong element
- **`color: transparent`** on the highlight layer's normal text — the highlight `<mark>` elements provide the only visible color there
- **Overlapping matches** need deduplication — first match wins, otherwise two `<mark>` tags at the same position glitch the DOM
- **Empty pattern or text** — return empty parts array to avoid `slice(0, 0)` noise

## When not to use

- **Syntax highlighting with 50+ token types** — use CodeMirror or Monaco
- **Rich text editing** — use Tiptap or Quill
- **Tiny text (< 1KB) only** — the dual-DOM approach creates ~2× nodes per keystroke; fine for test-text inputs (typical regex testing is < 10KB) but degrades on full documents
