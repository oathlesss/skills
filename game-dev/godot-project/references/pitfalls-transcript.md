# Godot Pitfalls — Error Transcripts

## 1. UID Resolution Failure

```
WARNING: res://scenes/test_arena.tscn:3 - ext_resource, invalid UID: uid://cplayermain - using text path instead
ERROR: Failed loading scene: res://scenes/test_arena.tscn.
```

**Cause:** Player scene declared `uid="uid://cplayermain"` in its `[gd_scene]` header, and arena referenced it via UID. Godot couldn't resolve the UID at headless load time.

**Fix:** Remove UID from player.tscn header: `[gd_scene load_steps=4 format=3]` (no uid=). Reference by path-only in arena: `[ext_resource type="PackedScene" path="res://scenes/player.tscn" id="1"]`.

## 2. Sub-Resource Reference Failure

```
ERROR: Parse Error: Invalid parameter. [Resource file res://scenes/test_arena.tscn:40]
```

**Cause:** Arena scene reused sub-resource IDs from another file. `[sub_resource type="RectangleShape2D" id="RectangleShape2D_player"]` was defined in player.tscn but referenced in arena.tscn.

**Fix:** Each .tscn has its own sub-resource namespace. Define shapes with unique IDs per file: `floor_col`, `plat_col`, `pillar_col`, `wall_col`. Never cross-reference sub-resources between files.

## 3. `-s` Script Extending Wrong Class

```
Can't load the script "tests/test_player.gd" as it doesn't inherit from SceneTree or MainLoop.
```

**Cause:** Test script used `extends Node`. Scripts run with `godot --headless -s` must extend `SceneTree` or `MainLoop`.

**Fix:** Change to `extends SceneTree`. Put test logic in `_init()`, use `await process_frame` to let the engine initialize, and call `root.add_child()` to add nodes.

## 4. `class_name` Not Resolved in `-s` Scripts

```
SCRIPT ERROR: Parse Error: Identifier "Player" not declared in the current scope.
```

**Cause:** `class_name Player` in player.gd registers the class globally when the project loads, but `-s` scripts run before full project init.

**Fix:** Use `load("res://scenes/player.tscn")` + `scene.instantiate()` instead of `Player.new()`. Access export vars with `player.get("var_name")` and private methods with `player.call("_method", args...)`.

## 5. Movement Fighting Gravity

**Symptom:** Player jumps up but never comes back down. Floats in place.

**Cause:** `move_toward(velocity.y, target_vel.y, accel * delta)` pulls velocity.y toward 0 every frame. With `accel = walk_speed / acceleration_time = 400/0.08 = 5000` and gravity `1400`, the movement code counters gravity by ~3.5x. At 60fps: accel*delta = 80, gravity*delta = 22.4. Velocity.y oscillates between 0 and 22.4 — effectively stuck.

**Fix:** Decompose velocity along surface tangent. Only apply `move_toward` to the tangent component:

```gdscript
var tangent := Vector2(-up_direction.y, up_direction.x)
var current := velocity.dot(tangent)
var target := input_dir * walk_speed
var next := move_toward(current, target, accel * delta)
velocity += tangent * (next - current)
```

## 6. Inverted Movement from Wrong Tangent Rotation

**Symptom:** A moves right, D moves left (inverted).

**Cause:** `Vector2(current_normal.y, -current_normal.x)` rotates 90° **clockwise**. For a flat ground normal of Vector2.UP (0, -1), this gives Vector2(-1, 0) = LEFT.

**Fix:** `Vector2(-current_normal.y, current_normal.x)` rotates 90° **counter-clockwise**. For Vector2.UP (0, -1), this gives Vector2(1, 0) = RIGHT. A maps to left, D to right.
