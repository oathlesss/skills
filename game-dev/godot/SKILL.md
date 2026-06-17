---
name: godot
description: Godot 4.x game development — project setup, CharacterBody2D movement,
  surface traversal, physics processing order, headless testing, and common pitfalls.
  Use when working on any Godot 4 project (Protect Arachne or other).
---

# Godot 4 Development

## Project setup

```bash
# Create project
mkdir -p project/{scenes,scripts,tests,assets/{art,audio,music}}
# Download Godot binary
curl -sLO "https://github.com/godotengine/godot-builds/releases/download/VERSION-stable/Godot_vVERSION-stable_linux.x86_64.zip"
python3 -c "import zipfile; zipfile.ZipFile('Godot_...zip').extractall('/tmp/godot')"
mv /tmp/godot/Godot_* ~/.local/bin/godot && chmod +x ~/.local/bin/godot
```

Launch: `~/.local/bin/godot --path /path/to/project`

## CharacterBody2D movement patterns

### Standard platformer (screen-space physics)
Gravity always screen-down, movement always screen-X, jump always screen-Y.

```gdscript
extends CharacterBody2D

func _physics_process(delta):
    # Gravity
    if not is_on_floor():
        velocity.y += gravity * delta
    # Movement
    var input_dir := Input.get_axis("move_left", "move_right")
    velocity.x = move_toward(velocity.x, input_dir * walk_speed, accel * delta)
    # Jump with coyote time + jump buffer
    move_and_slide()
```

### Wall/ceiling sticking (`floor_max_angle = PI`)
`move_and_slide()` treats any surface as floor. Keep physics in screen-space
so gravity/jump/movement are always screen-relative — avoids sign errors from
rotated `up_direction` math.

```gdscript
func _ready():
    floor_max_angle = PI  # any surface is floor
```

With this, `is_on_ceiling()` always returns false (everything is treated as floor).
Detect ceiling using `get_last_slide_collision().get_normal()` instead:

```gdscript
func _detect_surface():
    if not is_on_floor(): return
    var n := get_last_slide_collision().get_normal()
    if n.dot(Vector2.DOWN) > 0.7:   # ceiling
    elif n.dot(Vector2.LEFT) > 0.7:  # wall on player's right
    elif n.dot(Vector2.RIGHT) > 0.7: # wall on player's left
    else:                             # floor
```

### Contextual controls per surface
Map A/D differently based on which surface the player is on:

| Surface | A | D |
|---------|---|---|
| Floor/Ceiling | left | right |
| Right wall (x\|) | descend | climb |
| Left wall (\|x) | climb | descend |

Movement on walls uses `velocity.y` (screen-up = climb, screen-down = descend).

### Gravity on walls
Apply gravity on walls so descent is naturally faster than ascent.
Friction must be stronger than gravity at rest to prevent ice-sliding.

```gdscript
# Gravity: airborne + walls (not floor/ceiling)
if not is_on_floor():
    velocity.y += gravity * delta
if is_on_floor() and is_on_wall_surface:
    velocity.y += gravity * delta

# Friction must beat gravity when idle
friction_force = friction * walk_speed * delta  # e.g. 12 * 400 * 0.008 = 38.4
gravity_force = gravity * delta                  # e.g. 1400 * 0.008 = 11.2
# 38.4 > 11.2 → no sliding at rest ✓
```

## Physics processing order ⚠️ CRITICAL

The order of operations in `_physics_process` matters. Surface state (`is_on_floor`,
`is_on_ceiling`, collision normals) is only valid AFTER `move_and_slide()`.
Movement and jump decisions that depend on surface type must account for this.

**Correct order:**
```
1. Capture input (jump_buffer, key-held state)
2. Apply gravity/movement/friction (use previous-frame surface)
3. move_and_slide()       ← surface state updates here
4. Detect surface          ← now current
5. Execute jump/drop       ← surface is known
```

**Common pitfall:** checking `current_surface` before `_detect_surface()` runs.
Since `_detect_surface()` runs after `move_and_slide()`, any check before it
uses the PREVIOUS frame's surface. On the frame the player transitions to a
new surface (e.g., floor → ceiling), the check sees the old surface and fails.

**Fix:** split jump into `_capture_jump_input()` (before physics) and
`_execute_jump()` (after detection). Drop/ceiling-detach goes in
`_execute_jump()` or a separate `_handle_drop()`.

## Common pitfalls

### Sign errors in vector math
When using `up_direction`-relative math, verify with concrete examples:
- `up_direction = Vector2.UP = (0, -1)`
- Tangent (right): `up_direction.rotated(PI/2)` = (1, 0) ✓
- Tangent (wrong): `up_direction.rotated(-PI/2)` = (-1, 0) ✗
- Jump: `velocity += up_direction * impulse` = (0, -600) → UP ✓
- Jump (wrong): `velocity -= up_direction * impulse` = (0, 600) → DOWN ✗

### Godot 4 strict typing
Inline array indexing doesn't infer type:
```gdscript
# ✗ BREAKS
var name := ["A","B","C"][index]

# ✓ Works
var names: Array[String] = ["A","B","C"]
var name: String = names[index]
```

### Git workflow
After building features, commit AND push. The user expects pushed code.
```bash
git add -A && git commit -m "..." && git push origin main
```

## Headless testing

```bash
# Verify project loads
godot --headless --quit

# Run test script (must extend SceneTree, not Node)
godot --headless -s tests/test_player.gd
```

Test script template:
```gdscript
extends SceneTree

func _init():
    # tests run here
    quit(0)  # 0 = pass

func _make_player() -> Node:
    var scene = load("res://scenes/player.tscn")
    var player = scene.instantiate()
    root.add_child(player)
    return player
```

## Project structure
```
project/
├── project.godot
├── scenes/          # .tscn files
├── scripts/         # .gd files
├── tests/           # headless test scripts
└── assets/
    ├── art/
    ├── audio/
    └── music/
```
