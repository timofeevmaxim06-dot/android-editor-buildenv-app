@tool
extends EditorPlugin

var failures: Array[String] = []
var observations: Array[Dictionary] = []

func _press_navigation(button: Button, navigation: ScrollContainer) -> void:
	navigation.ensure_control_visible(button)
	await _settle(8)
	_inside_window(button, button.name)
	_expect(navigation.get_global_rect().grow(2).encloses(button.get_global_rect()), str(button.name) + " is clipped")
	var hits := [0]
	var record := func(): hits[0] += 1
	button.pressed.connect(record)
	var point := button.get_global_rect().get_center()
	for pressed in [true, false]:
		var event := InputEventMouseButton.new()
		event.button_index = MOUSE_BUTTON_LEFT
		event.pressed = pressed
		event.position = point
		event.global_position = point
		Input.parse_input_event(event)
		await _settle(3)
	_expect(hits[0] == 1, str(button.name) + " did not receive exactly one click")
	await _touch(point, true)
	await _touch(point, false)
	button.pressed.disconnect(record)
	_expect(hits[0] == 2, str(button.name) + " did not receive exactly one native tap")

func _touch(point: Vector2, pressed: bool, double_tap := false) -> void:
	var event := InputEventScreenTouch.new()
	event.index = 0
	event.position = point
	event.pressed = pressed
	event.double_tap = double_tap
	Input.parse_input_event(event)
	await _settle(3)

func _test_native_touch(base: Control) -> void:
	_mark("native_touch")
	EditorInterface.set_main_screen_editor("Script")
	EditorInterface.edit_script(load("res://phone_text_fixture.gd"), 0, 0, true)
	await _settle(30)
	var current := EditorInterface.get_script_editor().get_current_editor()
	var code := current.get_base_editor() as CodeEdit
	if code == null:
		_expect(false, "Native touch has no CodeEdit")
		return
	_expect(code.size.y >= get_tree().root.size.y * 0.5, "Native touch has less than half the window for code")
	var original := code.text
	var original_emulation := Input.emulate_mouse_from_touch
	Input.emulate_mouse_from_touch = true
	code.text = "alpha beta gamma\n".repeat(200)
	code.deselect()
	code.set_caret_line(0)
	code.set_caret_column(0)
	code.set_v_scroll(0)
	code.grab_focus()
	await _settle()
	var touch_events := [0]
	var record := func(event: InputEvent):
		if event is InputEventScreenTouch or event is InputEventScreenDrag:
			touch_events[0] += 1
	code.gui_input.connect(record)
	var local := Vector2(code.size.x * 0.4, code.size.y * 0.35)
	var point := code.global_position + local
	var expected_caret := code.get_line_column_at_pos(local)
	# A stale mouse over the minimap must not intercept a native text tap.
	Input.emulate_mouse_from_touch = false
	var stale_mouse := InputEventMouseMotion.new()
	stale_mouse.position = code.global_position + Vector2(code.size.x - 40, code.size.y * 0.5)
	stale_mouse.global_position = stale_mouse.position
	Input.parse_input_event(stale_mouse)
	await _settle(3)
	await _touch(point, true)
	await _touch(point, false)
	_expect(code.get_caret_line() == expected_caret.y and code.get_caret_column() == expected_caret.x, "Touch release did not place the caret at its position")
	Input.emulate_mouse_from_touch = true
	code.set_caret_line(0)
	code.set_caret_column(3)
	code.set_v_scroll(0)
	await _settle()
	var before := code.text
	await _touch(point, true)
	for step in range(1, 6):
		var event := InputEventScreenDrag.new()
		event.index = 0
		event.relative = Vector2(0, -20)
		event.position = point - Vector2(0, 20 * step)
		Input.parse_input_event(event)
		await _settle(3)
	await _touch(point - Vector2(0, 100), false)
	_expect(code.get_v_scroll() > 0, "Native single-finger drag did not scroll")
	_expect(code.text == before and not code.has_selection() and code.get_caret_line() == 0 and code.get_caret_column() == 3, "Native drag changed text, caret or selection")
	# A tap stops inertia before positioning the next word selection.
	await _touch(point, true)
	await _touch(point, false)
	code.set_v_scroll(0)
	code.deselect()
	await _settle()
	var word_rect := code.get_rect_at_line_column(0, 8)
	_expect(word_rect.position.x >= 0, "Selected test word is outside the drawable code area")
	var word_point := code.global_position + Vector2(word_rect.get_center())
	_expect(code.get_word_at_pos(Vector2(word_rect.get_center())) == "beta", "Word target does not map to beta")
	# Touch selection must use its own coordinates, even with a separate mouse.
	Input.emulate_mouse_from_touch = false
	var mouse := InputEventMouseMotion.new()
	mouse.position = code.global_position + Vector2(code.get_rect_at_line_column(0, 14).get_center())
	mouse.global_position = mouse.position
	Input.parse_input_event(mouse)
	await _settle(3)
	await _touch(word_point, true)
	await _touch(word_point, false)
	await _touch(word_point, true, true)
	await _touch(word_point, false, true)
	_expect(code.get_selected_text() == "beta", "Native double tap did not select the touched word: " + code.get_selected_text())
	_expect(code.is_selection_handle_enabled(), "Selection handles are disabled")
	_expect(touch_events[0] >= 12, "Native touch events did not reach CodeEdit")
	code.gui_input.disconnect(record)
	code.text = original
	code.deselect()
	Input.emulate_mouse_from_touch = original_emulation
	observations.append({"control": "native_touch", "events": touch_events[0], "scope": "Injected ScreenTouch/ScreenDrag; caret, scroll without edits and double-tap selection"})

