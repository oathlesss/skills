extends SceneTree

# Godot headless test runner template
# Run with: godot --headless --path . -s tests/test_foo.gd
#
# Usage:
#   1. Add test functions returning bool
#   2. Add function names to the tests[] array
#   3. Use _make_thing() to instantiate nodes into root

func _init() -> void:
	await process_frame

	var tests := [
		"test_example",
	]
	
	var passed := 0
	var failed := 0
	
	for test_name in tests:
		var result: bool = call(test_name)
		await process_frame
		if result:
			print("  PASS: %s" % test_name)
			passed += 1
		else:
			printerr("  FAIL: %s" % test_name)
			failed += 1
	
	print("\n%d/%d tests passed" % [passed, passed + failed])
	quit(0 if failed == 0 else 1)


# ── Helpers ──────────────────────────────────────
func _make_player() -> Node:
	var scene: PackedScene = load("res://scenes/player.tscn")
	var node: Node = scene.instantiate()
	root.add_child(node)
	return node


# ── Tests ────────────────────────────────────────
func test_example() -> bool:
	var player := _make_player()
	assert(player.get("walk_speed") == 400.0, "speed mismatch")
	player.queue_free()
	return true
