# Canvas Easter Egg Animations

Triggered by special response types from the backend (`"matrix"`, `"fireworks"`, etc.). A canvas element overlays the terminal, runs an animation loop, then cleans itself up.

## Backend: Special Response Type

Define a command that returns a custom type:

```go
func (r *Registry) matrix(args []string) Response {
    return Response{
        Output: "follow the white rabbit...",
        Type:   "matrix",
    }
}
```

Register the type in the pipeline handler so pipes don't eat it:

```go
// In executePipeline — add to special-types check
if result.Type == "clear" || result.Type == "matrix" || strings.HasPrefix(result.Type, "theme:") {
    return result  // propagate immediately, don't treat as error
}
```

## Frontend: Canvas Overlay

### Template

Canvas conditionally rendered as an absolute overlay on the terminal div:

```html
<div class="terminal ... relative">
  <canvas
    v-if="matrixActive"
    ref="matrixCanvas"
    class="absolute inset-0 z-10 pointer-events-none"
  ></canvas>
  <!-- ... rest of terminal -->
</div>
```

Key points:
- `relative` on the terminal container so the canvas positions correctly
- `absolute inset-0` to fill the terminal
- `pointer-events-none` so clicks pass through to the input
- `z-10` to float above content (make sure suggestion dropdowns use higher z-index)

### Response Handler

Check for the special type in the API response handler:

```js
const data = await res.json()

if (data.type === 'clear') {
  lines.value = []
} else if (data.type === 'matrix') {
  lines.value.push({ type: 'output', text: data.output })
  startMatrixRain()
} else if (data.type && data.type.startsWith('theme:')) {
  // ...
}
```

### Animation Function

Save the current theme before switching (so it can be restored after). Size canvas accounting for `devicePixelRatio` for crisp rendering on high-DPI and mobile screens:

```js
function startMatrixRain() {
  const prevTheme = localStorage.getItem('theme') || 'rose-pine'
  matrixActive.value = true
  applyTheme('matrix')

  nextTick(() => {
    const canvas = matrixCanvas.value
    const container = canvas.parentElement
    const dpr = window.devicePixelRatio || 1
    canvas.width = container.clientWidth * dpr
    canvas.height = container.clientHeight * dpr
    canvas.style.width = container.clientWidth + 'px'
    canvas.style.height = container.clientHeight + 'px'

    const ctx = canvas.getContext('2d')
    ctx.scale(dpr, dpr)  // draw using CSS pixels
    const chars = '日ﾊﾐﾋｰｳｼﾅﾓﾆｻﾜﾂｵﾘｱﾎﾃﾏｹﾒｴｶｷﾑﾕﾗｾﾈｽﾀﾇﾍ0123456789'
    const fontSize = 14
    const columns = Math.floor(container.clientWidth / fontSize)
    const drops = new Array(columns).fill(0)

    const draw = () => {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)'
      ctx.fillRect(0, 0, container.clientWidth, container.clientHeight)
      ctx.fillStyle = '#00ff41'
      ctx.font = `${fontSize}px monospace`

      for (let i = 0; i < drops.length; i++) {
        const char = chars[Math.floor(Math.random() * chars.length)]
        ctx.fillText(char, i * fontSize, drops[i] * fontSize)
        if (drops[i] * fontSize > container.clientHeight && Math.random() > 0.975) {
          drops[i] = 0
        }
        drops[i]++
      }
    }

    const interval = setInterval(draw, 40)

    matrixTimer.value = setTimeout(() => {
      clearInterval(interval)
      let opacity = 0
      const fadeOut = setInterval(() => {
        opacity += 0.05
        ctx.fillStyle = `rgba(0, 0, 0, ${opacity})`
        ctx.fillRect(0, 0, container.clientWidth, container.clientHeight)
        if (opacity >= 1) {
          clearInterval(fadeOut)
          applyTheme(prevTheme)  // restore theme before removing canvas
          lines.value = []
          matrixActive.value = false
        }
      }, 30)
    }, 8000)
  })
}
```

Key: use `container.clientWidth/Height` (not `canvas.width/height`) for all draw calls after scaling — the `ctx.scale(dpr, dpr)` maps CSS pixels to physical pixels, so you draw in CSS coordinates.

## Duration Tuning

- `draw` interval: 30-50ms (20-33fps) — fast enough to look smooth, slow enough to not tank performance
- Total duration: 5-10 seconds — long enough to be fun, short enough visitors stay
- Fade-out: ~20 steps at 30ms intervals = ~600ms fade
- Trail opacity (`rgba(0,0,0,0.05)`): lower = longer trails, higher = faster fade

## Extending

To add another animation type (e.g. `"fireworks"`):
1. Add `"fireworks"` type to the pipeline special-types list
2. Add a `fireworksActive` ref and canvas
3. Add branch in the response handler
4. Write a `startFireworks()` function following the same canvas → interval → timeout pattern
