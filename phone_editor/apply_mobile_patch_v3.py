"""Apply the pinned Preview 3 patch after validating every source file."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "preview3-manifest.json").read_text())
GODOT_COMMIT = MANIFEST["godot_commit"]
APP_ID = "org.godotengine.editor.v4.phonepreview31"


def validate(root):
    patch = HERE / "preview3.patch"
    if hashlib.sha256(patch.read_bytes()).hexdigest() != MANIFEST["patch_sha256"]:
        raise ValueError("Patch checksum mismatch")
    for path, sums in MANIFEST["files"].items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != sums["before"]:
            raise ValueError("Unexpected or already patched source: " + path)
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=root, check=True)


def apply(root):
    validate(root)
    subprocess.run(["git", "apply", str(HERE / "preview3.patch")], cwd=root, check=True)
    for path, sums in MANIFEST["files"].items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == sums["after"], path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    (validate if args.check else apply)(args.source.resolve())
    print(json.dumps({"preview": "3.1", "status": "VALIDATED" if args.check else "PATCHED",
                      "godot_commit": GODOT_COMMIT, "app_id": APP_ID,
                      "patch_sha256": MANIFEST["patch_sha256"],
                      "files": sorted(MANIFEST["files"])}, indent=2))