func _test_create_dialog(base: Control) -> void:
	_mark("create_dialog")
	var tabs := base.find_child("PhoneCreateTabs", true, false) as TabContainer
	_expect(tabs != null, "Tabbed creation dialog is missing")
	if tabs == null:
		return
	var dialog := tabs.get_parent() as Window
	_expect(dialog != null, "Creation tabs have no native dialog")
	if dialog == null:
		return
	get_tree().root.size = Vector2i(691, 1536)
	await _settle()
	dialog.popup_centered_clamped(Vector2i(600, 1000), 0.9)
	await _settle()
	_expect(tabs.get_tab_count() == 3, "Search, favorites and recent are not separate views")
	for index in range(3):
		tabs.current_tab = index
		await _settle()
		_expect(dialog.size.x <= get_tree().root.size.x and dialog.size.y <= get_tree().root.size.y, "Creation dialog exceeds portrait window")
		_expect(tabs.get_current_tab_control().size.x <= dialog.size.x, "Creation tab exceeds dialog width")
		observations.append({"control": "create_tab_" + str(index), "dialog": str(dialog.size)})
	dialog.hide()

func _enter_tree() -> void:
	_mark("plugin_loaded")
	call_deferred("_run_probe")

func _mark(stage: String) -> void:
	print("PHONE_LAYOUT_STAGE ", stage)
	var output := OS.get_environment("PHONE_LAYOUT_OUTPUT")
	DirAccess.make_dir_recursive_absolute(output)
	var progress := FileAccess.open(output.path_join("progress.txt"), FileAccess.WRITE)
	if progress != null:
		progress.store_line(stage)
		progress.close()

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

func _dump_widths(node: Node, threshold: float) -> void:
	if node is Control and node.is_visible_in_tree():
		var control := node as Control
		if control.get_combined_minimum_size().x >= threshold:
			print("PHONE_MIN_WIDTH ", control.get_path(), " class=", control.get_class(), " min=", control.get_combined_minimum_size(), " size=", control.size)
	for child in node.get_children(true):
		_dump_widths(child, threshold)

func _press_text_tool(editor: Control, name: String, native_tap := false) -> void:
	var button := editor.find_child(name, true, false) as Button
	if button == null:
		_expect(false, "Missing text action " + name)
		return
	var tools := editor.find_child("PhoneCodeTools", true, false) as ScrollContainer
	var in_more := tools.is_ancestor_of(button)
	if in_more:
		if not tools.is_visible_in_tree():
			await _tap_button(editor.find_child("PhoneMore", true, false) as Button)
		tools.ensure_control_visible(button)
	await _settle(8)
	_inside_window(button, name)
	var bounds := tools if in_more else editor.find_child("PhoneCodePrimary", true, false) as Control
	_expect(bounds.get_global_rect().grow(2).encloses(button.get_global_rect()), name + " is clipped by the toolbar")
	var hits := [0]
	var record_press := func(): hits[0] += 1
	button.pressed.connect(record_press)
	var point := button.get_global_rect().get_center()
	if native_tap:
		await _touch(point, true)
		await _touch(point, false)
	else:
		for pressed in [true, false]:
			var click := InputEventMouseButton.new()
			click.button_index = MOUSE_BUTTON_LEFT
			click.pressed = pressed
			click.position = point
			click.global_position = point
			Input.parse_input_event(click)
			await _settle(3)
	button.pressed.disconnect(record_press)
	_expect(hits[0] == 1, name + " did not receive exactly one real click/tap")
	_expect(not tools.is_visible_in_tree(), name + " left the extra commands covering code")

