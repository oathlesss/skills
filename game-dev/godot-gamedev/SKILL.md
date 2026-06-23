---
name: godot-gamedev
description: >
  Godot 4.x game development patterns — project setup, scene authoring,
  GDScript conventions, headless testing, and Linux installation. Use for
  any Godot project work such as creating scenes, writing scripts, running
  tests, or setting up a new Godot project.
triggers:
  - Godot game development
  - Godot project setup
  - creating Godot scenes or scripts
  - GDScript
  - running Godot tests
  - installing Godot on Linux
---

# Godot Game Development

Use this skill whenever the user asks to work on a Godot project — creating or editing scenes, writing GDScript, running tests, or setting up Godot itself.

## Tool choice: Godot first

When the user has explicitly chosen Godot as their engine (as in Project Arachne), do NOT fall back to pygame, HTML5 Canvas, or other engines as a workaround for missing dependencies. Install Godot and build in Godot. The user's engine choice is non-negotiable.

## Installing Godot on Linux

Godot 4.x is a single self-contained binary. No package manager needed.

```bash
VERSION=$(curl -sL "https://api.github.com/repos/godotengine/godot-builds/releases/latest" | python3 -c "import json,sys; print(json.load(sys.stdin)['tag_name'])")
curl -sLO "https://github.com/godotengine/godot-builds/releases/download/${VERSION}/Godot_${VERSION}_linux.x86_64.zip"
python3 -c "import zipfile; zipfile.ZipFile('Godot_${VERSION}_linux.x86_64.zip').extractall('/tmp/godot')"
mkdir -p ~/.local/bin
mv /tmp/godot/Godot_*_linux.x86_64 ~/.local/bin/godot
chmod +x ~/.local/bin/godot
```

Verify: `~/.local/bin/godot --version`

## Project structure conventions

```
project-name/
├── project.godot          # Godot 4 project file (config_version=5)
├── scenes/                # .tscn scene files
├── scripts/               # .gd GDScript files
├── tests/                 # Headless test scripts
├── assets/
│   ├── art/
│   ├── audio/
│   └── music/
└── data/                  # JSON data (cards, weapons, etc.)
```

## project.godot essentials

```ini
config_version=5

[application]
config/name="Project Name"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.6")

[display]
window/size/viewport_width=960
window/size/viewport_height=640

[input]
move_left={
"deadzone": 0.2,
"events": [key A, key Left]
}

[physics]
common/physics_ticks_per_second=120
```

## Scene files (.tscn) — critical pitfalls

Godot 4 .tscn files can be authored by hand but have strict formatting:

1. **UIDs are optional and risky**: Use `format=3` without UIDs (`uid://...`) in the header unless you know the exact UID. Mismatched UIDs cause load failures. Better to omit them and let Godot assign on first editor open.

2. **Sub-resources are file-scoped**: `[sub_resource type="RectangleShape2D" id="my_shape"]` — the `id` is local to this .tscn file only. Reusing the same id name in another file is fine. Referencing a sub_resource defined in another file will fail with "Invalid parameter" errors.

3. **External resources use paths, not UIDs**: `[ext_resource type="PackedScene" path="res://scenes/player.tscn" id="1"]` — use the path when manually authoring. Reference with `instance=ExtResource("1")`.

4. **Load steps must be exact**: The `load_steps=N` count must equal `1 + (number of ext_resource entries) + (number of sub_resource entries)`. Wrong count causes parse errors.

5. **Input map keycodes**: A=65, D=68, W=87, S=83, Left=4194319, Right=4194321, Up=4194320, Down=4194322, Space=32.

See `references/scene-examples.md` for a complete CharacterBody2D player scene template.

## After every meaningful code change

1. Verify the project loads: `godot --headless --quit` (must exit 0)
2. Run tests headless: `godot --headless -s tests/test_player.gd`
3. Commit with a descriptive message (active voice, "Fix X" or "Add Y")
4. Push immediately: `git push origin main`

Do not leave un-pushed commits. The user expects changes to be on the remote after you say "done."

### Pre-Commit Hook

Prevent broken commits with a `.git/hooks/pre-commit` that runs build + test:
```bash
#!/bin/bash
set -e
GODOT="${HOME}/.local/bin/godot"

# Verify project loads without errors
"$GODOT" --headless --quit 2>&1 | tail -5

# Run headless tests
"$GODOT" --headless -s tests/test_player.gd
```
This catches both project-load failures (broken .tscn, missing resources) and
test regressions before they reach the remote. Add it early — the hook
pays for itself the first time it blocks a bad commit.

## Pre-commit Hook (strongly recommended)

Automate the verify→test gate so broken commits can't land:

```bash
# .git/hooks/pre-commit
#!/bin/bash
set -e
GODOT="${HOME}/.local/bin/godot"
"$GODOT" --headless --quit 2>&1 | tail -5
if ! "$GODOT" --headless -s tests/test_player.gd 2>&1 | tail -10; then
    echo "❌ Tests failed — commit blocked."
    exit 1
fi
echo "✓ All checks passed — allowing commit."
```

Project Arachne at `/home/ruben/project-arachne` already has this hook installed.

## GDScript movement pitfalls

### `move_toward` on velocity.y cancels gravity

**Never** apply `move_toward` directly to `velocity.y` in a platformer. When airborne with no input, the target y-component is 0, so `move_toward(vy, 0, accel*dt)` pulls `vy` toward zero every frame. If movement acceleration exceeds gravity, the player floats permanently — gravity is cancelled out.

Fix: decompose velocity into the component parallel to intended movement (e.g., the surface tangent) and perpendicular to it. Only accelerate the parallel component:

```gdscript
# WRONG — fights gravity on y axis
velocity.x = move_toward(velocity.x, target.x, accel * delta)
velocity.y = move_toward(velocity.y, target.y, accel * delta)

# CORRECT — only accelerate along intended direction
var tangent_speed := velocity.dot(tangent)
var target_speed := input_dir * walk_speed
var new_speed := move_toward(tangent_speed, target_speed, accel * delta)
velocity += tangent * (new_speed - tangent_speed)
```

### Tangent formula for surface-walking

When computing a surface tangent from a normal, rotate counter-clockwise so flat ground (UP normal) maps to RIGHT:

```gdscript
# CORRECT: Vector2(-normal.y, normal.x) → UP (0,-1) gives RIGHT (1,0)
var tangent := Vector2(-current_normal.y, current_normal.x)
```

The clockwise variant `Vector2(normal.y, -normal.x)` inverts left/right controls.

### Defer surface traversal until the foundation is solid

Surface-walking (flipping gravity to stick to walls/ceilings) adds significant complexity. Don't activate it until the standard platformer (gravity-always-down) feels right. In Project Arachne, surface traversal is Week 3-4 (grapple phase), not Week 1-2 (basic movement).

## GDScript testing (headless)

Godot 4 tests run headless with `--headless -s path/to/test.gd`.

### Test script template

```gdscript
extends SceneTree

func _init() -> void:
	await process_frame   # let engine initialize
	# ... run tests ...
	quit(0)  # 0 = pass, 1 = fail

func _make_player() -> Node:
	var scene: PackedScene = load("res://scenes/player.tscn")
	var player: Node = scene.instantiate()
	root.add_child(player)
	return player
```

### Critical testing pitfalls

1. **Must extend `SceneTree`**, not `Node`. Scripts run via `-s` replace the main loop.

2. **`class_name` does NOT resolve** in `-s` script mode. Use `load("res://scripts/player.gd")` to get the Script resource, or instantiate .tscn and access properties with `get()`/`set()`/`call()`.

3. **`_ready()` won't fire** until you `await process_frame` after `add_child()`. Always await one frame after instantiation.

4. **Clean up between tests**: `player.queue_free()` then `await process_frame`.

5. **Run command**: `cd /path/to/project && ~/.local/bin/godot --headless -s tests/test_player.gd`

## Physics tuning

For physics-heavy games (grappling, PinJoint2D, momentum):
- `physics_ticks_per_second = 120` prevents joint instability
- Velocity damping above threshold may be needed for web/grapple physics
- Per the Arachne milestones, PinJoint2D stability requires increased ticks

## Physics Processing Order ⚠️ CRITICAL

The order of operations in `_physics_process` matters. Surface state (`is_on_floor`, `is_on_ceiling`, collision normals) is only valid AFTER `move_and_slide()`.

**Correct order:**
```
1. Capture input (jump_buffer, key-held state)
2. Apply gravity/movement/friction (use previous-frame surface)
3. move_and_slide()       ← surface state updates here
4. Detect surface          ← now current
5. Execute jump/drop       ← surface is known
```

**Common pitfall:** checking `current_surface` before `_detect_surface()` runs. Since detection happens after `move_and_slide()`, any check before it uses the PREVIOUS frame's surface — causing missed surface transitions.

**Fix:** split jump into `_capture_jump_input()` (before physics) and `_execute_jump()` (after detection).

## Up-Direction-Relative Vector Math Reference

When `up_direction` can change (wall/ceiling walking), ALL physics must be relative to it. Keep this table handy:

| What | Formula | On flat ground (up=0,-1) |
|------|---------|--------------------------|
| Gravity direction | `up_direction.rotated(PI)` | `(0,1)` = DOWN ✓ |
| Surface tangent (right) | `up_direction.rotated(PI/2)` | `(1,0)` = RIGHT ✓ |
| Surface tangent (left) | `up_direction.rotated(-PI/2)` | `(-1,0)` = LEFT |
| Jump direction | `velocity += up_direction * impulse` | `vy -= 600` = UP ✓ |
| Moving "upward"? | `velocity.dot(up_direction) > 0` | vy < 0 → dot > 0 ✓ |

