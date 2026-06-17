# Godot 4 Headless Test Runner

Known-good test pattern from Project Arachne (10/10 passing).

## Test file template

```gdscript
extends SceneTree

const TOLERANCE := 0.1

func _init() -> void:
	await process_frame  # let engine initialize

	var tests := [
		"test_param_check",
		"test_physics_calc",
	]
	
	var passed := 0
	var failed := 0
	
	for test_name in tests:
		var result: bool = call(test_name)
		await process_frame  # clean up between tests
		if result:
			print("  PASS: %s" % test_name)
			passed += 1
		else:
			printerr("  FAIL: %s" % test_name)
			failed += 1
	
	print("\n%d/%d tests passed" % [passed, passed + failed])
	quit(0 if failed == 0 else 1)

func _make_player() -> Node:
	var scene: PackedScene = load("res://scenes/player.tscn")
	var player: Node = scene.instantiate()
	root.add_child(player)
	return player

func test_param_check() -> bool:
	var player := _make_player()
	assert(player.get("walk_speed") == 400.0, "speed mismatch")
	player.queue_free()
	return true
```

## Run command
```bash
cd /path/to/project && godot --headless -s tests/test_player.gd
```

## Why these patterns

- `extends SceneTree`: Required for `-s` mode. Node won't work.
- `await process_frame` after `_init()`: Godot needs one tick to fully load project resources before tests can load scenes.
- `await process_frame` between tests: Lets `queue_free()` actually complete before next test instantiates.
- `load()` + `instantiate()` instead of `ClassName.new()`: `class_name` doesn't resolve in `-s` mode. Always use scene paths.
- `get()`/`set()`/`call()`: Access exported vars and methods via string keys since typed references to the script class won't work in `-s` mode.
- `assert()` without message arguments: Godot's assert only takes one argument (the condition). Use string formatting in the condition for messages.

## Pitfalls encountered and resolved

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `extends Node` | "doesn't inherit from SceneTree or MainLoop" | Use `extends SceneTree` |
| `class_name Player` usage | "Identifier 'Player' not declared" | Use `load()` + `instantiate()` |
| No `await process_frame` after `add_child` | `_ready()` never fires, state uninitialized | Always await one frame after adding to tree |
| No `await process_frame` between tests | Stale nodes from previous test not cleaned | Await after `queue_free()` |
| `assert(cond, "msg")` | Parse error: too many arguments | Godot assert takes one arg. Embed message in condition string. |