func _tap_button(button: Button) -> void:
	_expect(button != null and button.is_visible_in_tree(), "Missing visible button")
	if button == null or not button.is_visible_in_tree():
		return
	_inside_window(button, button.name)
	var point := button.get_global_rect().get_center()
	await _touch(point, true)
	await _touch(point, false)
	await _settle(6)

func _test_direction_lock(editor: Control, code: CodeEdit) -> void:
	_mark("direction_lock_and_wrap")
	var original := code.text
	var was_wrap := code.get_line_wrapping_mode() != TextEdit.LINE_WRAPPING_NONE
	if was_wrap:
		await _press_text_tool(editor, "PhoneWrap")
	code.text = ("# " + "long_word ".repeat(120) + "\n").repeat(80)
	code.grab_focus()
	var emulation := Input.emulate_mouse_from_touch
	Input.emulate_mouse_from_touch = true
	for reading in [false, true]:
		if reading:
			await _press_text_tool(editor, "PhoneScrollMode")
		for movement in [Vector2(3, -20), Vector2(-20, 3)]:
			# Stop previous inertia, then establish a known scroll position.
			var point := code.global_position + code.size * Vector2(0.4, 0.6)
			await _touch(point, true)
			await _touch(point, false)
			code.set_caret_line(0)
			code.set_caret_column(3)
			code.deselect()
			code.set_h_scroll(200)
			code.set_v_scroll(8)
			await _settle()
			var state := [code.text, code.get_caret_line(), code.get_caret_column(), code.get_selected_text()]
			var h := code.get_h_scroll()
			var v := code.get_v_scroll()
			await _touch(point, true)
			for step in range(1, 6):
				var drag := InputEventScreenDrag.new()
				drag.index = 0
				drag.relative = movement
				drag.position = point + movement * step
				Input.parse_input_event(drag)
				await _settle(3)
			await _touch(point + movement * 5, false)
			await _settle(10)
			if movement.y < 0:
				_expect(is_equal_approx(code.get_h_scroll(), h), "Vertical finger drag drifted horizontally, reading=" + str(reading))
				_expect(code.get_v_scroll() > v, "Vertical finger drag failed to scroll")
			else:
				_expect(code.get_h_scroll() > h, "Intentional horizontal drag was blocked")
				_expect(is_equal_approx(code.get_v_scroll(), v), "Horizontal drag drifted vertically")
			_expect(state == [code.text, code.get_caret_line(), code.get_caret_column(), code.get_selected_text()], "Directional scrolling changed editing state")
		if reading:
			await _press_text_tool(editor, "PhoneScrollMode")
	# Cancel the last native inertia before changing display settings.
	var stop := code.global_position + code.size * Vector2(0.4, 0.4)
	await _touch(stop, true)
	await _touch(stop, false)
	code.select(1, 2, 1, 6)
	var saved := _font_edit_state(code)
	await _press_text_tool(editor, "PhoneWrap")
	_expect(code.get_line_wrapping_mode() == TextEdit.LINE_WRAPPING_BOUNDARY, "Wrap command did not enable wrapping")
	_expect(code.get_h_scroll() == 0, "Wrapped code remained scrolled sideways")
	_expect(_font_edit_state(code) == saved, "Wrapping changed text, caret, selection or history")
	await _press_text_tool(editor, "PhoneWrap")
	_expect(code.get_line_wrapping_mode() == TextEdit.LINE_WRAPPING_NONE, "Wrap command did not toggle off")
	_expect(_font_edit_state(code) == saved, "Disabling wrapping changed editing state")
	if was_wrap:
		await _press_text_tool(editor, "PhoneWrap")
	code.text = original
	code.deselect()
	code.set_h_scroll(0)
	code.set_v_scroll(0)
	Input.emulate_mouse_from_touch = emulation
	observations.append({"control": "direction_lock_and_wrap", "scope": "Noisy vertical and intentional horizontal single-finger drags, both reading/edit modes; wrap without text/history changes"})

