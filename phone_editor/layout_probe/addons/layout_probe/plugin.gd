@tool
extends EditorPlugin

var failures: Array[String] = []
var observations: Array[Dictionary] = []

func _enter_tree() -> void:
	call_deferred("_run_probe")

func _settle(frames: int = 15) -> void:
	for _frame in range(frames):
		await get_tree().process_frame

func _expect(condition: bool, message: String) -> void:
	if not condition:
		failures.append(message)
		push_error(message)

func _inside_window(control: Control, label: String) -> void:
	var bounds := Rect2(Vector2.ZERO, Vector2(get_tree().root.size))
	var rect := control.get_global_rect()
	_expect(bounds.grow(2).encloses(rect), "%s outside window: %s / %s" % [label, rect, bounds])
	observations.append({"control": label, "rect": str(rect), "window": str(bounds)})

func _run_probe() -> void:
	await _settle(45)
	var settings := EditorInterface.get_editor_settings()
	if OS.get_environment("PHONE_LAYOUT_BOOTSTRAP") == "1":
		settings.set_setting("interface/touchscreen/phone_single_panel_mode", true)
		settings.set_setting("interface/editor/appearance/display_scale", 7)
		settings.set_setting("interface/editor/appearance/custom_display_scale", float(OS.get_environment("PHONE_LAYOUT_SCALE")))
		settings.set_setting("interface/editor/localization/editor_language", "ru")
		settings.set_setting("interface/editor/behavior/save_on_focus_loss", false)
		if ResourceSaver.save(settings) != OK:
			push_error("Could not save isolated test settings")
			get_tree().quit(1)
			return
		get_tree().quit(0)
		return

	var base: Control = EditorInterface.get_base_control()
	var panels := base.find_child("PhonePanels", true, false) as Control
	var navigation := base.find_child("PhoneNavigation", true, false) as Control
	var workspace := base.find_child("PhoneWorkspace", true, false) as Control
	if panels == null or navigation == null or workspace == null:
		push_error("Phone layout was not constructed")
		get_tree().quit(1)
		return

	var output := OS.get_environment("PHONE_LAYOUT_OUTPUT")
	DirAccess.make_dir_recursive_absolute(output)
	for window_size in [Vector2i(1920, 864), Vector2i(1536, 691)]:
		get_tree().root.size = window_size
		await _settle()
		_expect(get_tree().root.size == window_size, "Window was enlarged beyond requested drawable size")
		for button_name in ["PhoneWorkspaceButton", "PhoneSceneButton", "PhoneFilesButton", "PhoneInspectorButton"]:
			var button := base.find_child(button_name, true, false) as Button
			if button == null:
				_expect(false, "Missing navigation button " + button_name)
				continue
			button.emit_signal("pressed")
			await _settle()
			var show_workspace: bool = button_name == "PhoneWorkspaceButton"
			_expect(workspace.is_visible_in_tree() == show_workspace, "Wrong workspace visibility after " + button_name)
			_expect(panels.is_visible_in_tree() != show_workspace, "Workspace and dock panels overlap after " + button_name)
			_inside_window(navigation, "navigation")
			_inside_window(button, button_name)
			var active: Control = workspace if show_workspace else panels
			_inside_window(active, button_name + " area")
			_expect(active.size.y >= window_size.y * 0.5, "Less than half the height remains for " + button_name)
			if not show_workspace:
				var tabs := panels.get_child(0) as TabContainer
				var dock := tabs.get_current_tab_control()
				_inside_window(dock, button_name + " dock")
				var expected := {"PhoneSceneButton": "SceneTreeDock", "PhoneFilesButton": "FileSystemDock", "PhoneInspectorButton": "InspectorDock"}
				_expect(dock.is_class(expected[button_name]), "Wrong native dock selected by " + button_name)
			await RenderingServer.frame_post_draw
			var screenshot := get_viewport().get_texture().get_image()
			var screenshot_path := output.path_join("%sx%s-%s.png" % [window_size.x, window_size.y, button_name])
			_expect(screenshot.save_png(screenshot_path) == OK, "Could not save UI screenshot")

	var report := {"failures": failures, "observations": observations,
		"scope": "Linux runtime of the shared dock-layout code; Android gestures and Android-specific chrome are not tested"}
	var report_file := FileAccess.open(output.path_join("geometry.json"), FileAccess.WRITE)
	if report_file == null:
		push_error("Could not write geometry report")
		get_tree().quit(1)
		return
	report_file.store_string(JSON.stringify(report, "\t"))
	report_file.close()
	print("PHONE_LAYOUT_RESULT ", "PASS" if failures.is_empty() else "FAIL")
	get_tree().quit(0 if failures.is_empty() else 1)