**Three common sign errors:**

1. **Tangent rotation**: `up_direction.rotated(PI/2)` not `-PI/2`. With `up=(0,-1)`: `PI/2` → `(1,0)` = RIGHT ✓. `-PI/2` → `(-1,0)` = LEFT ✗ (inverts A/D).
2. **Jump direction**: `velocity += up_direction * impulse` not `-=`. `+= (-600)` → goes UP ✓. `-= (-600)` = `+= (0,600)` → goes DOWN ✗.
3. **Jump cut condition**: `velocity.dot(up_direction) > 0` not `< 0`. During ascent: dot=500>0 ✓. `< 0` only fires during fall ✗.

## Surface-Walking Advanced Patterns

### The wall-snapping pitfall (8-direction raycasts)

When using 8-direction raycasts for surface detection, **filter raycasts by gravity-direction alignment**. Without filtering, side-facing rays pick up nearby walls, override the surface normal, and the player's gravity flips — they get yanked sideways into invisible walls.

Fix: only consider raycasts whose direction is within ~70° of the current gravity direction:
```gdscript
var ray_dir := ray.target_position.normalized()
if ray_dir.dot(gravity_direction) < 0.34:  # cos(70°)
    continue
```

Side walls are handled by `move_and_slide()` collision, not gravity rotation.

### Hysteresis buffer management

When aggregating normals over N frames:
- Cap buffer size: `if buf.size() > hysteresis_frames * 3: buf.pop_front()`
- Compare successive normals with `distance_to()` to detect inconsistency

### Contextual controls per surface

When `floor_max_angle = PI`, map A/D differently based on surface:

| Surface | A | D |
|---------|---|---|
| Floor/Ceiling | left | right |
| Right wall | descend | climb |
| Left wall | climb | descend |

Movement on walls uses `velocity.y` (screen-up = climb, screen-down = descend).

### Gravity on walls

Apply gravity on walls so descent is naturally faster than ascent. Ensure friction force > gravity force at rest:
```gdscript
friction_force = friction * walk_speed * delta  # e.g. 12 × 400 × 0.008 = 38.4
gravity_force = gravity * delta                  # e.g. 1400 × 0.008 = 11.2
# 38.4 > 11.2 → no sliding at rest ✓
```

## Input Map Configuration

**Ponytail rule:** Godot editor writes verbose input map — keep only the keys you actually read in code. Delete unused actions. Standard platformers only need `move_left`, `move_right`, `jump`.

**Keycodes for hand-authored project.godot:**
- A=65, D=68, W=87, S=83
- Space=32
- Left=4194319, Right=4194321, Up=4194320, Down=4194322

See `templates/project.godot` for a minimal working example.

## Prototype Controller Verification Checklist

After any physics change, test these scenarios:
- [ ] A/D moves correct direction on flat ground
- [ ] A/D moves correct direction after jumping onto a platform
- [ ] Jump goes up, gravity brings player back down
- [ ] Releasing jump early cuts height (variable jump)
- [ ] Coyote time: jump just after walking off a ledge
- [ ] Jump buffer: press jump just before landing
- [ ] No ice-sliding when releasing all keys on any surface
- [ ] Walking into a wall stops the player (doesn't clip through)
- [ ] `godot --headless --quit` loads without errors
- [ ] Tests pass: `godot --headless -s tests/test_player.gd`

## References and Templates

### References
- `references/scene-examples.md` — complete CharacterBody2D player scene template
- `references/testing.md` — GDScript headless testing patterns and pitfalls
- `references/wall-snapping-bug.md` — full diagnosis of the surface-detection wall-snapping pitfall
- `references/sign-error-examples.md` — worked examples of the three sign errors with manual verification on all surface orientations
- `references/pitfalls-transcript.md` — 6 error transcripts with full reproduction and fix

### Templates
- `templates/project.godot` — minimal working project.godot with WASD+Space input map
- `templates/test_runner.gd` — SceneTree-based headless test runner skeleton
- `templates/player.gd` — CharacterBody2D player controller with surface walking, coyote time, jump buffer
- `templates/headless_test_runner.gd` — alternative headless test runner

For gameplay prototyping before the art pipeline:
- Use `ColorRect` nodes in Godot (no external sprite files needed)
- Character: distinct colored rects for body, core, sensor/eye
- Arena: dark background (#111118), muted blue-grey platforms (#2a2a40 range)
- Debug overlay: velocity (red), surface normal (green), gravity (blue)
