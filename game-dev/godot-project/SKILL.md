---
name: godot-project
description: Godot 4.x project setup, headless CI validation, GDScript testing patterns, common .tscn pitfalls, and useful engine tricks. Use when creating or validating a Godot project, writing GDScript tests, debugging scene load errors, or setting up Godot on Linux.
triggers:
  - Creating a new Godot project
  - Running Godot headless for CI or validation
  - Writing GDScript unit tests
  - Debugging .tscn parse errors (UIDs, sub-resources)
  - Setting up Godot on Linux
  - Godot movement/physics patterns
---

# Godot Project Workflow

## Installation (Linux)

Godot 4.x is a single binary. Download from GitHub releases:

```bash
curl -sLO "https://github.com/godotengine/godot-builds/releases/download/4.6.3-stable/Godot_v4.6.3-stable_linux.x86_64.zip"
# If unzip is missing, use python3:
python3 -c "
import zipfile
with zipfile.ZipFile('Godot_v4.6.3-stable_linux.x86_64.zip') as z:
    z.extractall('/tmp/godot')
"
mkdir -p ~/.local/bin
mv /tmp/godot/Godot_v*_linux.x86_64 ~/.local/bin/godot
chmod +x ~/.local/bin/godot
```

Snap only has Godot 3. Flatpak may work but direct binary is simpler.

## Project Structure

Minimal Godot 4 project:
```
project/
├── project.godot          # Engine config, input map, main scene
├── scenes/
│   ├── player.tscn        # PackedScene for CharacterBody2D
│   └── test_arena.tscn    # Main scene with arena geometry
├── scripts/
│   └── player.gd          # GDScript with class_name
├── tests/
│   └── test_player.gd     # Headless test script
└── assets/{art,audio,music}/
```

## project.godot

Minimum:
```ini
config_version=5

[application]
config/name="Game Name"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.6")

[input]
move_left={"events": [key A, key Left]}
move_right={"events": [key D, key Right]}
jump={"events": [key Space]}
```

### Input map format

Each action is a JSON object. PONITAIL: Godot editor writes verbose input map — keep only the keys you actually read in code. Delete unused actions (dead config = dead weight).

The `move_up`/`move_down` actions are NOT needed unless the game reads `Input.get_axis("move_up", "move_down")`. Standard platformers only need `move_left`, `move_right`, `jump`.

## Scene Files (.tscn)

### ⚠️ PITFALL: UID references

When a scene references another scene (e.g. arena instantiates player), the `ext_resource` line can use either a `uid://` or a `path`. UIDs are flaky when writing .tscn by hand — prefer `path`:

```
; WORKS reliably:
[ext_resource type="PackedScene" path="res://scenes/player.tscn" id="1"]

; FRAGILE (may fail with "invalid UID"):
[ext_resource type="PackedScene" uid="uid://cplayermain" path="res://scenes/player.tscn" id="1"]
```

If you see `ext_resource, invalid UID: uid://...` in headless output, replace UID references with path-only.

### ⚠️ PITFALL: Sub-resource IDs

Sub-resources (`[sub_resource]`) are file-scoped. Define each shape with a unique ID and reference it by that ID:

```
[sub_resource type="RectangleShape2D" id="floor_col"]
size = Vector2(960, 16)

[node name="CollisionShape2D" ...]
shape = SubResource("floor_col")
```

Never reuse a sub-resource ID from another .tscn — each file has its own namespace.

### ⚠️ PITFALL: `load_steps` count

The `load_steps` header must match the number of `[ext_resource]` + `[sub_resource]` entries. If scene loading fails with a parse error, check this count.

## Headless Validation & Testing

### Validate a project loads:
```bash
godot --headless --quit
```
Exit code 0 = clean load. Errors print to stderr.

### Run a test script:
```bash
godot --headless -s tests/test_foo.gd
```

### ⚠️ PITFALL: Test scripts MUST extend SceneTree or MainLoop

Scripts run with `-s` must extend `SceneTree` or `MainLoop`, NOT `Node`. Use `extends SceneTree` and put test logic in `_init()`:

```gdscript
extends SceneTree

func _init() -> void:
    await process_frame  # Give engine one tick
    # ... run tests ...
    quit(0)  # or quit(1) on failure
```

### Testing player nodes:

`class_name` declarations are NOT resolved when running with `-s`. Use `load()` and `get()`/`call()`:

```gdscript
func _make_player() -> Node:
    var scene: PackedScene = load("res://scenes/player.tscn")
    var player: Node = scene.instantiate()
    root.add_child(player)
    return player

func test_speed() -> bool:
    var p := _make_player()
    assert(p.get("walk_speed") == 400.0, "speed mismatch")
    p.queue_free()
    return true
```

Use `player.get("export_var_name")` for exported vars and `player.call("_private_method", args...)` for private methods.

## Useful Patterns

### Wall/ceiling sticking (one-line)

Godot's `move_and_slide()` uses `floor_max_angle` (radians) to determine which surfaces count as "floor." Default is ~0.78 rad (45° slope limit). Set to `PI` to treat EVERY surface as floor:

```gdscript
func _ready() -> void:
    floor_max_angle = PI  # ponytail: walk on walls and ceilings
```

This gives full surface traversal with zero extra code. Replace with selective raycast-based surface detection if you need per-surface filtering.

### Movement along surfaces

When using `floor_max_angle = PI`, movement should follow the current floor tangent. Decompose velocity along the surface tangent to avoid fighting gravity:

```gdscript
var tangent := Vector2(-up_direction.y, up_direction.x)  # RIGHT on flat ground
var current_tangent_speed := velocity.dot(tangent)
var new_speed := move_toward(current_tangent_speed, target_speed, accel * delta)
velocity += tangent * (new_speed - current_tangent_speed)
```

This only accelerates along the surface — gravity (perpendicular) is untouched. Avoid `move_toward` on raw `velocity.x`/`.y` when surface normals can rotate.

### Standard platformer gravity

```gdscript
func _apply_gravity(delta: float) -> void:
    if not is_on_floor():
        velocity.y += gravity * delta
```

Guard with `not is_on_floor()` so gravity is zero when standing. Otherwise gravity accumulates and `move_and_slide()` has to cancel it every frame.

### Variable jump height

```gdscript
# On jump release, cut upward velocity
if Input.is_action_just_released("jump") and velocity.y < 0:
    velocity.y *= jump_cut_multiplier  # e.g. 0.5
```

### Coyote time + jump buffer

```gdscript
# Timers
if not is_on_floor():
    coyote_timer -= delta
else:
    coyote_timer = coyote_time
jump_buffer_timer -= delta

# On jump press
if Input.is_action_just_pressed("jump"):
    jump_buffer_timer = jump_buffer_time

# Execute
if jump_buffer_timer > 0 and coyote_timer > 0:
    velocity.y = -jump_impulse
    coyote_timer = 0
    jump_buffer_timer = 0
```

Place timer logic in ONE function (e.g. `_handle_timers`), not duplicated. Jump execution reads timers, doesn't manage them.

## Tool Support Files

- `references/pitfalls-transcript.md` — 6 error transcripts with full reproduction and fix (UID resolution, sub-resource namespace, `-s` script class, class_name resolution, gravity cancellation, tangent rotation inversion)