func _font_edit_state(code: CodeEdit) -> Array:
	return [code.text, code.get_caret_line(), code.get_caret_column(),
		code.get_selected_text(), code.get_version(), code.has_undo(), code.has_redo(),
		DisplayServer.clipboard_get(), code.has_focus()]

func _menu_choose(button: MenuButton, index: int) -> void:
	await _tap_button(button)
	var popup := button.get_popup()
	_expect(popup.visible, str(button.name) + " did not open")
	_expect(index >= 0 and index < popup.item_count, "Missing menu item")
	if index < 0 or index >= popup.item_count:
		popup.hide()
		return
	popup.set_focused_item(index)
	var event := InputEventKey.new()
	event.keycode = KEY_ENTER
	event.pressed = true
	popup.push_input(event)
	await _settle(6)
	_expect(not popup.visible, "Selected menu stayed open")

func _test_sections_and_context(base: Control) -> void:
	_mark("sections_and_context")
	var sections := base.find_child("PhoneSections", true, false) as MenuButton
	await _tap_button(sections)
	var menu := sections.get_popup()
	var target := (base.find_child("PhoneDockInspectorDock", true, false) as Button).text
	var index := -1
	for i in range(menu.item_count):
		if menu.get_item_text(i) == target:
			index = i
	_expect(menu.item_count >= 10, "Section chooser omitted editor sections")
	menu.hide()
	EditorInterface.get_selection().clear()
	await _settle()
	await _menu_choose(sections, index)
	var choose := base.find_child("PhoneChooseNode", true, false) as Button
	var label := base.find_child("PhoneSelectedNode", true, false) as Label
	_expect(choose.is_visible_in_tree(), "Inspector has no route back to the scene tree")
	_expect(label.text.contains("не выбран"), "Empty selection has misleading context")
	await _tap_button(choose)
	_expect((base.find_child("PhoneDockSceneTreeDock", true, false) as Button).button_pressed, "Choose node did not open Scene")
	var root := EditorInterface.get_edited_scene_root()
	EditorInterface.get_selection().add_node(root)
	await _settle()
	await _menu_choose(sections, index)
	_expect(label.text.contains(str(root.name)), "Selected node name is missing from context")
	EditorInterface.get_selection().clear()
	observations.append({"control": "sections_and_context", "scope": "Real section-menu activation, scene return and selected node label"})

func _test_2d_tools(base: Control) -> void:
	_mark("phone_2d_tools")
	EditorInterface.set_main_screen_editor("2D")
	await _settle()
	var pan := base.find_child("Phone2DPan", true, false) as Button
	var select := base.find_child("Phone2DSelect", true, false) as Button
	var frame := base.find_child("Phone2DFrame", true, false) as MenuButton
	await _tap_button(pan)
	_expect(pan.button_pressed and not select.button_pressed, "2D overview mode is not active")
	var root := EditorInterface.get_edited_scene_root()
	var marker := Node2D.new()
	marker.name = "PhoneProbeMarker"
	marker.position = Vector2(900, 600)
	root.add_child(marker)
	EditorInterface.get_selection().clear()
	EditorInterface.get_selection().add_node(marker)
	await _settle()
	var surface := base.find_child("Phone2DViewport", true, false) as Control
	var point := surface.get_global_rect().get_center()
	var viewport := EditorInterface.get_editor_viewport_2d()
	var before := viewport.global_canvas_transform
	var emulation := Input.emulate_mouse_from_touch
	Input.emulate_mouse_from_touch = true
	await _touch(point, true)
	for step in range(1, 6):
		var drag := InputEventScreenDrag.new()
		drag.index = 0
		drag.relative = Vector2(12, 9)
		drag.position = point + drag.relative * step
		Input.parse_input_event(drag)
		await _settle(3)
	await _touch(point + Vector2(60, 45), false)
	_expect(not viewport.global_canvas_transform.is_equal_approx(before), "2D overview drag did not move the view")
	_expect(marker.position == Vector2(900, 600), "2D overview drag moved the scene object")
	_expect(EditorInterface.get_selection().get_selected_nodes() == [marker], "2D overview drag changed selection")
	await _menu_choose(frame, 0)
	await _menu_choose(frame, 1)
	await _menu_choose(frame, 2)
	_expect(marker.position == Vector2(900, 600), "Framing changed scene content")
	await _tap_button(select)
	_expect(select.button_pressed and not pan.button_pressed, "Could not return to 2D selection mode")
	EditorInterface.get_selection().clear()
	marker.queue_free()
	Input.emulate_mouse_from_touch = emulation
	observations.append({"control": "phone_2d_tools", "scope": "Native tap and drag, mode feedback, frame commands without object movement"})

