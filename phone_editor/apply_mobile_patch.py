"""Fail-closed, editor-only preview patch for one pinned Godot source revision.

Run on a disposable checkout, never on a user's game or installed editor.
All anchors are checked before any file is changed. No signing material is used.
"""

from pathlib import Path
import argparse
import json

GODOT_COMMIT = "ed1daf0bf001b61586d9930840f2f1394092c079"
APP_ID = "org.godotengine.editor.v4.phonepreview1"
EDITS = []


def replace(path, old, new):
    EDITS.append((path, old, new))


EDITOR = "platform/android/java/editor/"
replace(EDITOR + "build.gradle", 'applicationId "org.godotengine.editor.v4"',
        f'applicationId "{APP_ID}"')
replace(EDITOR + "build.gradle", 'editorAppName: "Godot Engine 4"',
        'editorAppName: "Godot Phone Preview 1"')
# Reuse the working SAF build provider without changing GABE or its data.
for relative in ("src/main/AndroidManifest.xml",
                 "src/main/java/org/godotengine/editor/buildprovider/GradleBuildEnvironmentClient.kt"):
    replace(EDITOR + relative, "org.godotengine.godot_gradle_build_environment",
            "org.godotengine.godot_gradle_build_environment.saftest")

SETTINGS = "editor/settings/editor_settings.cpp"
replace(SETTINGS, "\t// Scene tabs\n", """
	// Phone preview settings affect editor controls only. Restart gives a clean layout.
	EDITOR_SETTING_BASIC(Variant::INT, PROPERTY_HINT_RANGE, "interface/touchscreen/phone_target_size_dp", 48, "32,64,1")
	set_restart_if_changed("interface/touchscreen/phone_target_size_dp", true);
	EDITOR_SETTING_BASIC(Variant::INT, PROPERTY_HINT_RANGE, "interface/touchscreen/phone_text_pan_percent", 100, "25,200,5")
	set_restart_if_changed("interface/touchscreen/phone_text_pan_percent", true);
	EDITOR_SETTING_BASIC(Variant::BOOL, PROPERTY_HINT_NONE, "interface/touchscreen/phone_scrollable_top_bar", is_android_editor, "")
	set_restart_if_changed("interface/touchscreen/phone_scrollable_top_bar", true);

	// Scene tabs
""")

THEME = "editor/themes/editor_theme_manager.cpp"
replace(THEME, "\t_populate_visual_shader_styles(theme, config);\n", """	_populate_visual_shader_styles(theme, config);

#ifdef ANDROID_ENABLED
	if (config.enable_touch_optimizations && !OS::get_singleton()->has_feature("xr_editor")) {
		// Android's screen_get_dpi is densityDpi, not physical xdpi. Do not use
		// screen_get_scale: the Android editor clamps it to fit its desktop layout.
		const int target_dp = CLAMP((int)EDITOR_GET("interface/touchscreen/phone_target_size_dp"), 32, 64);
		const int target_px = Math::ceil(target_dp * MAX(1.0, DisplayServer::get_singleton()->screen_get_dpi() / 160.0));
		theme->set_constant("phone_minimum_target", "Button", target_px);
		theme->set_constant("phone_minimum_target", "LineEdit", target_px);
		theme->set_constant("phone_minimum_target", "Tree", target_px);
		theme->set_constant("inspector_property_height", EditorStringName(Editor), MAX(target_px, theme->get_constant("inspector_property_height", EditorStringName(Editor))));
		theme->set_constant("phone_pan_percent", "TextEdit", CLAMP((int)EDITOR_GET("interface/touchscreen/phone_text_pan_percent"), 25, 200));

		// Popup rows and real tab rectangles grow with their backgrounds.
		const int font_height = theme->get_font("font", "PopupMenu")->get_height(theme->get_font_size("font_size", "PopupMenu"));
		theme->set_constant("v_separation", "PopupMenu", MAX(theme->get_constant("v_separation", "PopupMenu"), target_px - font_height));
		List<StringName> types;
		theme->get_type_list(&types);
		for (const StringName &type : types) {
			List<StringName> styles;
			theme->get_stylebox_list(type, &styles);
			for (const StringName &style_name : styles) {
				if (style_name != "tab_selected" && style_name != "tab_unselected" && style_name != "tab_hovered" && style_name != "tab_disabled") {
					continue;
				}
				Ref<StyleBox> style = theme->get_stylebox(style_name, type)->duplicate();
				const int tab_font_height = theme->get_font("font", "TabBar")->get_height(theme->get_font_size("font_size", "TabBar"));
				const float margin = MAX(0, target_px - tab_font_height) / 2.0;
				style->set_content_margin(SIDE_TOP, MAX(style->get_content_margin(SIDE_TOP), margin));
				style->set_content_margin(SIDE_BOTTOM, MAX(style->get_content_margin(SIDE_BOTTOM), margin));
				theme->set_stylebox(style_name, type, style);
			}
		}
	}
#endif
""")

BUTTON = "scene/gui/button.cpp"
replace(BUTTON, '#include "core/object/callable_mp.h"',
        '#include "core/config/engine.h"\n#include "core/object/callable_mp.h"')
