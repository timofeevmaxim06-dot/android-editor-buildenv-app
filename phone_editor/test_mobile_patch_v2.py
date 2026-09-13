"""Patch invariants. Runtime geometry is tested separately by layout_probe."""
from pathlib import Path
import sys
import unittest
import apply_mobile_patch_v2 as patch

SOURCE = Path(sys.argv.pop())


class Preview2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pending = patch.prepare(SOURCE)

    def test_no_global_control_size_patch(self):
        for path in ("scene/gui/button.cpp", "scene/gui/line_edit.cpp", "scene/gui/tree.cpp"):
            self.assertNotIn(path, self.pending)
        self.assertNotIn("phone_minimum_target", "\n".join(self.pending.values()))
        self.assertNotIn("phone_target_size_dp", self.pending[patch.v1.SETTINGS])

    def test_identity_isolated_from_both_previous_editors(self):
        gradle = self.pending[patch.v1.EDITOR + "build.gradle"]
        self.assertIn('applicationId "' + patch.APP_ID + '"', gradle)
        self.assertNotIn('applicationId "' + patch.v1.APP_ID + '"', gradle)
        self.assertNotIn('applicationId "org.godotengine.editor.v4"', gradle)

    def test_native_dock_ownership_preserved(self):
        node = self.pending[patch.NODE]
        self.assertIn("editor_dock_manager->add_dock(SceneTreeDock::get_singleton())", node)
        self.assertIn("editor_dock_manager->add_dock(filesystem_dock)", node)
        self.assertIn("editor_dock_manager->add_dock(InspectorDock::get_singleton())", node)
        self.assertIn("EditorDock::DOCK_LAYOUT_VERTICAL", self.pending[patch.MANAGER_CPP])
        self.assertIn("p_grab_focus", self.pending[patch.MANAGER_CPP])
        self.assertNotIn("MobileDockPlugin", node)

    def test_window_minimum_not_scaled_in_phone_mode(self):
        self.assertIn("phone_mode ? Size2(360, 240) : Size2(1024, 600) * EDSCALE", self.pending[patch.NODE])

    def test_no_hidden_tab_size_accumulation(self):
        self.assertIn("slot->set_use_hidden_tabs_for_min_size(false)", self.pending[patch.NODE])
        self.assertIn("slot->set_custom_minimum_size(Size2())", self.pending[patch.NODE])

    def test_text_pan_guard_preserved_without_new_gesture_changes(self):
        text = self.pending[patch.v1.TEXT]
        self.assertIn("#if defined(ANDROID_ENABLED) && defined(TOOLS_ENABLED)", text)
        self.assertIn("Engine::get_singleton()->is_editor_hint()", text)
        self.assertIn("pan_delta.y /= MAX(1, get_line_height())", text)
        self.assertFalse(any("GodotGestureHandler" in p for p in self.pending))

    def test_main_mode_buttons_reveal_workspace(self):
        self.assertIn("EditorDockManager::show_phone_workspace).bind(true)", self.pending[patch.MAIN_SCREEN])


if __name__ == "__main__":
    unittest.main()