func _test_font_tools(editor: Control, code: CodeEdit, output: String) -> void:
	_mark("font_tools")
	await _press_text_tool(editor, "PhoneFontReset")
	var original_size := code.get_theme_font_size("font_size")
	var code_rect := code.get_global_rect()
	var saved_state := _font_edit_state(code)
	var old_emulation := Input.emulate_mouse_from_touch
	Input.emulate_mouse_from_touch = true
	for native_tap in [false, true]:
		await _press_text_tool(editor, "PhoneFontLarger", native_tap)
		_expect(code.get_theme_font_size("font_size") > original_size, "Font + did not enlarge code")
		_expect(_font_edit_state(code) == saved_state, "Font + changed editing state")
		_expect(code.get_global_rect().is_equal_approx(code_rect), "Font + moved or resized the code area")
		await _press_text_tool(editor, "PhoneFontSmaller", native_tap)
		_expect(code.get_theme_font_size("font_size") == original_size, "Font - did not restore one step")
		_expect(_font_edit_state(code) == saved_state, "Font - changed editing state")
	await _press_text_tool(editor, "PhoneScrollMode")
	var surface := code.get_node("PhoneCodeScrollSurface") as Control
	for index in range(4):
		await _press_text_tool(editor, "PhoneFontLarger", true)
	_expect(surface.is_visible_in_tree(), "Font controls unexpectedly left reading mode")
	_expect(_font_edit_state(code) == saved_state, "Font adjustment in reading mode changed editing state")
	var enlarged := code.get_theme_font_size("font_size")
	var window_size := get_tree().root.size
	get_tree().root.size = Vector2i(window_size.y, window_size.x)
	await _settle()
	_expect(code.get_theme_font_size("font_size") == enlarged, "Rotation reset the code font")
	get_tree().root.size = window_size
	await _settle()
	_inside_window(code, "enlarged code font")
	_expect(code.size.y >= window_size.y * 0.5, "Font controls reduced code height")
	RenderingServer.force_draw(false)
	_expect(get_viewport().get_texture().get_image().save_png(output.path_join("font-actions-%sx%s.png" % [window_size.x, window_size.y])) == OK, "Could not save enlarged-font screenshot")
	await _press_text_tool(editor, "PhoneFontReset", true)
	_expect(code.get_theme_font_size("font_size") == original_size, "Font reset did not return to configured size")
	_expect(surface.is_visible_in_tree(), "Font reset unexpectedly left reading mode")
	_expect(_font_edit_state(code) == saved_state, "Font reset changed editing state")
	await _press_text_tool(editor, "PhoneScrollMode")
	Input.emulate_mouse_from_touch = old_emulation
	observations.append({"control": "font_tools", "default_pixels": original_size,
		"enlarged_pixels": enlarged, "window": str(window_size),
		"scope": "Mouse and native taps; preserved text, selection, undo/redo, clipboard, focus, reading mode, orientation and code geometry"})

