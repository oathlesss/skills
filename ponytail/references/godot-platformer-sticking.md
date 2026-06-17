# Godot 4 Platformer: Wall/Ceiling Sticking (Screen-Space Pattern)

## The problem

You want a CharacterBody2D to stick to walls and ceilings (like SpiderHeck),
not just floors. You have basic movement working on flat ground.

## What doesn't work: `up_direction`-relative vector math

The "obvious" approach — gravity, movement, and jump all expressed as vectors
relative to `up_direction` — introduces a cascade of sign errors. Every
operation requires mentally rotating the coordinate system:

```
# Tempting but bug-prone:
velocity += up_direction.rotated(PI) * gravity * delta    # gravity along surface
var tangent := up_direction.rotated(PI / 2)                # which rotation?
velocity += up_direction * jump_impulse                     # += or -=?
velocity.dot(up_direction) > 0                              # > 0 or < 0?
```

Each line is a sign-error waiting to happen. In practice, 3+ bugs per attempt
(tangent rotated wrong way, jump impulse wrong sign, jump cut condition
inverted). These bugs cascade: fixing one reintroduces another.

## What works: Screen-space physics

Keep gravity/movement/jump in simple screen coordinates. Let
`move_and_slide()` handle the sticking via `floor_max_angle = PI`:

```gdscript
floor_max_angle = PI  # any surface = floor

func _apply_gravity(delta):
    if not is_on_floor():
        velocity.y += gravity * delta           # always screen-down

func _handle_movement(delta):
    velocity.x = move_toward(velocity.x, target, accel * delta)  # always screen-X

func _handle_jump():
    velocity.y = -jump_impulse                  # always screen-up
```

`move_and_slide()` with `floor_max_angle = PI` resolves collisions against
any surface. The player sticks on contact. No coordinate rotation needed.

## Pitfall: Friction must cover the right axis

On walls, residual velocity lives on the Y axis (sliding up/down). Friction
that only damps `velocity.x` won't stop wall-sliding:

```gdscript
# WRONG — only stops horizontal slide:
velocity.x = move_toward(velocity.x, 0, friction)

# RIGHT — stops slide on any surface:
velocity = velocity.move_toward(Vector2.ZERO, friction)
```

## Contextual controls: surface detection

Once sticking works, players expect A/D to move along the surface they're on.
Detect surface type via `get_last_slide_collision()` normal:

```gdscript
func _detect_surface():
    if not is_on_floor(): return
    var n := get_last_slide_collision().get_normal()
    if n.dot(Vector2.UP) > 0.7:    surface = FLOOR
    if n.dot(Vector2.DOWN) > 0.7:  surface = CEILING
    if n.dot(Vector2.LEFT) > 0.7:  surface = WALL_RIGHT   # wall on player's right
    if n.dot(Vector2.RIGHT) > 0.7: surface = WALL_LEFT    # wall on player's left
```

Then map controls contextually:

| Surface | A | D | Jump |
|---------|---|---|------|
| Floor | left | right | up |
| Ceiling | left | right | up (bonk) |
| Wall right (x\|) | down | climb up | detach left |
| Wall left (\|x) | climb up | down | detach right |

For ceiling: add S key to detach (small downward nudge).

## Friction must also be contextual

Damp X on horizontal surfaces, Y on vertical ones:

```gdscript
match surface:
    FLOOR, CEILING: velocity.x = move_toward(velocity.x, 0, friction)
    _:              velocity.y = move_toward(velocity.y, 0, friction)
```

## When to upgrade to full surface traversal

This pattern works for prototypes. The limits:
- Can't walk AROUND corners smoothly (need raycast-based surface detection)
- Jump direction is always screen-up, not perpendicular to surface
- Gravity is always screen-down, not along surface tangent

Upgrade to full `up_direction`-relative vector math only when:
1. You have a solid test suite catching sign errors
2. You need the player to walk continuously around box corners
3. You need jump to always fire perpendicular to current surface

Until then, screen-space is simpler and has zero sign-error surface area.
