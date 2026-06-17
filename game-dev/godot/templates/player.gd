extends CharacterBody2D
class_name Player

# ── Movement parameters ─────────────────────────
@export var walk_speed: float = 400.0
@export var jump_impulse: float = 600.0
@export var jump_cut_multiplier: float = 0.5
@export var acceleration_time: float = 0.08
@export var direction_change_multiplier: float = 1.5
@export var gravity: float = 1400.0
@export var friction: float = 12.0
@export var coyote_time: float = 0.08
@export var jump_buffer_time: float = 0.1

# ── Surface classification ──────────────────────
enum Surface { FLOOR, CEILING, WALL_LEFT, WALL_RIGHT, NONE }
var current_surface: int = Surface.NONE

# ── State ───────────────────────────────────────
var coyote_timer: float = 0.0
var jump_buffer_timer: float = 0.0
var last_input: float = 0.0
var jump_held: bool = false

@onready var debug_label: Label = $DebugLabel

# ── Startup ─────────────────────────────────────
func _ready() -> void:
	up_direction = Vector2.UP
	floor_max_angle = PI

# ── Per-frame ───────────────────────────────────
func _physics_process(delta: float) -> void:
	_handle_timers(delta)
	_apply_gravity(delta)
	_handle_movement(delta)
	_handle_friction(delta)
	_capture_jump_input()
	move_and_slide()
	_detect_surface()
	_execute_jump()
	_handle_drop()
	_update_debug()

# ── Surface detection (after move_and_slide) ────
func _detect_surface() -> void:
	if not is_on_floor():
		current_surface = Surface.NONE
		return
	var col := get_last_slide_collision()
	if not col:
		current_surface = Surface.FLOOR
		return
	var n := col.get_normal()
	if n.dot(Vector2.UP) > 0.7:
		current_surface = Surface.FLOOR
	elif n.dot(Vector2.DOWN) > 0.7:
		current_surface = Surface.CEILING
	elif n.dot(Vector2.LEFT) > 0.7:
		current_surface = Surface.WALL_RIGHT
	elif n.dot(Vector2.RIGHT) > 0.7:
		current_surface = Surface.WALL_LEFT
	else:
		current_surface = Surface.FLOOR

# ── Gravity (airborne + walls) ──────────────────
func _apply_gravity(delta: float) -> void:
	if not is_on_floor():
		velocity.y += gravity * delta
	if is_on_floor() and current_surface in [Surface.WALL_LEFT, Surface.WALL_RIGHT]:
		velocity.y += gravity * delta

# ── Movement (contextual by surface) ────────────
func _handle_movement(delta: float) -> void:
	var raw := Input.get_axis("move_left", "move_right")
	var accel := walk_speed / acceleration_time
	
	if sign(raw) != sign(last_input) and raw != 0.0:
		accel *= direction_change_multiplier
	if raw != 0.0:
		last_input = raw
	
	match current_surface:
		Surface.FLOOR, Surface.CEILING, Surface.NONE:
			var target := raw * walk_speed
			velocity.x = move_toward(velocity.x, target, accel * delta)
		Surface.WALL_RIGHT:
			var target := raw * walk_speed
			velocity.y = move_toward(velocity.y, -target, accel * delta)
		Surface.WALL_LEFT:
			var target := -raw * walk_speed
			velocity.y = move_toward(velocity.y, -target, accel * delta)

# ── Friction ────────────────────────────────────
func _handle_friction(delta: float) -> void:
	if not is_on_floor():
		return
	if Input.get_axis("move_left", "move_right") != 0.0:
		return
	match current_surface:
		Surface.FLOOR, Surface.CEILING, Surface.NONE:
			velocity.x = move_toward(velocity.x, 0.0, friction * walk_speed * delta)
		_:
			velocity.y = move_toward(velocity.y, 0.0, friction * walk_speed * delta)

# ── Jump capture (before move_and_slide) ────────
func _capture_jump_input() -> void:
	if Input.is_action_just_pressed("jump"):
		jump_buffer_timer = jump_buffer_time
	jump_held = Input.is_action_pressed("jump")

# ── Jump execute (after surface detection) ──────
func _execute_jump() -> void:
	if not jump_held and velocity.y < 0 and coyote_timer <= 0:
		velocity.y *= jump_cut_multiplier
	if jump_buffer_timer > 0.0 and coyote_timer > 0.0:
		velocity.y = -jump_impulse
		coyote_timer = 0.0
		jump_buffer_timer = 0.0

# ── Ceiling drop (S key) ────────────────────────
func _handle_drop() -> void:
	if current_surface == Surface.CEILING and Input.is_key_pressed(KEY_S):
		velocity.y = 50
		coyote_timer = 0.0

# ── Timers ──────────────────────────────────────
func _handle_timers(delta: float) -> void:
	if not is_on_floor():
		coyote_timer -= delta
	else:
		coyote_timer = coyote_time
	jump_buffer_timer -= delta

# ── Debug ───────────────────────────────────────
func _update_debug() -> void:
	queue_redraw()
	if debug_label:
		var surf_names: Array[String] = ["FLOOR","CEILING","WALL_L","WALL_R","NONE"]
		var txt := "VEL: %.1f, %.1f\nINPUT: %.2f\nSURFACE: %s\nCOYOTE: %.3f  BUF: %.3f" % [
			velocity.x, velocity.y,
			Input.get_axis("move_left", "move_right"),
			surf_names[current_surface],
			coyote_timer, jump_buffer_timer
		]
		debug_label.text = txt

func _draw() -> void:
	if Engine.is_editor_hint():
		return
	draw_line(Vector2.ZERO, velocity * 0.1, Color.RED, 2.0)
	if coyote_timer > 0:
		draw_circle(Vector2(0, -24), 3, Color.YELLOW)
	if jump_buffer_timer > 0:
		draw_circle(Vector2(0, -30), 3, Color.CYAN)
