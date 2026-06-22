# Surface detection wall-snapping — error transcript

## Symptom
Player reports "invisible walls" and erratic movement. Movement feels "scuffed."

## Root cause
`_detect_surface()` iterates ALL 8 raycasts (0° to 315°) and picks the one with highest
`normal.dot(-gravity_direction)`. When the player walks near a pillar:

1. A side-facing ray (e.g. 90° = right) hits the pillar
2. Pillar reports normal pointing LEFT (Vector2(-1, 0))
3. `normal.dot(-gravity_direction)` where gravity_direction = Vector2.DOWN:
   `Vector2(-1,0).dot(Vector2(0,1))` = 0.0
4. Meanwhile floor ray (270°) reports normal UP: `Vector2(0,1).dot(Vector2(0,1))` = 1.0
5. Floor wins... initially

BUT when gravity_direction has been lerped slightly (e.g. from a prior frame where
the player bumped a corner), the dot products shift and the side wall can win.
Once target_gravity_direction flips, the player's "up" becomes sideways,
and they try to walk on the wall. The wall collision pushes them back,
creating the "invisible wall" feeling.

## Fix applied
Filter raycasts by gravity-direction alignment BEFORE evaluating normals:

```gdscript
var ray_dir := ray.target_position.normalized()
if ray_dir.dot(gravity_direction) < 0.34:  # cos(70°) ≈ 0.34
    continue
```

This means only the 2-3 "downward" rays (within 70° of gravity) participate in
surface detection. Side walls are handled by move_and_slide() collision alone.

## Commit
e8033d3 — "Fix surface detection and jump input"
