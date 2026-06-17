---
name: godot-player-controller
description: >-
  Godot 4.x CharacterBody2D player controller patterns for prototyping —
  screen-space vs up_direction-relative physics, wall/ceiling sticking,
  coyote time, jump buffering, friction, and common sign-error debugging.
license: MIT
---

# Godot 2D Player Controller (Prototype)

Patterns and pitfalls for building a CharacterBody2D player controller in
Godot 4.x, focused on the prototype phase. Production surface traversal
(raycast-based) comes later — this is for getting a playable character fast.

## Rule 1: Screen-space physics first, vector math later

For prototypes, keep gravity, jump, and movement in screen coordinates
(`velocity.y`, `velocity.x`). Do NOT use `up_direction`-relative vector
math unless you have a working raycast-based surface detection system in
place AND the math is fully verified on all surface orientations.

**Screen-space (use this for prototypes):**
- Gravity: `velocity.y += gravity * delta`
- Jump: `velocity.y = -jump_impulse`
- Movement: `velocity.x = move_toward(velocity.x, target, accel * delta)`

**`up_direction`-relative (defer to later):**
- Gravity: `velocity += up_direction.rotated(PI) * gravity * delta`
- Jump: `velocity += up_direction * jump_impulse`
- Movement: decompose along `up_direction.rotated(PI/2)`

Mixing screen-space and `up_direction`-relative math on the same frame
causes the player to fight gravity, slide infinitely, or get stuck.

## Rule 2: Wall/ceiling sticking via floor_max_angle

The one-line ponytail hack for wall/ceiling sticking:

```gdscript
func _ready() -> void:
    up_direction = Vector2.UP
    floor_max_angle = PI  # treat any surface as floor
```

This makes `move_and_slide()` treat walls and ceilings as floor surfaces.
The player sticks on contact. Works correctly ONLY with screen-space
physics (Rule 1) — when physics are `up_direction`-relative, gravity
rotates and causes ice-sliding.

With this hack:
- Walls: player sticks, gravity pulls screen-down, friction prevents slide
- Ceilings: player sticks, gravity pulls screen-down but `move_and_slide`
  keeps them on the ceiling surface
- Movement is always screen-X (no climbing walls). For wall-climbing,
  you need Rule 1's deferred vector math or a separate wall-climb mechanic.

## Rule 3: Friction prevents ice-sliding

When using `floor_max_angle = PI`, add surface friction to prevent
residual velocity from causing slow slides:

```gdscript
@export var friction: float = 12.0

func _handle_friction(delta: float) -> void:
    if not is_on_floor():
        return
    var input_dir := Input.get_axis("move_left", "move_right")
    if input_dir != 0.0:
        return
    velocity.x = move_toward(velocity.x, 0.0, friction * walk_speed * delta)
```

## Rule 4: Coyote time + jump buffer

Standard pattern, place these before `move_and_slide()`:

```gdscript
@export var coyote_time: float = 0.08
@export var jump_buffer_time: float = 0.1
var coyote_timer: float = 0.0
var jump_buffer_timer: float = 0.0

func _handle_timers(delta: float) -> void:
    if not is_on_floor():
        coyote_timer -= delta
    else:
        coyote_timer = coyote_time
    jump_buffer_timer -= delta

func _handle_jump() -> void:
    if Input.is_action_just_pressed("jump"):
        jump_buffer_timer = jump_buffer_time
    if Input.is_action_just_released("jump") and velocity.y < 0:
        velocity.y *= jump_cut_multiplier  # variable jump height
    if jump_buffer_timer > 0.0 and coyote_timer > 0.0:
        velocity.y = -jump_impulse
        coyote_timer = 0.0
        jump_buffer_timer = 0.0
```

Note: reset `coyote_timer` in ONE place. Duplicating the
`if is_on_floor(): coyote_timer = coyote_time` in both `_handle_timers`
and `_handle_jump` is a bug waiting to happen — pick one.

## Pitfalls

### Sign errors in vector math (three common ones)

When switching to `up_direction`-relative math, these three sign errors
break physics:

1. **Tangent rotation**: `up_direction.rotated(PI/2)` not `-PI/2`.
   With `up_direction = (0,-1)`: `PI/2` → `(1,0)` = RIGHT ✓.
   `-PI/2` → `(-1,0)` = LEFT ✗ (inverts A/D).

2. **Jump direction**: `velocity += up_direction * impulse` not `-=`.
   With `up_direction = (0,-1)`: `+= (-600)` → goes UP ✓.
   `-= (-600)` = `+= (0,600)` → goes DOWN ✗ (pushes into floor).

3. **Jump cut condition**: `velocity.dot(up_direction) > 0` not `< 0`.
   During ascent (vy=-500, up=(0,-1)): dot=500>0 ✓.
   `< 0` only fires during fall ✗ (never cuts jump height).

### Gravity guard must match physics model

Screen-space: `if not is_on_floor(): velocity.y += gravity * delta`
Vector: `if not is_on_floor(): velocity += up_direction.rotated(PI) * gravity * delta`

The `if not is_on_floor()` guard is correct for both — when stuck to a
surface, `is_on_floor()` is true and gravity should NOT pull the player
off the surface.

### Don't mix screen-space and up_direction-relative

A player controller where gravity is screen-space but jump is
`up_direction`-relative (or vice versa) produces frame-order-dependent
bugs that are hard to diagnose. Pick one model and stick with it
throughout the entire `_physics_process`.

## Verification checklist

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

## References

- `references/sign-error-examples.md` — Worked examples of the three sign errors
  with manual verification on all surface orientations.
