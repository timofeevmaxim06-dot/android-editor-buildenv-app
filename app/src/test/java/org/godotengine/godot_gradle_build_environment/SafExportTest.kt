package org.godotengine.godot_gradle_build_environment

import org.junit.Assert.*
import org.junit.Test

class SafExportTest {
    private fun args(path: String = "/tmp/demo/builds", name: String = "test.aab") =
        listOf("copyAndRenameBinary", "-Pexport_path=$path", "-Pexport_filename=$name")

    @Test fun normalExportIsStaged() {
        val input = args()
        val plan = SafExport.plan(input, "/tmp/demo")!!
        assertEquals(listOf("builds"), plan.directories)
        assertEquals("test.aab", plan.filename)
        val rewritten = SafExport.arguments(input, plan)
        assertTrue(rewritten.contains("-Pexport_path=/project/${plan.staging}"))
        assertFalse(rewritten.contains("-Pexport_path=/tmp/demo/builds"))
    }
    @Test fun buildWithoutCopyIsUntouched() {
        assertNull(SafExport.plan(listOf("bundleStandardRelease"), "/tmp/demo"))
    }
    @Test fun godotFilePrefixPreservesLiteralPath() {
        val root = "/tmp/demo space%20"
        val plan = SafExport.plan(args("file:$root/builds"), root)!!
        assertEquals(listOf("builds"), plan.directories)
    }
    @Test(expected = IllegalArgumentException::class) fun prefixedTraversalIsRejected() {
        SafExport.plan(args("file:/tmp/demo/../other"), "/tmp/demo")
    }
    @Test(expected = IllegalArgumentException::class) fun siblingIsRejected() {
        SafExport.plan(args("/tmp/demo-other"), "/tmp/demo")
    }
    @Test(expected = IllegalArgumentException::class) fun traversalIsRejected() {
        SafExport.plan(args("/tmp/demo/../other"), "/tmp/demo")
    }
    @Test(expected = IllegalArgumentException::class) fun filenameTraversalIsRejected() {
        SafExport.plan(args(name = "../test.aab"), "/tmp/demo")
    }
    @Test fun stagingNeverReusesOldOutput() {
        assertNotEquals(SafExport.plan(args(), "/tmp/demo")!!.staging,
            SafExport.plan(args(), "/tmp/demo")!!.staging)
    }
}
