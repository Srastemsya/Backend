package ru.srastemsya.uikit

import android.os.Build
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import kotlin.math.cos
import kotlin.math.sin
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.dp
import com.kashif_e.backdrop.Backdrop
import com.kashif_e.backdrop.backdrops.layerBackdrop
import com.kashif_e.backdrop.backdrops.rememberLayerBackdrop
import com.kashif_e.backdrop.drawBackdrop
import com.kashif_e.backdrop.effects.blur
import com.kashif_e.backdrop.effects.lens
import com.kashif_e.backdrop.highlight.Highlight

enum class SrGlassMode { Liquid, Frosted, Solid }

internal val LocalSrBackdrop = staticCompositionLocalOf<Backdrop?> { null }

/** The gradient used behind the surfaces in the Figma assembly examples. */
fun Modifier.srGlassBackground(angleDegrees: Float = 106f): Modifier = drawWithCache {
    val angle = Math.toRadians(angleDegrees.toDouble())
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
fun SrGlassHost(
    background: @Composable BoxScope.() -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    content: @Composable BoxScope.(Backdrop) -> Unit
) {
    val backdrop = rememberLayerBackdrop()
    Box(modifier) {
        Box(
            Modifier.matchParentSize().then(if (enabled && Build.VERSION.SDK_INT >= 31)
                Modifier.layerBackdrop(backdrop) else Modifier),
            content = background
        )
        CompositionLocalProvider(LocalSrBackdrop provides if (enabled) backdrop else null) {
            content(backdrop)
        }
    }
}

fun Modifier.srGlass(
    backdrop: Backdrop?,
    shape: Shape = SrShapes.Panel,
    mode: SrGlassMode = SrGlassMode.Liquid,
    tint: Color = SrColors.Glass
): Modifier {
    val base = shadow(6.dp, shape, clip = false, ambientColor = SrColors.Shadow, spotColor = SrColors.Shadow)
    if (backdrop == null || mode == SrGlassMode.Solid) {
        return base.clip(shape).background(SrColors.Solid).border(1.dp, SrColors.Border, shape)
    }
    if (Build.VERSION.SDK_INT < 31) {
        // The compositor can still show the real background through a translucent surface.
        val fill = if (mode == SrGlassMode.Liquid) tint.copy(alpha = maxOf(tint.alpha, .26f)) else tint
        return base.clip(shape).background(fill).border(1.dp, SrColors.GlassEdge, shape)
    }
    return base.drawBackdrop(
        backdrop = backdrop,
        shape = { shape },
        effects = {
            blur(if (mode == SrGlassMode.Frosted) 12.dp.toPx() else 6.dp.toPx())
            if (mode == SrGlassMode.Liquid && Build.VERSION.SDK_INT >= 33) {
                lens(13.dp.toPx(), 22.dp.toPx())
            }
        },
        highlight = { Highlight.Ambient },
        shadow = { null },
        onDrawSurface = { drawRect(tint) }
    ).clip(shape).border(1.dp, SrColors.GlassEdge, shape)
}

@Composable
fun SrGlassSurface(
    backdrop: Backdrop? = LocalSrBackdrop.current,
    modifier: Modifier = Modifier,
    mode: SrGlassMode = SrGlassMode.Liquid,
    shape: Shape = SrShapes.Panel,
    content: @Composable BoxScope.() -> Unit
) = Box(modifier.srGlass(backdrop, shape, mode), content = content)