replace(BUTTON, '\treturn get_minimum_size_for_text_and_icon("", _icon);', """	Size2 size = get_minimum_size_for_text_and_icon("", _icon);
#if defined(ANDROID_ENABLED) && defined(TOOLS_ENABLED)
	if (Engine::get_singleton()->is_editor_hint() && has_theme_constant("phone_minimum_target", "Button")) {
		const int target = get_theme_constant("phone_minimum_target", "Button");
		size = size.max(Size2(target, target));
	}
#endif
	return size;""")

LINE = "scene/gui/line_edit.cpp"
replace(LINE, "\treturn style_min_size + min_size;", """	Size2 size = style_min_size + min_size;
#if defined(ANDROID_ENABLED) && defined(TOOLS_ENABLED)
	if (Engine::get_singleton()->is_editor_hint() && has_theme_constant("phone_minimum_target", "LineEdit")) {
		const int target = get_theme_constant("phone_minimum_target", "LineEdit");
		size = size.max(Size2(target, target));
	}
#endif
	return size;""")

TREE = "scene/gui/tree.cpp"
replace(TREE, '#include "core/config/project_settings.h"',
        '#include "core/config/engine.h"\n#include "core/config/project_settings.h"')
replace(TREE, "\tint item_min_height = MAX(font_height, p_item->get_custom_minimum_height());", """	int item_min_height = MAX(font_height, p_item->get_custom_minimum_height());
#if defined(ANDROID_ENABLED) && defined(TOOLS_ENABLED)
	if (Engine::get_singleton()->is_editor_hint() && has_theme_constant("phone_minimum_target", "Tree")) {
		item_min_height = MAX(item_min_height, get_theme_constant("phone_minimum_target", "Tree"));
	}
#endif""")

TEXT = "scene/gui/text_edit.cpp"
replace(TEXT, "\t\tconst real_t delta = pan_gesture->get_delta().y;", """		Vector2 pan_delta = pan_gesture->get_delta();
		real_t horizontal_multiplier = 100.0;
#if defined(ANDROID_ENABLED) && defined(TOOLS_ENABLED)
		if (Engine::get_singleton()->is_editor_hint() && has_theme_constant("phone_pan_percent", "TextEdit")) {
			// GodotGestureHandler sends Android motion pixels / 5. Recover pixels,
			// then convert vertical motion to rows. No change to mouse-wheel input,
			// caret/selection gestures, desktop builds, or exported game templates.
			const real_t sensitivity = get_theme_constant("phone_pan_percent", "TextEdit") / 100.0;
			pan_delta *= 5.0 * sensitivity;
			pan_delta.y /= MAX(1, get_line_height());
			horizontal_multiplier = 1.0;
		}
#endif
		const real_t delta = pan_delta.y;""")
replace(TEXT, "h_scroll->set_value(h_scroll->get_value() + pan_gesture->get_delta().x * 100);",
        "h_scroll->set_value(h_scroll->get_value() + pan_delta.x * horizontal_multiplier);")

NODE = "editor/editor_node.cpp"
replace(NODE, '#include "editor_node.h"',
        '#include "editor_node.h"\n\n#include "scene/gui/scroll_container.h"')
replace(NODE, "\ttitle_bar = memnew(EditorTitleBar);\n\tbase_vbox->add_child(title_bar);", """	title_bar = memnew(EditorTitleBar);
	if ((bool)EDITOR_GET("interface/touchscreen/phone_scrollable_top_bar") && !OS::get_singleton()->has_feature("xr_editor")) {
		ScrollContainer *phone_top_scroll = memnew(ScrollContainer);
		phone_top_scroll->set_name("PhoneTopBarScroll");
		phone_top_scroll->set_h_size_flags(Control::SIZE_EXPAND_FILL);
		phone_top_scroll->set_horizontal_scroll_mode(ScrollContainer::SCROLL_MODE_AUTO);
		phone_top_scroll->set_vertical_scroll_mode(ScrollContainer::SCROLL_MODE_DISABLED);
		base_vbox->add_child(phone_top_scroll);
		phone_top_scroll->add_child(title_bar);
	} else {
		base_vbox->add_child(title_bar);
	}""")


def prepare(root):
    version = (root / "version.py").read_text()
    for value in ('major = 4', 'minor = 7', 'patch = 2', 'status = "stable"'):
        if value not in version.splitlines():
            raise ValueError(f"Not the expected Godot 4.7.2 stable source: {value}")
    pending = {}
    for relative, old, new in EDITS:
        original = pending.get(relative)
        if original is None:
            original = (root / relative).read_text()
        count = original.count(old)
        if count != 1:
            raise ValueError(f"Expected exactly one anchor in {relative}, found {count}: {old[:90]!r}")
        pending[relative] = original.replace(old, new, 1)
    return pending


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--check", action="store_true", help="Validate without changing files")
    args = parser.parse_args()
    pending = prepare(args.source)
    if not args.check:
        for relative, content in pending.items():
            (args.source / relative).write_text(content)
    print(json.dumps({"status": "VALIDATED" if args.check else "PATCHED",
                      "upstream_commit": GODOT_COMMIT,
                      "application_id_base": APP_ID,
                      "changed_files": sorted(pending)}, indent=2))


if __name__ == "__main__":
    main()