func _test_text_tools(base: Control, output: String) -> void:
	_mark("text_actions")
	# Match the documented explicit return from the Inspector to the workspace.
	EditorInterface.set_main_screen_editor("Script")
	EditorInterface.set_main_screen_editor("Script")
	EditorInterface.edit_script(load("res://phone_text_fixture.gd"), 0, 0, true)
	await _settle(45)
	var current := EditorInterface.get_script_editor().get_current_editor()
	if current == null:
		_expect(false, "No script editor opened for text actions")
		return
	var code := current.get_base_editor() as CodeEdit
	if code == null:
		_expect(false, "Script editor did not provide CodeEdit")
		return
	var editor := code.get_parent() as Control
	_expect(code.is_visible_in_tree(), "Code editor is hidden during text action checks")
	var tools := editor.find_child("PhoneCodeTools", true, false) as ScrollContainer
	if tools == null:
		_expect(false, "Phone code tools were not created")
		return
	_inside_window(code, "code editor")
	var primary := editor.find_child("PhoneCodePrimary", true, false) as Control
	_inside_window(primary, "primary code commands")
	for name in ["PhonePaste", "PhoneUndo", "PhoneLeft", "PhoneRight", "PhoneFontLarger", "PhoneMore"]:
		var button := editor.find_child(name, true, false) as Control
		_expect(button.is_visible_in_tree() and primary.get_global_rect().encloses(button.get_global_rect()), name + " is not immediately accessible")
	_expect(code.size.y >= get_tree().root.size.y * 0.5, "Less than half the window remains for code in compact mode")
	var status := editor.find_child("PhoneCodeStatus", true, false) as Control
	_expect(status != null and not status.is_visible_in_tree(), "Compact mode did not hide the code status row")
	var navigation := base.find_child("PhoneNavigation", true, false) as Control
	_expect(navigation.is_visible_in_tree(), "Unified tabs are inaccessible in code mode")
	await _press_text_tool(editor, "PhonePanels")
	_expect(navigation.is_visible_in_tree(), "Panels command did not restore navigation")
	_expect(status.is_visible_in_tree(), "Panels command did not restore the code status row")
	_inside_window(navigation, "restored navigation")
	_inside_window(code, "code with panels")
	await _press_text_tool(editor, "PhonePanels")
	_expect(navigation.is_visible_in_tree(), "Unified tabs disappeared when menus were collapsed")
	_expect(not status.is_visible_in_tree(), "Status row did not collapse with menus")
	var scripts := base.find_child("PhoneScriptList", true, false) as Control
	await _press_text_tool(editor, "PhoneScripts")
	_expect(scripts.is_visible_in_tree(), "Scripts command did not open the native list")
	_inside_window(scripts, "script list")
	_inside_window(code, "code with script list")
	await _press_text_tool(editor, "PhoneScripts")
	_expect(not scripts.is_visible_in_tree(), "Scripts command did not close the native list")
	var original := code.text
	code.text = ""
	code.grab_focus()
	var pasted := "var имя = 7\nvar text = \"Привет, мир 😀\""
	DisplayServer.clipboard_set(pasted)
	await _press_text_tool(editor, "PhonePaste")
	_expect(code.text == pasted, "Unicode multiline clipboard paste changed text")
	_expect(code.has_focus(), "Paste button stole keyboard focus")
	code.set_caret_line(0)
	code.set_caret_column(5)
	await _press_text_tool(editor, "PhoneSelectLine")
	_expect(code.get_selected_text() == "var имя = 7", "Select line did not select exactly the current line")
	await _press_text_tool(editor, "PhoneCopy")
	_expect(DisplayServer.clipboard_get() == "var имя = 7", "Copy did not preserve the selected line")
	DisplayServer.clipboard_set("var имя = 42")
	await _press_text_tool(editor, "PhonePaste")
	_expect(code.get_line(0) == "var имя = 42", "Paste did not replace the selected line")
	await _press_text_tool(editor, "PhoneUndo")
	_expect(code.text == pasted, "Undo did not restore text after line replacement")
	await _press_text_tool(editor, "PhoneRedo")
	_expect(code.get_line(0) == "var имя = 42", "Redo did not restore the replacement")
	code.deselect()
	code.set_caret_line(0)
	code.set_caret_column(4)
	await _press_text_tool(editor, "PhoneRight")
	_expect(code.get_caret_column() == 5, "Right arrow failed to move one Cyrillic character")
	await _press_text_tool(editor, "PhoneExtendSelection")
	await _press_text_tool(editor, "PhoneRight")
	_expect(code.get_selected_text() == "м", "Arrow selection did not select the next character")
	await _press_text_tool(editor, "PhoneExtendSelection")
	await _press_text_tool(editor, "PhoneCut")
	_expect(DisplayServer.clipboard_get() == "м" and code.get_line(0) == "var ия = 42", "Cut did not remove exactly the selection")
	await _press_text_tool(editor, "PhoneUndo")
	_expect(code.get_line(0) == "var имя = 42", "Cut could not be undone")
	await _test_font_tools(editor, code, output)
	await _test_direction_lock(editor, code)
	code.text = "# строка для прокрутки\n".repeat(200)
	code.deselect()
	code.set_caret_line(0)
	code.set_caret_column(3)
	code.set_v_scroll(0)
	await _press_text_tool(editor, "PhoneScrollMode")
	var surface := code.get_node("PhoneCodeScrollSurface") as Control
	_expect(surface.is_visible_in_tree(), "Scroll mode did not activate")
	var before := code.text
	var start := surface.get_global_rect().get_center()
	var press := InputEventMouseButton.new()
	press.button_index = MOUSE_BUTTON_LEFT
	press.pressed = true
	press.position = start
	press.global_position = start
	Input.parse_input_event(press)
	await _settle(3)
	var move := InputEventMouseMotion.new()
	move.position = start - Vector2(0, 60)
	move.global_position = move.position
	move.relative = Vector2(0, -60)
	move.button_mask = MOUSE_BUTTON_MASK_LEFT
	Input.parse_input_event(move)
	await _settle(3)
	press.pressed = false
	press.position = move.position
	press.global_position = move.position
	Input.parse_input_event(press)
	await _settle(3)
	_expect(code.get_v_scroll() > 0, "Reading mode drag did not scroll")
	_expect(code.text == before and not code.has_selection() and code.get_caret_line() == 0 and code.get_caret_column() == 3, "Reading mode changed code, selection or caret")
	await _press_text_tool(editor, "PhoneScrollMode")
	_expect(not surface.is_visible_in_tree(), "Could not return to editing mode")
	code.text = original
	code.set_caret_line(0)
	tools.scroll_horizontal = 0
	await _settle()
	RenderingServer.force_draw(false)
	_expect(get_viewport().get_texture().get_image().save_png(output.path_join("code-actions-%sx%s.png" % [get_tree().root.size.x, get_tree().root.size.y])) == OK, "Could not save code toolbar screenshot")
	observations.append({"control": "text_actions", "scope": "Real mouse clicks on the native CodeEdit toolbar; clipboard, line replacement, undo, redo, selection and reading drag"})
	EditorInterface.set_main_screen_editor("3D")
	await _settle()
	_expect(navigation.is_visible_in_tree(), "Leaving Script did not restore navigation")
	_expect((base.find_child("PhoneTopBarScroll", true, false) as Control).is_visible_in_tree(), "Leaving Script did not restore main menu")

