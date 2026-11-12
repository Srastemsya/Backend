package ru.srastemsya.uikit

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.runtime.Composable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import kotlin.math.cos
import kotlin.math.sin
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.dp

expect interface SrBackdrop

enum class SrGlassMode { Liquid, Frosted, Solid }

internal val LocalSrBackdrop = staticCompositionLocalOf<SrBackdrop?> { null }

/** The gradient used behind the surfaces in the Figma assembly examples. */
fun Modifier.srGlassBackground(angleDegrees: Float = 106f): Modifier = drawWithCache {
    val angle = angleDegrees.toDouble() * kotlin.math.PI / 180.0
    val direction = Offset(sin(angle).toFloat(), -cos(angle).toFloat())
    val extent = (kotlin.math.abs(size.width * direction.x) +
        kotlin.math.abs(size.height * direction.y)) / 2f
    val middle = Offset(size.width / 2f, size.height / 2f)
    val brush = Brush.linearGradient(
        0f to SrColors.GlassCloud, .35294f to SrColors.GlassIris,
        .68627f to SrColors.GlassSea, .98039f to SrColors.GlassRose,
        start = middle - direction * extent, end = middle + direction * extent
    )
    onDrawBehind { drawRect(brush) }
}

@Composable
expect fun SrGlassHost(
    background: @Composable BoxScope.() -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    content: @Composable BoxScope.(SrBackdrop) -> Unit
)

expect fun Modifier.srGlass(
    backdrop: SrBackdrop?,
    shape: Shape = SrShapes.Panel,
    mode: SrGlassMode = SrGlassMode.Liquid,
    tint: Color = SrColors.Glass
): Modifier

@Composable
fun SrGlassSurface(
    backdrop: SrBackdrop? = LocalSrBackdrop.current,
    modifier: Modifier = Modifier,
    mode: SrGlassMode = SrGlassMode.Liquid,
    shape: Shape = SrShapes.Panel,
    content: @Composable BoxScope.() -> Unit
) = Box(modifier.srGlass(backdrop, shape, mode), content = content)
