extends SceneTree

# Minimal Godot headless test runner
# Run: godot --headless --path . -s tests/runner.gd

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


func test_example() -> bool:
	# Load scene by path, not class_name
	var scene: PackedScene = load("res://scenes/player.tscn")
	var node: Node = scene.instantiate()
	root.add_child(node)
	
	# Access properties via get()/set() since class_name not available
	var speed: float = node.get("walk_speed")
	assert(speed == 400.0, "speed mismatch: %s" % speed)
	
	node.queue_free()
	return true
