"""Verify archive integrity and ARM64 payload; signature is checked by apksigner."""

import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile


def verify(path):
    with ZipFile(path) as apk:
        if apk.testzip() is not None:
            raise ValueError("Corrupt APK ZIP entry")
        names = apk.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate APK ZIP entries")
        if "AndroidManifest.xml" not in names or "classes.dex" not in names:
            raise ValueError("Missing Android application payload")
        libraries = [name for name in names if name.startswith("lib/") and name.endswith(".so")]
        if not libraries or not all(name.startswith("lib/arm64-v8a/") for name in libraries):
            raise ValueError("Expected ARM64-only native libraries")
        godot_libraries = [name for name in libraries if "godot_android" in name]
        if len(godot_libraries) != 1:
            raise ValueError("Expected exactly one Godot native library")
        with apk.open(godot_libraries[0]) as library:
            header = library.read(20)
        if header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != 183:
            raise ValueError("Native payload is not little-endian ELF64 AArch64")
    with path.open("rb") as apk_file:
        digest = hashlib.file_digest(apk_file, "sha256").hexdigest()
    return {"apk": path.name, "bytes": path.stat().st_size, "sha256": digest,
            "libraries": libraries, "device_test": "NOT_TESTED_ON_DEVICE",
            "signing": "EPHEMERAL_DEBUG_KEY_NO_UPDATE_CONTINUITY_GUARANTEE"}


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1])), indent=2))
