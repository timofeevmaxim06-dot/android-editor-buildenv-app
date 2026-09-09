package org.godotengine.godot_gradle_build_environment

import android.content.Context
import androidx.documentfile.provider.DocumentFile
import java.io.File
import java.security.MessageDigest
import java.util.UUID

/** Test-only export bridge. Never writes directly into shared storage from proot. */
internal object SafExport {
    data class Plan(val directories: List<String>, val filename: String, val staging: String)

    fun plan(args: List<String>, projectPath: String): Plan? {
        if (args.none { it == "copyAndRenameBinary" || it == ":copyAndRenameBinary" }) return null
        fun property(name: String): String = args.lastOrNull { it.startsWith("-P$name=") }
            ?.substringAfter('=') ?: error("Missing export property: $name")
        val root = File(projectPath).canonicalFile
        val destination = File(property("export_path")).canonicalFile
        require(destination == root || destination.path.startsWith(root.path + File.separator)) {
            "Test export must stay inside the granted project folder"
        }
        val filename = property("export_filename")
        require(filename.isNotBlank() && filename != "." && filename != ".." &&
            filename.none { it == '/' || it == '\\' || it.code < 32 }) { "Invalid export filename" }
        require(filename.endsWith(".aab") || filename.endsWith(".apk")) { "Only APK/AAB export is supported" }
        val relative = destination.relativeTo(root).path
        return Plan(relative.split(File.separatorChar).filter { it.isNotEmpty() }, filename,
            ".gabe-export-${UUID.randomUUID()}")
    }

    fun arguments(args: List<String>, plan: Plan): List<String> =
        args.filterNot { it.startsWith("-Pexport_path=") } + "-Pexport_path=/project/${plan.staging}"

    fun publish(context: Context, projectPath: String, workDir: File, plan: Plan) {
        val source = File(File(workDir, plan.staging), plan.filename)
        require(source.isFile && source.length() > 0) { "Staged artifact is missing or empty" }
        val uri = FileUtils.getProjectTreeUri(context, projectPath)
            ?: error("Project folder access is missing")
        var directory = DocumentFile.fromTreeUri(context, uri) ?: error("Invalid project folder")
        for (part in plan.directories) {
            directory = directory.findFile(part) ?: directory.createDirectory(part)
                ?: error("Cannot create export directory")
            require(directory.isDirectory) { "Export path is not a directory" }
        }
        // Do not overwrite an existing artifact during this diagnostic test.
        require(directory.findFile(plan.filename) == null) {
            "Export file already exists. Choose a new filename; existing file was not changed"
        }
        val target = directory.createFile("application/octet-stream", plan.filename)
            ?: error("Cannot create export file through Android folder access")
        try {
            require(target.name == plan.filename) { "Storage provider changed export filename" }
            val digest = MessageDigest.getInstance("SHA-256")
            val output = context.contentResolver.openOutputStream(target.uri, "w")
                ?: error("Cannot open export output")
            output.use { out -> source.inputStream().use { input ->
                val buffer = ByteArray(65536)
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    digest.update(buffer, 0, count)
                    out.write(buffer, 0, count)
                }
            } }
            val expected = digest.digest()
            val actual = MessageDigest.getInstance("SHA-256")
            var size = 0L
            val input = context.contentResolver.openInputStream(target.uri)
                ?: error("Cannot verify export")
            input.use {
                val buffer = ByteArray(65536)
                while (true) {
                    val count = it.read(buffer)
                    if (count < 0) break
                    size += count
                    actual.update(buffer, 0, count)
                }
            }
            require(size == source.length() && expected.contentEquals(actual.digest())) {
                "Export verification failed; staged artifact retained"
            }
        } catch (e: Exception) {
            // Only remove the new file created by this invocation, never an existing artifact.
            val removed = runCatching { target.delete() }.getOrDefault(false)
            throw IllegalStateException("${e.message}; partial export removed=$removed; staged artifact retained", e)
        }
        source.delete()
        source.parentFile?.delete()
    }
}
