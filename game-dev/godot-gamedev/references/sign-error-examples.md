# Sign Error Examples — Godot Vector Math

All examples assume `up_direction = Vector2.UP = (0, -1)` (flat ground).
Verify each on walls and ceilings before shipping.

## Error 1: Tangent rotation direction

```gdscript
# WRONG — A/D inverted
var tangent := up_direction.rotated(-PI / 2)
# (0,-1) rotated -90° → (-1,0) = LEFT
# D key (positive input) → moves LEFT

# CORRECT
var tangent := up_direction.rotated(PI / 2)
# (0,-1) rotated +90° → (1,0) = RIGHT
# D key (positive input) → moves RIGHT
```

## Error 2: Jump impulse sign

```gdscript
# WRONG — pushes into floor
velocity -= up_direction * jump_impulse
# (0,0) -= (0,-1) * 600 = (0,0) -= (0,-600) = (0,600) → DOWN

# CORRECT — pushes away from surface
velocity += up_direction * jump_impulse
# (0,0) += (0,-1) * 600 = (0,-600) → UP
```

## Error 3: Jump cut condition

```gdscript
# WRONG — never fires during ascent
if Input.is_action_just_released("jump") and velocity.dot(up_direction) < 0:
    velocity -= up_direction * velocity.dot(up_direction) * (1.0 - cut)

# During ascent: velocity=(0,-500), up=(0,-1), dot=(-500)*(-1)=500
# 500 < 0 is FALSE → cut never fires
# During fall: velocity=(0,200), up=(0,-1), dot=200*(-1)=-200
# -200 < 0 is TRUE → cut fires during FALL (wrong!)
```

```gdscript
# CORRECT — fires during ascent
if Input.is_action_just_released("jump") and velocity.dot(up_direction) > 0:
    velocity -= up_direction * velocity.dot(up_direction) * (1.0 - cut)

# During ascent: velocity=(0,-500), up=(0,-1), dot=500
# 500 > 0 is TRUE → cut fires ✓
# Cuts upward velocity by (1-cut_multiplier) fraction
# (0,-500) -= (0,-1)*500*0.5 = (0,-500) -= (0,-250) = (0,-250) ✓
```

## Manual verification table

Verify on all surface orientations before shipping:

| Surface | `up_direction` | Gravity dir | Tangent (PI/2) | Jump dir | Cut dot>0? |
|---------|---------------|-------------|-----------------|----------|-----------|
| Floor   | (0,-1)        | (0,1) ↓     | (1,0) →         | (0,-1) ↑ | vy<0→yes |
| Right wall | (-1,0)     | (1,0) →     | (0,-1) ↑        | (-1,0) ← | vx<0→yes |
| Left wall  | (1,0)      | (-1,0) ←    | (0,1) ↓         | (1,0) →  | vx>0→yes |
| Ceiling    | (0,1)      | (0,-1) ↑    | (-1,0) ←        | (0,1) ↓  | vy>0→yes |
