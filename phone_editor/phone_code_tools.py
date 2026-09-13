"""Editor-only phone text actions, implemented on the existing CodeEdit."""


def add_edits(replace):
    header = "editor/gui/code_editor.h"
    source = "editor/gui/code_editor.cpp"
    script = "editor/script/script_editor_plugin.cpp"
    script_header = "editor/script/script_editor_plugin.h"
    replace(source, '#include "code_editor.h"', '#include "code_editor.h"\n#include "editor/script/script_editor_plugin.h"\n#include "servers/display/display_server.h"')
    replace(script, '#include "scene/gui/separator.h"', '#include "scene/gui/separator.h"\n#include "scene/gui/scroll_container.h"')
    replace(script_header, "\tbool restoring_layout;", """
	bool restoring_layout;
	bool phone_compact = true;
	Control *phone_menu_scroll = nullptr;
	HashMap<ObjectID, bool> phone_hidden_chrome;
	void update_phone_chrome();""")
    replace(script_header, "\tbool toggle_files_panel();", "\tvoid toggle_phone_chrome();\n\tbool toggle_files_panel();")
    replace(script, "bool ScriptEditor::toggle_files_panel() {", """
void ScriptEditor::toggle_phone_chrome() {
	phone_compact = !phone_compact;
	update_phone_chrome();
}

void ScriptEditor::update_phone_chrome() {
	if (!is_inside_tree() || !(bool)EDITOR_GET("interface/touchscreen/phone_single_panel_mode")) {
		return;
	}
	bool keyboard_visible = false;
#ifdef ANDROID_ENABLED
	keyboard_visible = is_visible_in_tree() && DisplayServer::get_singleton()->virtual_keyboard_get_height() > 0;
#endif
	// Help tabs have no code toolbar, so they must retain the normal navigation.
	const bool compact = is_visible_in_tree() && Object::cast_to<TextEditorBase>(_get_current_editor()) && (phone_compact || keyboard_visible);
	if (compact) {
		Control *base = EditorNode::get_singleton()->get_gui_base();
		Control *chrome[] = {
			Object::cast_to<Control>(base->find_child("PhoneNavigation", true, false)),
			Object::cast_to<Control>(base->find_child("PhoneTopBarScroll", true, false)),
			EditorSceneTabs::get_singleton(),
		};
		for (Control *control : chrome) {
			if (control) {
				const ObjectID id = control->get_instance_id();
				if (!phone_hidden_chrome.has(id)) {
					phone_hidden_chrome.insert(id, control->is_visible());
				}
				control->hide();
			}
		}
	} else {
		for (const KeyValue<ObjectID, bool> &entry : phone_hidden_chrome) {
			if (Control *control = Object::cast_to<Control>(ObjectDB::get_instance(entry.key))) {
				control->set_visible(entry.value);
			}
		}
		phone_hidden_chrome.clear();
	}
	if (phone_menu_scroll) {
		phone_menu_scroll->set_visible(!compact);
	}
}

bool ScriptEditor::toggle_files_panel() {""")
    replace(script, "\tmenu_hb = memnew(HBoxContainer);\n\tmain_container->add_child(menu_hb);", """
	menu_hb = memnew(HBoxContainer);
	if ((bool)EDITOR_GET("interface/touchscreen/phone_single_panel_mode")) {
		ScrollContainer *scroll = memnew(ScrollContainer);
		scroll->set_name("PhoneScriptMenuScroll");
		scroll->set_horizontal_scroll_mode(ScrollContainer::SCROLL_MODE_AUTO);
		scroll->set_vertical_scroll_mode(ScrollContainer::SCROLL_MODE_DISABLED);
		main_container->add_child(scroll);
		scroll->add_child(menu_hb);
		phone_menu_scroll = scroll;
	} else {
		main_container->add_child(menu_hb);
	}
""")
    replace(script, '\tlist_split->set_visible(EditorSettings::get_singleton()->get_project_metadata("files_panel", "show_files_panel", true));', """
	list_split->set_name("PhoneScriptList");
	const bool phone_mode = EDITOR_GET("interface/touchscreen/phone_single_panel_mode");
	list_split->set_visible(EditorSettings::get_singleton()->get_project_metadata("files_panel", phone_mode ? "show_phone_files_panel" : "show_files_panel", !phone_mode));
""")
    # Keep the native list toggle and persistence; its phone preference is separate.
    for path in (script, source):
        replace(path, 'set_project_metadata("files_panel", "show_files_panel",', 'set_project_metadata("files_panel", (bool)EDITOR_GET("interface/touchscreen/phone_single_panel_mode") ? "show_phone_files_panel" : "show_files_panel",')
    replace(script, "void ScriptEditor::_tab_changed(int p_which) {", """void ScriptEditor::_tab_changed(int p_which) {
	callable_mp(this, &ScriptEditor::update_phone_chrome).call_deferred();""")
    # Lists still scroll; one row of minimum height is enough on the phone.
    replace(script, "Size2(100, 60) * EDSCALE", 'Size2(100, (bool)EDITOR_GET("interface/touchscreen/phone_single_panel_mode") ? 24 : 60) * EDSCALE')
    for name in ("members_overview", "help_overview"):
        replace(script, name + "->set_custom_minimum_size(Size2(0, 60) * EDSCALE);", name + '->set_custom_minimum_size(Size2(0, (bool)EDITOR_GET("interface/touchscreen/phone_single_panel_mode") ? 24 : 60) * EDSCALE);')
    replace(script, "#ifdef ANDROID_ENABLED\n\t\tcase NOTIFICATION_VISIBILITY_CHANGED: {\n\t\t\tset_process(is_visible_in_tree());\n\t\t} break;\n\n\t\tcase NOTIFICATION_PROCESS:", """
		case NOTIFICATION_VISIBILITY_CHANGED: {
			update_phone_chrome();
#ifdef ANDROID_ENABLED
			set_process(is_visible_in_tree());
#endif
		} break;

#ifdef ANDROID_ENABLED
		case NOTIFICATION_PROCESS:""")
    replace(script, "\t\t\tEditorSceneTabs::get_singleton()->set_visible(!kb_height);\n\t\t\tmenu_hb->set_visible(!kb_visible);", """
			if ((bool)EDITOR_GET("interface/touchscreen/phone_single_panel_mode")) {
				update_phone_chrome();
			} else {
				EditorSceneTabs::get_singleton()->set_visible(!kb_height);
				menu_hb->set_visible(!kb_visible);
			}
""")
    replace("scene/gui/text_edit.h", "\tvoid set_virtual_keyboard_enabled(bool p_enabled);", "\tvoid refresh_virtual_keyboard();\n\tvoid set_virtual_keyboard_enabled(bool p_enabled);")
    replace("scene/gui/text_edit.cpp", "void TextEdit::_show_virtual_keyboard() {", """
void TextEdit::refresh_virtual_keyboard() {
	// Keep native IME text/selection synchronized after an editor toolbar action.
	// Never open a hidden keyboard or take focus from another field.
	if (has_focus() && DisplayServer::get_singleton()->virtual_keyboard_get_height() > 0) {
		_show_virtual_keyboard();
	}
}

void TextEdit::_show_virtual_keyboard() {""")
    replace(header, "\tFindReplaceBar *find_replace_bar = nullptr;", """
	FindReplaceBar *find_replace_bar = nullptr;
	Control *phone_scroll_surface = nullptr;
	Button *phone_scroll_button = nullptr;
	Button *phone_select_button = nullptr;
	void _phone_text_action(int p_action);
	void _phone_scroll_toggled(bool p_enabled);
	void _phone_scroll_input(const Ref<InputEvent> &p_event);
	Button *_phone_add_action(HBoxContainer *p_row, const String &p_name, const String &p_label, int p_action);
""")
    replace(source, '#include "scene/gui/separator.h"', '#include "scene/gui/separator.h"\n#include "scene/gui/scroll_container.h"')
    replace(source, "CodeTextEditor::CodeTextEditor() {", r"""
Button *CodeTextEditor::_phone_add_action(HBoxContainer *p_row, const String &p_name, const String &p_label, int p_action) {
	Button *button = memnew(Button);
	button->set_name(p_name);
	button->set_text(p_label);
	button->set_focus_mode(FOCUS_NONE); // Keep selection and the Android IME on the code.
	button->set_custom_minimum_size(Size2(36, 34) * EDSCALE);
	if (p_action >= 0) {
		button->connect(SceneStringName(pressed), callable_mp(this, &CodeTextEditor::_phone_text_action).bind(p_action));
	}
	p_row->add_child(button);
	return button;
}

void CodeTextEditor::_phone_scroll_toggled(bool p_enabled) {
	phone_scroll_surface->set_visible(p_enabled);
	phone_scroll_button->set_text(p_enabled ? String::utf8("Править") : String::utf8("Листать"));
}

void CodeTextEditor::_phone_scroll_input(const Ref<InputEvent> &p_event) {
	// Explicit reading mode: dragging cannot move the caret or change selection.
	Vector2 pixels;
	Ref<InputEventMouseMotion> motion = p_event;
	Ref<InputEventMouseButton> button = p_event;
	Ref<InputEventPanGesture> pan = p_event;
	if (motion.is_valid() && motion->get_button_mask().has_flag(MouseButtonMask::LEFT)) {
		pixels = -motion->get_relative();
	} else if (pan.is_valid()) {
		pixels = pan->get_delta();
#ifdef ANDROID_ENABLED
		pixels *= 5.0;
#endif
	} else if (button.is_valid() && button->is_pressed()) {
		if (button->get_button_index() == MouseButton::WHEEL_DOWN) {
			pixels.y = text_editor->get_line_height() * 3;
		} else if (button->get_button_index() == MouseButton::WHEEL_UP) {
			pixels.y = -text_editor->get_line_height() * 3;
		}
	}
	const real_t sensitivity = (int)EDITOR_GET("interface/touchscreen/phone_text_pan_percent") / 100.0;
	text_editor->set_v_scroll(text_editor->get_v_scroll() + pixels.y * sensitivity / MAX(1, text_editor->get_line_height()));
	text_editor->set_h_scroll(text_editor->get_h_scroll() + pixels.x * sensitivity);
	phone_scroll_surface->accept_event();
}

void CodeTextEditor::_phone_text_action(int p_action) {
	phone_scroll_button->set_pressed(false);
	text_editor->grab_focus();
	text_editor->apply_ime();
	switch (p_action) {
		case 0: text_editor->paste(); break;
		case 1: text_editor->copy(); break;
		case 2: text_editor->cut(); break;
		case 3: text_editor->undo(); break;
		case 4: text_editor->redo(); break;
		case 5: {
			text_editor->remove_secondary_carets();
			const int line = text_editor->get_caret_line();
			text_editor->select(line, 0, line, text_editor->get_line(line).length());
		} break;
		case 6: text_editor->select_all(); break;
		case 7: {
			text_editor->set_virtual_keyboard_show_on_focus(true);
			text_editor->release_focus();
			text_editor->grab_focus();
			text_editor->set_virtual_keyboard_show_on_focus(false);
		} break;
		case 8: _show_goto_popup_request(); break;
		case 9: {
#ifdef ANDROID_ENABLED
			DisplayServer::get_singleton()->virtual_keyboard_hide();
#endif
			ScriptEditor::get_singleton()->toggle_phone_chrome();
		} break;
		case 16: {
#ifdef ANDROID_ENABLED
			DisplayServer::get_singleton()->virtual_keyboard_hide();
#endif
			_toggle_files_pressed();
		} break;
		default: {
			const Key keys[] = { Key::LEFT, Key::RIGHT, Key::UP, Key::DOWN, Key::HOME, Key::END };
			ERR_FAIL_INDEX(p_action - 10, 6);
			Ref<InputEventKey> key;
			key.instantiate();
			key->set_keycode(keys[p_action - 10]);
			key->set_pressed(true);
			key->set_shift_pressed(phone_select_button->is_pressed());
			text_editor->gui_input(key);
		} break;
	}
	if (p_action != 7 && p_action != 8 && p_action != 9 && p_action != 16) {
		text_editor->refresh_virtual_keyboard();
	}
}

CodeTextEditor::CodeTextEditor() {""")
    replace(source, "\ttext_editor->set_deselect_on_focus_loss_enabled(false);", """
	text_editor->set_deselect_on_focus_loss_enabled(false);
	if ((bool)EDITOR_GET("interface/touchscreen/phone_single_panel_mode")) {
		ScrollContainer *tools = memnew(ScrollContainer);
		tools->set_name("PhoneCodeTools");
		tools->set_horizontal_scroll_mode(ScrollContainer::SCROLL_MODE_AUTO);
		tools->set_vertical_scroll_mode(ScrollContainer::SCROLL_MODE_DISABLED);
		tools->set_h_size_flags(SIZE_EXPAND_FILL);
		add_child(tools);
		move_child(tools, 0);
		HBoxContainer *row = memnew(HBoxContainer);
		tools->add_child(row);
		// Compact script mode keeps code usable at 200%; Panels restores navigation.
		_phone_add_action(row, "PhonePanels", String::utf8("Панели"), 9);
		_phone_add_action(row, "PhonePaste", String::utf8("Вставить"), 0);
		_phone_add_action(row, "PhoneUndo", String::utf8("Отмена"), 3);
		_phone_add_action(row, "PhoneSelectLine", String::utf8("Строка"), 5);
		_phone_add_action(row, "PhoneCopy", String::utf8("Копировать"), 1);
		_phone_add_action(row, "PhoneLeft", String::utf8("←"), 10);
		_phone_add_action(row, "PhoneRight", String::utf8("→"), 11);
		phone_select_button = _phone_add_action(row, "PhoneExtendSelection", String::utf8("Выделять"), -1);
		phone_select_button->set_toggle_mode(true);
		phone_select_button->set_tooltip_text(String::utf8("Включите и нажимайте стрелки, чтобы точно выделить текст."));
		phone_scroll_button = _phone_add_action(row, "PhoneScrollMode", String::utf8("Листать"), -1);
		phone_scroll_button->set_toggle_mode(true);
		phone_scroll_button->set_tooltip_text(String::utf8("Прокрутка одним пальцем без перемещения курсора. Нажмите «Править», чтобы вернуться к вводу."));
		phone_scroll_button->connect(SceneStringName(toggled), callable_mp(this, &CodeTextEditor::_phone_scroll_toggled));
		_phone_add_action(row, "PhoneKeyboard", String::utf8("Клавиатура"), 7);
		_phone_add_action(row, "PhoneUp", String::utf8("↑"), 12);
		_phone_add_action(row, "PhoneDown", String::utf8("↓"), 13);
		_phone_add_action(row, "PhoneHome", String::utf8("Начало"), 14);
		_phone_add_action(row, "PhoneEnd", String::utf8("Конец"), 15);
		_phone_add_action(row, "PhoneCut", String::utf8("Вырезать"), 2);
		_phone_add_action(row, "PhoneRedo", String::utf8("Повтор"), 4);
		_phone_add_action(row, "PhoneSelectAll", String::utf8("Всё"), 6);
		_phone_add_action(row, "PhoneGoToLine", String::utf8("К строке"), 8);
		_phone_add_action(row, "PhoneScripts", String::utf8("Скрипты"), 16);
		phone_scroll_surface = memnew(Control);
		phone_scroll_surface->set_name("PhoneCodeScrollSurface");
		text_editor->add_child(phone_scroll_surface);
		phone_scroll_surface->set_anchors_and_offsets_preset(Control::PRESET_FULL_RECT);
		phone_scroll_surface->set_mouse_filter(MOUSE_FILTER_STOP);
		phone_scroll_surface->set_focus_mode(FOCUS_NONE);
		phone_scroll_surface->hide();
		phone_scroll_surface->connect(SceneStringName(gui_input), callable_mp(this, &CodeTextEditor::_phone_scroll_input));
	}
""")
