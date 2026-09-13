"""Preview 2: native dock navigation, no global minimum-size inflation.

Only the isolated app/provider identity and text-pan conversion are reused
from preview 1. Layout is implemented through Godot 4.7.2's DockManager.
"""
import argparse
import json
from pathlib import Path
import apply_mobile_patch as v1
import phone_code_tools

GODOT_COMMIT = v1.GODOT_COMMIT
APP_ID = "org.godotengine.editor.v4.phonepreview2"
EDITS = []
for path, old, new in v1.EDITS:
    if path.startswith(v1.EDITOR) or path == v1.TEXT:
        EDITS.append((path, old, new.replace(v1.APP_ID, APP_ID).replace("Godot Phone Preview 1", "Godot Phone Preview 2")))


def replace(path, old, new):
    EDITS.append((path, old, new))


replace(v1.SETTINGS, "\t// Scene tabs\n", """	// Phone layout is also selectable on desktop for geometry regression checks.
	EDITOR_SETTING_BASIC(Variant::BOOL, PROPERTY_HINT_NONE, "interface/touchscreen/phone_single_panel_mode", is_android_editor, "")
	set_restart_if_changed("interface/touchscreen/phone_single_panel_mode", true);
	EDITOR_SETTING_BASIC(Variant::INT, PROPERTY_HINT_RANGE, "interface/touchscreen/phone_text_pan_percent", 100, "25,200,5")
	set_restart_if_changed("interface/touchscreen/phone_text_pan_percent", true);

	// Scene tabs
""")
replace(v1.THEME, "\t_populate_visual_shader_styles(theme, config);\n", """	_populate_visual_shader_styles(theme, config);
#ifdef ANDROID_ENABLED
	if (config.enable_touch_optimizations && !OS::get_singleton()->has_feature("xr_editor")) {
		theme->set_constant("phone_pan_percent", "TextEdit", CLAMP((int)EDITOR_GET("interface/touchscreen/phone_text_pan_percent"), 25, 200));
	}
#endif
""")

MANAGER_H = "editor/docks/editor_dock_manager.h"
MANAGER_CPP = "editor/docks/editor_dock_manager.cpp"
replace(MANAGER_H, "\tbool docks_visible = true;", """	bool docks_visible = true;
	DockTabContainer *phone_slot = nullptr;
	Control *phone_workspace = nullptr;
	Control *phone_panels = nullptr;""")
replace(MANAGER_H, "\tvoid update_docks_menu();", """	void setup_phone_layout(DockTabContainer *p_slot, Control *p_workspace, Control *p_panels);
	void show_phone_workspace(bool p_show);
	void update_docks_menu();""")
replace(MANAGER_CPP, "void EditorDockManager::_move_dock(EditorDock *p_dock, Control *p_target, int p_tab_index, bool p_set_current) {", """void EditorDockManager::setup_phone_layout(DockTabContainer *p_slot, Control *p_workspace, Control *p_panels) {
	ERR_FAIL_COND(!all_docks.is_empty()); // Configure before registering docks.
	phone_slot = p_slot;
	phone_workspace = p_workspace;
	phone_panels = p_panels;
	show_phone_workspace(true);
}

void EditorDockManager::show_phone_workspace(bool p_show) {
	if (!phone_slot) {
		return;
	}
	if (!p_show) {
		EditorNode::get_singleton()->set_distraction_free_mode(false);
	}
	phone_workspace->set_visible(p_show);
	phone_panels->set_visible(!p_show);
}

void EditorDockManager::_move_dock(EditorDock *p_dock, Control *p_target, int p_tab_index, bool p_set_current) {""")
replace(MANAGER_CPP, "\tNode *parent = p_dock->get_parent();\n\tif (parent == p_target)", """	// Keep registration, selection, feature profiles and persistence with the
	// native manager. Only vertical docking destinations are consolidated.
	DockTabContainer *requested_slot = Object::cast_to<DockTabContainer>(p_target);
	if (phone_slot && requested_slot && requested_slot->layout == EditorDock::DOCK_LAYOUT_VERTICAL) {
		p_target = phone_slot;
	}
	Node *parent = p_dock->get_parent();
	if (parent == p_target)""")
replace(MANAGER_CPP, "\tDockTabContainer *tab_container = p_dock->get_parent_container();\n\tif (!tab_container", """	DockTabContainer *tab_container = p_dock->get_parent_container();
	// Explicit dock navigation may reveal panels; background inspector updates
	// must not steal the workspace while editing a scene or a script.
	if (phone_slot && tab_container == phone_slot && p_grab_focus) {
		show_phone_workspace(false);
	}
	if (!tab_container""")

