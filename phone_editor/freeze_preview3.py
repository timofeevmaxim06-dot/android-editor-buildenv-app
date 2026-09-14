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
assert not subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=root).strip(), 'Untracked source files need an explicit freeze policy'
names = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=root, text=True).splitlines()
payload = subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=root)
sha = lambda data: hashlib.sha256(data).hexdigest()
manifest['patch_sha256'] = sha(payload)
manifest['files'] = {name: {'before': sha(subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=root)),
                           'after': sha((root / name).read_bytes())} for name in names}
manifest['preview'] = '3.2'
manifest['accepted_recipe_base'] = 'fa8d989724d21cfa3b53012b6c26a9399a1dc5f2'
(here / 'preview3.patch').write_bytes(payload)
(here / 'preview3-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'patch_sha256': sha(payload), 'files': len(names), 'bytes': len(payload)}))
