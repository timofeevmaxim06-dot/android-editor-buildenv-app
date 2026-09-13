"""Editor-only phone text actions, implemented on the existing CodeEdit."""


def add_edits(replace):
    header = "editor/gui/code_editor.h"
    source = "editor/gui/code_editor.cpp"
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
		// Primary actions first; the remaining row is reachable by a horizontal swipe.
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
    replace("editor/script/script_editor_plugin.cpp", "\t\t\tconst bool kb_visible = kb_height > 0;", """
			const bool kb_visible = kb_height > 0;
			if ((bool)EDITOR_GET("interface/touchscreen/phone_single_panel_mode")) {
				// Keep the code and its text actions above the Android keyboard.
				Control *base = EditorNode::get_singleton()->get_gui_base();
				const char *chrome_names[] = { "PhoneNavigation", "PhoneTopBarScroll" };
				for (const char *name : chrome_names) {
					Control *chrome = Object::cast_to<Control>(base->find_child(name, true, false));
					if (chrome) {
						chrome->set_visible(!kb_visible);
					}
				}
			}
""")