NODE = v1.NODE
replace(NODE, '#include "editor_node.h"', '#include "editor_node.h"\n\n#include "scene/gui/flow_container.h"\n#include "scene/gui/scroll_container.h"')
for path, old, new in v1.EDITS:
    if path == NODE and 'phone_top_scroll' in new:
        replace(path, old, new.replace('phone_scrollable_top_bar', 'phone_single_panel_mode'))
replace(NODE, "\ttitle_bar = memnew(EditorTitleBar);\n\tmain_vbox->add_child(title_bar);", """
	title_bar = memnew(EditorTitleBar);
	if ((bool)EDITOR_GET("interface/touchscreen/phone_single_panel_mode")) {
		// Exercise the same scrollable phone chrome in the desktop runtime test.
		ScrollContainer *phone_top_scroll = memnew(ScrollContainer);
		phone_top_scroll->set_name("PhoneTopBarScroll");
		phone_top_scroll->set_h_size_flags(Control::SIZE_EXPAND_FILL);
		phone_top_scroll->set_horizontal_scroll_mode(ScrollContainer::SCROLL_MODE_AUTO);
		phone_top_scroll->set_vertical_scroll_mode(ScrollContainer::SCROLL_MODE_DISABLED);
		main_vbox->add_child(phone_top_scroll);
		phone_top_scroll->add_child(title_bar);
	} else {
		main_vbox->add_child(title_bar);
	}
""")
replace(NODE, "\t\tconst Size2 minimum_size = Size2(1024, 600) * EDSCALE;", """		// A desktop-sized forced window is larger than a phone's drawable area.
		const bool phone_mode = EDITOR_GET("interface/touchscreen/phone_single_panel_mode");
		const Size2 minimum_size = phone_mode ? Size2(360, 240) : Size2(1024, 600) * EDSCALE;""")
replace(NODE, "\tLocalVector<DockTabContainer *> dock_slots;", """	HFlowContainer *phone_navigation = nullptr;
	LocalVector<DockTabContainer *> dock_slots;""")
replace(NODE, "\teditor_main_screen->set_v_size_flags(Control::SIZE_EXPAND_FILL);", """	editor_main_screen->set_v_size_flags(Control::SIZE_EXPAND_FILL);

	if ((bool)EDITOR_GET("interface/touchscreen/phone_single_panel_mode")) {
		// Reuse a registered native slot in the center. Empty side slots collapse
		// naturally, including after restoring a saved desktop dock layout.
		// The split auto-shows itself when its children change visibility, so
		// switch a plain wrapper rather than hiding the split directly.
		VBoxContainer *phone_workspace = memnew(VBoxContainer);
		phone_workspace->set_name("PhoneWorkspace");
		phone_workspace->set_v_size_flags(Control::SIZE_EXPAND_FILL);
		phone_workspace->set_h_size_flags(Control::SIZE_EXPAND_FILL);
		center_vb->remove_child(center_split);
		center_vb->add_child(phone_workspace);
		phone_workspace->add_child(center_split);
		VBoxContainer *phone_panels = memnew(VBoxContainer);
		phone_panels->set_name("PhonePanels");
		phone_panels->set_v_size_flags(Control::SIZE_EXPAND_FILL);
		phone_panels->set_h_size_flags(Control::SIZE_EXPAND_FILL);
		center_vb->add_child(phone_panels);
		for (DockTabContainer *slot : dock_slots) {
			if (slot->dock_slot == EditorDock::DOCK_SLOT_RIGHT_UL) {
				slot->get_parent()->remove_child(slot);
				phone_panels->add_child(slot);
				slot->set_custom_minimum_size(Size2());
				slot->set_use_hidden_tabs_for_min_size(false);
				editor_dock_manager->setup_phone_layout(slot, phone_workspace, phone_panels);
				break;
			}
		}
		phone_navigation = memnew(HFlowContainer);
		phone_navigation->set_name("PhoneNavigation");
		center_vb->add_child(phone_navigation);
		center_vb->move_child(phone_navigation, 0);
		Button *workspace_button = memnew(Button);
		workspace_button->set_name("PhoneWorkspaceButton");
		workspace_button->set_text(TTR("Editor"));
		workspace_button->set_custom_minimum_size(Size2(0, 32 * EDSCALE));
		workspace_button->connect(SceneStringName(pressed), callable_mp(editor_dock_manager, &EditorDockManager::show_phone_workspace).bind(true));
		phone_navigation->add_child(workspace_button);
	}
""")
replace(NODE, "\teditor_dock_manager->add_dock(history_dock);", """	editor_dock_manager->add_dock(history_dock);
	if (phone_navigation) {
		EditorDock *phone_docks[] = { SceneTreeDock::get_singleton(), filesystem_dock, InspectorDock::get_singleton() };
		const char *phone_names[] = { "PhoneSceneButton", "PhoneFilesButton", "PhoneInspectorButton" };
		for (int i = 0; i < 3; i++) {
			Button *button = memnew(Button);
			button->set_name(phone_names[i]);
			button->set_text(phone_docks[i]->get_display_title());
			button->set_custom_minimum_size(Size2(0, 32 * EDSCALE));
			button->connect(SceneStringName(pressed), callable_mp(editor_dock_manager, &EditorDockManager::focus_dock).bind(phone_docks[i]));
			phone_navigation->add_child(button);
		}
	}
""")