func _run_probe() -> void:
	_mark("waiting_for_initial_frames")
	await _settle(45)
	_mark("initial_frames_received")
	var settings := EditorInterface.get_editor_settings()
	if OS.get_environment("PHONE_LAYOUT_BOOTSTRAP") == "1":
		settings.set_setting("interface/touchscreen/phone_single_panel_mode", true)
		settings.set_setting("interface/editor/appearance/display_scale", 7)
		settings.set_setting("interface/editor/appearance/custom_display_scale", float(OS.get_environment("PHONE_LAYOUT_SCALE")))
		settings.set_setting("interface/editor/localization/editor_language", "ru")
		settings.set_setting("interface/editor/behavior/save_on_focus_loss", false)
		settings.set_setting("interface/editor/display/vsync_mode", 0)
		if ResourceSaver.save(settings) != OK:
			push_error("Could not save isolated test settings")
			get_tree().quit(1)
			return
		_mark("bootstrap_complete")
		get_tree().quit(0)
		return

	var base: Control = EditorInterface.get_base_control()
	# Begin geometry checks in the scene workspace even if a prior test saved Script.
	EditorInterface.set_main_screen_editor("3D")
	await _settle()
	var navigation := base.find_child("PhoneNavigation", true, false) as Control
	var workspace := base.find_child("PhoneWorkspace", true, false) as Control
	# The code toolbar also contains a PhonePanels button after reopening Script.
	# Dock panels are the workspace's sibling, never a recursive name match.
	var panels: VBoxContainer = null
	if workspace != null:
		panels = workspace.get_node_or_null("../PhonePanels") as VBoxContainer
	if panels == null or navigation == null or workspace == null:
		push_error("Phone layout was not constructed")
		get_tree().quit(1)
		return

	var output := OS.get_environment("PHONE_LAYOUT_OUTPUT")
	DirAccess.make_dir_recursive_absolute(output)
	for window_size in [Vector2i(1920, 864), Vector2i(1536, 691), Vector2i(691, 1536)]:
		_mark("resize_%s" % window_size)
		print("PHONE_WINDOW_BEFORE ", get_tree().root.size, " min=", get_tree().root.min_size, " wrapping=", get_tree().root.wrap_controls, " contents=", get_tree().root.get_contents_minimum_size())
		get_tree().root.size = window_size
		print("PHONE_WINDOW_REQUESTED ", window_size, " immediate=", get_tree().root.size)
		await _settle()
		print("PHONE_WINDOW_SETTLED ", get_tree().root.size, " min=", get_tree().root.min_size, " wrapping=", get_tree().root.wrap_controls, " contents=", get_tree().root.get_contents_minimum_size())
		_expect(get_tree().root.size == window_size, "Window was enlarged beyond requested drawable size")
		_dump_widths(base, window_size.x - 100)
		for button_name in ["2D", "3D", "PhoneDockSceneTreeDock", "PhoneDockFileSystemDock", "PhoneDockInspectorDock", "PhoneDockSignalsDock", "PhoneDockGroupsDock", "PhoneDockImportDock", "PhoneDockHistoryDock"]:
			_mark("select_%s_%s" % [window_size, button_name])
			var button := base.find_child(button_name, true, false) as Button
			if button_name in ["2D", "3D"]:
				button = base.find_child("EditorMainScreenButtons", true, false).get_node(button_name) as Button
			if button == null:
				_expect(false, "Missing navigation button " + button_name)
				continue
			await _press_navigation(button, navigation as ScrollContainer)
			await _settle()
			var show_workspace: bool = button_name in ["2D", "3D"]
			_expect(workspace.is_visible_in_tree() == show_workspace, "Wrong workspace visibility after " + button_name)
			_expect(panels.is_visible_in_tree() != show_workspace, "Workspace and dock panels overlap after " + button_name)
			_inside_window(navigation, "navigation")
			_inside_window(button, button_name)
			var active: Control = workspace if show_workspace else panels
			_inside_window(active, button_name + " area")
			_expect(active.size.y >= window_size.y * 0.5, "Less than half the height remains for " + button_name)
			if not show_workspace:
				var tabs: TabContainer = null
				for child in panels.get_children():
					if child is TabContainer:
						tabs = child
				_expect(tabs != null, "Native dock tab container is missing after " + button_name)
				if tabs != null:
					_expect(not tabs.tabs_visible, "Duplicated dock tabs remain visible")
					var dock := tabs.get_current_tab_control()
					_expect(dock != null, "No native dock selected after " + button_name)
					if dock != null:
						_inside_window(dock, button_name + " dock")
						var expected := {"PhoneDockSceneTreeDock": "SceneTreeDock", "PhoneDockFileSystemDock": "FileSystemDock", "PhoneDockInspectorDock": "InspectorDock", "PhoneDockSignalsDock": "SignalsDock", "PhoneDockGroupsDock": "GroupsDock", "PhoneDockImportDock": "ImportDock", "PhoneDockHistoryDock": "HistoryDock"}
						_expect(dock.is_class(expected[button_name]), "Wrong native dock selected by " + button_name)
			# Force a frame: an idle editor may have no next redraw to await.
			_mark("capture_%s_%s" % [window_size, button_name])
			RenderingServer.force_draw(false)
			var screenshot := get_viewport().get_texture().get_image()
			var screenshot_path := output.path_join("%sx%s-%s.png" % [window_size.x, window_size.y, button_name])
			_expect(screenshot.save_png(screenshot_path) == OK, "Could not save UI screenshot")

	for code_size in [Vector2i(1536, 691), Vector2i(691, 1536)]:
		get_tree().root.size = code_size
		await _settle()
		await _test_sections_and_context(base)
		await _test_2d_tools(base)
		await _test_text_tools(base, output)
		await _test_native_touch(base)
	await _test_create_dialog(base)
	var report := {"failures": failures, "observations": observations,
		"scope": "Linux runtime of shared phone chrome and native code actions; Injected native touch events exercised on Linux; Android dispatch, system clipboard and IME remain device checks"}
	var report_file := FileAccess.open(output.path_join("geometry.json"), FileAccess.WRITE)
	if report_file == null:
		push_error("Could not write geometry report")
		get_tree().quit(1)
		return
	report_file.store_string(JSON.stringify(report, "\t"))
	report_file.close()
	print("PHONE_LAYOUT_RESULT ", "PASS" if failures.is_empty() else "FAIL")
	_mark("complete")
	get_tree().quit(0 if failures.is_empty() else 1)
