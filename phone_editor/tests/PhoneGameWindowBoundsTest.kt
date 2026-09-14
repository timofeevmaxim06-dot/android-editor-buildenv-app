package org.godotengine.editor.embed

import org.junit.Assert.*
import org.junit.Test

class PhoneGameWindowBoundsTest {
    @Test fun restoredLandscapeWindowFitsPortraitAndKeepsAspect() {
        val b = fitPhoneGameWindow(-700, 1500, 1920, 1080, 864, 1920, true)
        assertTrue(b.x >= 0 && b.y >= 0)
        assertTrue(b.x + b.width <= 864 && b.y + b.height <= 1920)
        assertEquals(1920.0 / 1080, b.width.toDouble() / b.height, 0.01)
    }

    @Test fun dragAndResizeCannotHideWindowControls() {
        for (sw in listOf(1, 320, 691, 864, 1920)) {
            for (sh in listOf(1, 240, 691, 1536, 1920)) {
                for (aspect in listOf(true, false)) {
                    for (offset in listOf(-10000, 0, 10000)) {
                        val b = fitPhoneGameWindow(offset, offset, 1920, 1080, sw, sh, aspect)
                        assertTrue(b.width > 0 && b.height > 0)
                        assertTrue(b.x >= 0 && b.y >= 0)
                        assertTrue(b.x + b.width <= sw && b.y + b.height <= sh)
                        val again = fitPhoneGameWindow(b.x, b.y, b.width, b.height, sw, sh, aspect)
                        assertEquals("Repeated clamp must not shrink or distort the window", b, again)
                    }
                }
            }
        }
    }

    @Test fun rotationAndFullscreenReturnRefitWithoutNegativeBounds() {
        val a = fitPhoneGameWindow(1400, 400, 1280, 720, 1920, 864, true)
        val b = fitPhoneGameWindow(a.x, a.y, a.width, a.height, 864, 1920, true)
        val c = fitPhoneGameWindow(b.x, b.y, b.width, b.height, 1920, 864, true)
        assertTrue(b.x + b.width <= 864)
        assertTrue(c.y + c.height <= 864)
        val invalid = fitPhoneGameWindow(-99, -99, -1, 0, 320, 240, false)
        assertTrue(invalid.width in 1..320 && invalid.height in 1..240)
        assertEquals(0, invalid.x)
        assertEquals(0, invalid.y)
    }
}
