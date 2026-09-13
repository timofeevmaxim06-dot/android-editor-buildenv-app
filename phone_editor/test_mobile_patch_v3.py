"""Verify the frozen source contract; runtime input is exercised by layout_probe_v3."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import apply_mobile_patch_v3 as patch

SOURCE = Path(sys.argv.pop()).resolve()


class Preview3Tests(unittest.TestCase):
    def test_apply_is_atomic_and_repeat_is_rejected(self):
        patch.validate(SOURCE)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in patch.MANIFEST["files"]:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(SOURCE / name, root / name)
            patch.apply(root)
            with self.assertRaises(ValueError):
                patch.apply(root)
            self.assertIn('applicationId "' + patch.APP_ID + '"', (root / 'platform/android/java/editor/build.gradle').read_text())
            self.assertNotIn('MobileDockPlugin', (root / 'editor/editor_node.cpp').read_text())

    def test_source_change_rejected_before_any_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in patch.MANIFEST["files"]:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(SOURCE / name, root / name)
            target = root / 'scene/gui/text_edit.cpp'
            target.write_bytes(target.read_bytes() + b'\n// concurrent change\n')
            before = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in patch.MANIFEST["files"]}
            with self.assertRaises(ValueError):
                patch.apply(root)
            after = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in patch.MANIFEST["files"]}
            self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
