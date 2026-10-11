"""Verify archive integrity and ARM64 payload; signature is checked by apksigner."""

import hashlib
import json
import os
import re
import subprocess
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
            "signing": "VERIFY_SEPARATE_APKSIGNER_REPORT"}


if __name__ == "__main__":
    path = Path(sys.argv[1]).resolve()
    result = verify(path)
    sdk = Path(os.environ["ANDROID_HOME"])
    build_tools = sdk / "build-tools/36.1.0"
    badging = subprocess.check_output([str(build_tools / "aapt2"), "dump", "badging", str(path)], text=True)
    package = re.search(r"package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']+)'", badging)
    if not package:
        raise ValueError("Cannot read APK package and version")
    expected_code = 40702500 + int(os.environ.get("GODOT_PHONE_BUILD_NUMBER", "3"))
    if package[1] != "org.godotengine.editor.v4.phonepreview31.debug" or int(package[2]) != expected_code or expected_code <= 40702502:
        raise ValueError("APK identity or version breaks the 3.4 update path: " + package[0])
    signature = subprocess.check_output(["java", "-jar", str(build_tools / "lib/apksigner.jar"), "verify", "--verbose", "--print-certs", str(path)], text=True)
    fingerprint = "921564d50b125fc1dfbe2209be475ed2172adf8be7f472532f212819715d3e8c"
    if "certificate SHA-256 digest: " + fingerprint not in signature:
        raise ValueError("Signing certificate does not match installed preview 3.4")
    subprocess.run([str(build_tools / "zipalign"), "-c", "-P", "16", "4", str(path)], check=True, stdout=subprocess.DEVNULL)
    result.update({"application_id":package[1], "version_code":int(package[2]), "version_name":package[3],
                   "signing":"MATCHES_3.4_CERTIFICATE", "certificate_sha256":fingerprint,
                   "previous_version_code":40702502, "update_metadata_compatible":True, "zipalign_16k":True})
    print(json.dumps(result, indent=2))
