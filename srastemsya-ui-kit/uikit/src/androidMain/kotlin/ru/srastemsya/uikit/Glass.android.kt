package ru.srastemsya.uikit

import android.os.Build
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
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

actual typealias SrBackdrop = Backdrop

@Composable
actual fun SrGlassHost(
    background: @Composable BoxScope.() -> Unit,
    modifier: Modifier,
    enabled: Boolean,
    content: @Composable BoxScope.(SrBackdrop) -> Unit
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

actual fun Modifier.srGlass(
    backdrop: SrBackdrop?,
    shape: Shape,
    mode: SrGlassMode,
    tint: Color
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
internal actual fun SrNativeTabBar(selected: SrTab, onSelect: (SrTab) -> Unit, modifier: Modifier): Boolean = false

@Composable
fun SrCatalog() {
    SrTheme {
        Catalog(when {
            Build.VERSION.SDK_INT >= 33 -> "Преломление и размытие"
            Build.VERSION.SDK_INT >= 31 -> "Размытие фона"
            else -> "Полупрозрачность"
        })
    }
}
