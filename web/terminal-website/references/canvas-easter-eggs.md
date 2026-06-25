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

Size canvas to container, run setInterval for the animation, setTimeout for cleanup:

```js
function startMatrixRain() {
  matrixActive.value = true
  applyTheme('matrix')  // optional: switch theme

  nextTick(() => {
    const canvas = matrixCanvas.value
    const container = canvas.parentElement
    canvas.width = container.clientWidth
    canvas.height = container.clientHeight
    // ponytail: no resize observer — this runs once per invocation

    const ctx = canvas.getContext('2d')
    const chars = '日ﾊﾐﾋｰｳｼﾅﾓﾆｻﾜﾂｵﾘｱﾎﾃﾏｹﾒｴｶｷﾑﾕﾗｾﾈｽﾀﾇﾍ0123456789'
    const fontSize = 14
    const columns = Math.floor(canvas.width / fontSize)
    const drops = new Array(columns).fill(0)

    const draw = () => {
      // Semi-transparent black for trail effect
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = '#00ff41'
      ctx.font = `${fontSize}px monospace`

      for (let i = 0; i < drops.length; i++) {
        const char = chars[Math.floor(Math.random() * chars.length)]
        ctx.fillText(char, i * fontSize, drops[i] * fontSize)
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
          drops[i] = 0
        }
        drops[i]++
      }
    }

    const interval = setInterval(draw, 40)  // ~25fps

    matrixTimer.value = setTimeout(() => {
      clearInterval(interval)
      // Fade to solid color
      let opacity = 0
      const fadeOut = setInterval(() => {
        opacity += 0.05
        ctx.fillStyle = `rgba(13, 13, 13, ${opacity})`
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        if (opacity >= 1) {
          clearInterval(fadeOut)
          matrixActive.value = false
          lines.value = []
        }
      }, 30)
    }, 8000)
  })
}
```

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
