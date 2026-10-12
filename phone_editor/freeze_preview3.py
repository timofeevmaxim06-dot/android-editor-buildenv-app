"""Freeze an already reviewed Godot worktree into the pinned patch and file hashes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
here = Path(__file__).resolve().parent
manifest = json.loads((here / 'preview3-manifest.json').read_text())
base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
assert base == manifest['godot_commit']
subprocess.run(['git', 'diff', '--check'], cwd=root, check=True)
untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=root, text=True).splitlines()
fixture = 'platform/android/java/editor/src/test/java/org/godotengine/editor/embed/PhoneGameWindowBoundsTest.kt'
for name in untracked:
    assert name == fixture and (root / name).read_bytes() == (here / 'tests/PhoneGameWindowBoundsTest.kt').read_bytes(), 'Unexpected untracked source: ' + name
names = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=root, text=True).splitlines()
payload = subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=root)
sha = lambda data: hashlib.sha256(data).hexdigest()
manifest['patch_sha256'] = sha(payload)
manifest['files'] = {name: {'before': sha(subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=root)),
                           'after': sha((root / name).read_bytes())} for name in names}
manifest['preview'] = '3.6.0'
manifest['accepted_recipe_base'] = '404f5bb5b0e8cc424f4974a8f49e12d3dc2fa1de'
(here / 'preview3.patch').write_bytes(payload)
(here / 'preview3-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'patch_sha256': sha(payload), 'files': len(names), 'bytes': len(payload)}))