MAIN_SCREEN = "editor/editor_main_screen.cpp"
replace(MAIN_SCREEN, '#include "editor/editor_node.h"', '#include "editor/editor_node.h"\n#include "editor/docks/editor_dock_manager.h"')
replace(MAIN_SCREEN, "\ttb->connect(SceneStringName(pressed), callable_mp(this, &EditorMainScreen::select).bind(buttons.size()));", """	tb->connect(SceneStringName(pressed), callable_mp(this, &EditorMainScreen::select).bind(buttons.size()));
	tb->connect(SceneStringName(pressed), callable_mp(EditorDockManager::get_singleton(), &EditorDockManager::show_phone_workspace).bind(true));""")


# Run the Android chrome tree, including its action strip, in the desktop
# phone-layout test too. Desktop mode without the setting keeps its old tree.
replace(NODE, '#ifdef ANDROID_ENABLED\n#include "editor/gui/touch_actions_panel.h"\n#endif // ANDROID_ENABLED', '#include "editor/gui/touch_actions_panel.h"')
replace("editor/editor_node.h", "#ifdef ANDROID_ENABLED\n\tVBoxContainer *base_vbox", "\tVBoxContainer *base_vbox")
replace("editor/editor_node.h", "\tvoid _touch_actions_panel_mode_changed();\n#endif", "\tvoid _touch_actions_panel_mode_changed();")
replace("editor/editor_node.h", "#ifdef ANDROID_ENABLED\nclass TouchActionsPanel;\n#endif", "class TouchActionsPanel;")
replace(NODE, "#ifdef ANDROID_ENABLED\nvoid EditorNode::_touch_actions_panel_mode_changed()", "void EditorNode::_touch_actions_panel_mode_changed()")
replace(NODE, '\n#endif\n\n#ifdef MACOS_ENABLED\nextern "C" GameViewPluginBase', '\n\n#ifdef MACOS_ENABLED\nextern "C" GameViewPluginBase')
replace(NODE, "#ifdef ANDROID_ENABLED\n\tbase_vbox = memnew(VBoxContainer);", """
#ifdef ANDROID_ENABLED
	const bool use_phone_chrome = true;
#else
	const bool use_phone_chrome = EDITOR_GET("interface/touchscreen/phone_single_panel_mode");
#endif
	if (use_phone_chrome) {
	base_vbox = memnew(VBoxContainer);""")
replace(NODE, "\tgui_base->add_child(base_vbox);\n#else", "\tgui_base->add_child(base_vbox);\n\t} else {")
replace(NODE, "\n#endif\n\n\tDockSplitContainer *main_vsplit", "\n\t}\n\n\tDockSplitContainer *main_vsplit")

TOUCH = "editor/gui/touch_actions_panel.cpp"
replace(TOUCH, '#include "scene/gui/texture_rect.h"', '#include "scene/gui/texture_rect.h"\n#include "scene/gui/scroll_container.h"')
replace(TOUCH, "\tadd_child(box);", """
	if (!is_floating && (bool)EDITOR_GET("interface/touchscreen/phone_single_panel_mode")) {
		ScrollContainer *scroll = memnew(ScrollContainer);
		scroll->set_name("PhoneTouchActionsScroll");
		scroll->set_horizontal_scroll_mode(ScrollContainer::SCROLL_MODE_DISABLED);
		scroll->set_vertical_scroll_mode(ScrollContainer::SCROLL_MODE_AUTO);
		add_child(scroll);
		scroll->add_child(box);
	} else {
		add_child(box);
	}
""")

phone_code_tools.add_edits(replace)


def prepare(root):
    version = (root / "version.py").read_text().splitlines()
    if not all(value in version for value in ('major = 4', 'minor = 7', 'patch = 2', 'status = "stable"')):
        raise ValueError("Requires pristine Godot 4.7.2 stable")
    pending = {}
    for relative, old, new in EDITS:
        original = pending.get(relative)
        if original is None:
            original = (root / relative).read_text()
        if original.count(old) != 1:
            raise ValueError(f"Ambiguous or missing anchor in {relative}: {old[:100]!r}")
        pending[relative] = original.replace(old, new, 1)
    return pending


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    pending = prepare(args.source)
    if not args.check:
        for path, content in pending.items():
            (args.source / path).write_text(content)
    print(json.dumps({"preview": 2, "status": "VALIDATED" if args.check else "PATCHED",
                      "godot_commit": GODOT_COMMIT, "app_id": APP_ID,
                      "files": sorted(pending)}, indent=2))
