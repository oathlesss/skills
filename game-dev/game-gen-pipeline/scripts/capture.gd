extends SceneTree

# Capture a screenshot of the running game. Run via:
#   xvfb-run -a godot --path <project> --rendering-method gl_compatibility -s capture.gd
# with env CAPTURE_OUT=<abs/path.png> [CAPTURE_FRAMES=<n>].

func _init() -> void:
	var main_scene: PackedScene = load("res://scenes/main.tscn")
	var main: Node = main_scene.instantiate()
	get_root().add_child(main)

	var frames := 90
	var frames_str := OS.get_environment("CAPTURE_FRAMES")
	if frames_str != "" and frames_str.is_valid_int():
		frames = frames_str.to_int()
	for i in frames:
		await process_frame

	var img := get_root().get_texture().get_image()
	if img == null:
		printerr("CAPTURE_NULL: no rendering server. Are you running under xvfb-run?")
		quit(1)
	var out := OS.get_environment("CAPTURE_OUT")
	if out == "":
		out = "res://screenshot.png"
	img.save_png(out)
	print("CAPTURE_OK size=", img.get_size(), " -> ", out)
	quit(0)
