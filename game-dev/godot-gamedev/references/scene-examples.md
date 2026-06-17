# Godot 4 Scene Templates

Complete, valid .tscn examples for common scene types. Copy and adapt.

## CharacterBody2D Player Scene

```ini
[gd_scene load_steps=3 format=3]

[ext_resource type="Script" path="res://scripts/player.gd" id="1"]

[sub_resource type="RectangleShape2D" id="hitbox"]
size = Vector2(28, 32)

[node name="Player" type="CharacterBody2D"]
collision_layer = 1
collision_mask = 1
script = ExtResource("1")

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
position = Vector2(0, -2)
shape = SubResource("hitbox")

[node name="PlaceholderSprite" type="ColorRect" parent="."]
offset_left = -14
offset_top = -32
offset_right = 14
offset_bottom = 0
color = Color(1, 0.35, 0.1, 1)

[node name="DebugLabel" type="Label" parent="."]
offset_left = -80
offset_top = -80
offset_right = 80
offset_bottom = -60
text = "---"
```

Note: `load_steps=3` = 1 base + 1 ext_resource + 1 sub_resource.

## StaticBody2D Platform

```ini
[node name="Platform" type="StaticBody2D" parent="."]

[node name="CollisionShape2D" type="CollisionShape2D" parent="Platform"]
position = Vector2(400, 400)
shape = SubResource("plat_shape")

[node name="ColorRect" type="ColorRect" parent="Platform"]
offset_left = 320
offset_top = 394
offset_right = 480
offset_bottom = 406
color = Color(0.25, 0.27, 0.4, 1)
```

The `SubResource("plat_shape")` must be defined in the file's `[sub_resource]` section.

## Arena scene (composing walls, platforms, player)

```ini
[gd_scene load_steps=5 format=3]

[ext_resource type="PackedScene" path="res://scenes/player.tscn" id="1"]

[sub_resource type="RectangleShape2D" id="floor"]
size = Vector2(960, 16)

[sub_resource type="RectangleShape2D" id="plat"]
size = Vector2(160, 12)

[node name="TestArena" type="Node2D"]

[node name="Player" parent="." instance=ExtResource("1")]
position = Vector2(200, 500)

[node name="Floor" type="StaticBody2D" parent="."]

[node name="CollisionShape2D" type="CollisionShape2D" parent="Floor"]
position = Vector2(480, 630)
shape = SubResource("floor")

[node name="ColorRect" type="ColorRect" parent="Floor"]
offset_left = 0
offset_top = 622
offset_right = 960
offset_bottom = 640
color = Color(0.2, 0.22, 0.35, 1)
```

Key: Each sub_resource gets a unique local id. The id namespace is per-file.

## Input map keycode reference

Common physical_keycode values for project.godot input maps:

| Key        | Code      |
|-----------|-----------|
| A         | 65        |
| D         | 68        |
| W         | 87        |
| S         | 83        |
| Space     | 32        |
| Left      | 4194319   |
| Right     | 4194321   |
| Up        | 4194320   |
| Down      | 4194322   |
