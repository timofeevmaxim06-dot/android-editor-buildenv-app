"""Source/recipe checks, not device UX acceptance or independent QA."""

from pathlib import Path
import sys
import tempfile
import unittest

import apply_mobile_patch as patch


class MobilePatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(sys.argv.pop()) if len(sys.argv) > 1 else None
        if cls.source is None or not (cls.source / "version.py").is_file():
            raise RuntimeError("Supply the pristine pinned Godot source directory")
        cls.changed = patch.prepare(cls.source)

    def test_pristine_files_not_modified(self):
        self.assertEqual(patch.prepare(self.source), self.changed)

    def test_exact_change_surface(self):
        self.assertEqual(len(self.changed), 10)
        self.assertTrue(all("project.godot" not in p for p in self.changed))
        for p, content in self.changed.items():
            self.assertNotEqual(content, (self.source / p).read_text())

    def test_only_isolated_editor_identity(self):
        gradle = self.changed[patch.EDITOR + "build.gradle"]
        self.assertIn('applicationId "' + patch.APP_ID + '"', gradle)
        self.assertNotIn('applicationId "org.godotengine.editor.v4"', gradle)
        self.assertNotIn("secrets.", gradle)
        manifest = self.changed[patch.EDITOR + "src/main/AndroidManifest.xml"]
        self.assertIn("godot_gradle_build_environment.saftest", manifest)
        # Do not enable portrait until the central-dock layout is ported and tested.
        self.assertIn('android:screenOrientation="userLandscape"', manifest)

    def test_runtime_and_desktop_are_guarded(self):
        for path in (patch.BUTTON, patch.LINE, patch.TREE, patch.TEXT):
            content = self.changed[path]
            self.assertIn("#if defined(ANDROID_ENABLED) && defined(TOOLS_ENABLED)", content)
            self.assertIn("Engine::get_singleton()->is_editor_hint()", content)
            self.assertIn("has_theme_constant(\"phone_", content)

    def test_no_gesture_bridge_changes(self):
        self.assertFalse(any("GodotGestureHandler" in p for p in self.changed))
        # Conversion assumes this exact upstream bridge; fail if it changes.
        bridge = self.source / "platform/android/java/lib/src/main/java/org/godotengine/godot/input/GodotGestureHandler.kt"
        self.assertIn("handlePanEvent(x, y, distanceX / 5f, distanceY / 5f)", bridge.read_text())

    def test_pan_units(self):
        for movement in (-240.0, -7.5, 0.0, 7.5, 240.0):
            for height in (16, 32, 64):
                native_delta = movement / 5
                rows = native_delta * 5 / height
                self.assertAlmostEqual(rows * height, movement)
                self.assertAlmostEqual(native_delta * 5, movement)
        self.assertIn("pan_delta.y /= MAX(1, get_line_height())", self.changed[patch.TEXT])
        self.assertIn("horizontal_multiplier = 1.0", self.changed[patch.TEXT])

    def test_target_units(self):
        for dpi in (160, 240, 320, 440, 480):
            self.assertAlmostEqual(48 * (dpi / 160) / (dpi / 160), 48)
        self.assertIn("screen_get_dpi() / 160.0", self.changed[patch.THEME])

    def test_reapplication_rejected_without_partial_write(self):
        with tempfile.TemporaryDirectory(prefix="godot-phone-patch-test-") as folder:
            root = Path(folder)
            (root / "version.py").write_text((self.source / "version.py").read_text())
            for path, content in self.changed.items():
                destination = root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content)
            with self.assertRaises(ValueError):
                patch.prepare(root)
            for path, content in self.changed.items():
                self.assertEqual((root / path).read_text(), content)


if __name__ == "__main__":
    # Remove the source path before unittest interprets command-line arguments.
    source = sys.argv.pop()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MobilePatchTests)
    sys.argv.append(source)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
