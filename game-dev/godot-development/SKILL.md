---
name: godot-development
description: >
  Godot 4.x game development patterns — project setup, scene authoring,
  headless testing, surface-walking mechanics, and common pitfalls.
  Load when building or debugging Godot projects, writing GDScript,
  creating scenes programmatically, or running Godot tests.
license: MIT
---

# Godot Development

## Trigger conditions
- User asks to create/modify a Godot 4.x project
- User asks to write GDScript, .tscn scene files, or project.godot
- User needs to run Godot tests headless
- User is building surface-walking or physics-based movement

## Manual project creation

Godot projects are plain text files — no editor required. Create them directly:

### project.godot
Minimal structure:
```ini
; Engine configuration file.
config_version=5

[application]
config/name="Game Name"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.6")

[display]
window/size/viewport_width=960
window/size/viewport_height=640

[input]
action_name={
"deadzone": 0.2,
"events": [Object(InputEventKey, ...)]
}

[physics]
common/physics_ticks_per_second=120
```

### InputEventKey format
Each key event is a one-line Object literal. Copy the exact format from a working project.godot (Godot is strict about commas between array elements). Keycode 32 = Space, physical_keycode 87 = W, 65 = A, 68 = D, 83 = S. Arrow keys: 4194319=Left, 4194320=Up, 4194321=Right, 4194322=Down.

### Scene files (.tscn)
Key rules for hand-authoring:
- `load_steps=N` must count all external resources + sub-resources
- Sub-resources use `[sub_resource type="RectangleShape2D" id="unique_id"]` — IDs must be unique within the file
- Scene instances reference by path: `[ext_resource type="PackedScene" path="res://scenes/player.tscn" id="1"]`
- Avoid UIDs in hand-written scenes — they require Godot to have generated them first. Use paths instead: `instance=ExtResource("1")` with `path="res://..."` (no `uid=` in the ext_resource line)
- Each `StaticBody2D` platform needs its own CollisionShape2D shape; don't reuse sub_resource IDs across different body types unless they're genuinely identical

### Scene load verification
```bash
godot --headless --quit          # exits 0 if project loads clean
godot --headless --check-only --quit  # validates without running
```

## Headless testing

Godot tests run with `-s` flag. The test script MUST `extends SceneTree`:

```gdscript
extends SceneTree

func _init() -> void:
    await process_frame  # give engine a frame to init
    # ... run tests ...
    quit(0)  # or quit(1) on failure
```

Pitfalls:
- `class_name` declarations are NOT available when running with `-s` — use `load()` to access scripts and `get()`/`set()` to access properties
- `add_child()` goes to `root.add_child()`, not `self`
- `Node.queue_free()` + `await process_frame` between tests prevents stale-node interference

## Surface-walking mechanics

### The wall-snapping pitfall
When using 8-direction raycasts for surface detection, **filter raycasts by gravity-direction alignment**. Without filtering, side-facing rays pick up nearby walls, override the surface normal, and the player's gravity flips — they get yanked sideways into invisible walls.

Fix: only consider raycasts whose direction is within ~70° of the current gravity direction:
```gdscript
var ray_dir := ray.target_position.normalized()
if ray_dir.dot(gravity_direction) < 0.34:  # cos(70°)
    continue
```

This ensures only "downward" rays (relative to current gravity) detect the walking surface. Side walls are ignored for surface detection — they're handled by `move_and_slide()` collision, not gravity rotation.

### Hysteresis buffer management
When aggregating normals over N frames for consistency:
- Cap the buffer size (`if buf.size() > hysteresis_frames * 3: buf.pop_front()`) to prevent unbounded growth
- Compare successive normals with `distance_to()` to detect inconsistency

### Tangent movement

Movement input (scalar left/right) maps to the surface tangent. **The tangent must rotate the normal counter-clockwise** so that `tango(UP) = RIGHT`:

```gdscript
# CORRECT — counter-clockwise rotation. UP → RIGHT.
var tangent := Vector2(-current_normal.y, current_normal.x)
```

**Wrong formula** (clockwise rotation, inverts A/D controls):
```gdscript
# WRONG — Vector2(UP.y, -UP.x) = Vector2(-1, 0) = LEFT
var tangent := Vector2(current_normal.y, -current_normal.x)
```

When decomposing velocity, only accelerate along the tangent — do NOT use `move_toward` on raw `velocity.x`/`velocity.y` components, because that fights gravity on the perpendicular axis:

```gdscript
# Correct: decompose, accelerate only along tangent
var current_tangent_speed := velocity.dot(tangent)
var target_tangent_speed := input_dir * walk_speed
var new_speed := move_toward(current_tangent_speed, target_tangent_speed, accel * delta)
velocity += tangent * (new_speed - current_tangent_speed)
```

### The `move_toward` gravity-fighting pitfall

**Never** do this:
```gdscript
velocity.x = move_toward(velocity.x, target.x, accel * delta)
velocity.y = move_toward(velocity.y, target.y, accel * delta)
```

When airborne with no input, `target = (0, 0)`, so `move_toward` pulls `velocity.y` toward zero **every frame**. If the movement acceleration exceeds gravity acceleration, the player levitates — gravity can't overcome the constant reset toward zero. The player "goes up and never comes down."

Fix: decompose velocity into tangent (parallel) and normal (perpendicular) components. Only accelerate the tangent component; leave the normal component to gravity and collisions alone.

## Godot binary installation (Linux)
```bash
# Download latest stable
curl -sLO "https://github.com/godotengine/godot-builds/releases/download/VERSION-stable/Godot_vVERSION-stable_linux.x86_64.zip"
# Extract (no unzip? use python)
python3 -c "import zipfile; zipfile.ZipFile('zipname').extractall('/tmp/out')"
# Install
mv /tmp/out/Godot_v*_linux.x86_64 ~/.local/bin/godot
chmod +x ~/.local/bin/godot
```

## Supporting files
- `references/wall-snapping-bug.md` — full diagnosis of the surface-detection wall-snapping pitfall
- `templates/project.godot` — minimal working project.godot with WASD+Space+W input map
- `templates/test_runner.gd` — SceneTree-based headless test runner skeleton
