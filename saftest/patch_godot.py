"""Mechanical, fail-closed patch of the pinned Godot 4.7.2 editor sources."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
editor = root / "platform/android/java/editor"
old_provider = "org.godotengine.godot_gradle_build_environment"
for relative in (
    "src/main/AndroidManifest.xml",
    "src/main/java/org/godotengine/editor/buildprovider/GradleBuildEnvironmentClient.kt",
):
    path = editor / relative
    text = path.read_text()
    assert text.count(old_provider) == 1, f"Unexpected provider declaration: {path}"
    path.write_text(text.replace(old_provider, old_provider + ".saftest"))

path = editor / "build.gradle"
text = path.read_text()
for old, new in (
    ('applicationId "org.godotengine.editor.v4"',
     'applicationId "org.godotengine.editor.v4.saftest"'),
    ('editorAppName: "Godot Engine 4"', 'editorAppName: "Godot SAF Test"'),
):
    assert text.count(old) == 1, f"Unexpected editor configuration: {old}"
    text = text.replace(old, new)
path.write_text(text)
