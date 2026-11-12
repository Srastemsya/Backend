@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package ru.srastemsya.uikit

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.dp
import kotlinx.cinterop.useContents
import platform.Foundation.NSProcessInfo

actual interface SrBackdrop
private object IosBackdrop : SrBackdrop

internal fun hasNativeGlass(): Boolean =
    NSProcessInfo.processInfo.operatingSystemVersion.useContents { majorVersion >= 26 }

@Composable
actual fun SrGlassHost(
    background: @Composable BoxScope.() -> Unit,
    modifier: Modifier,
    enabled: Boolean,
    content: @Composable BoxScope.(SrBackdrop) -> Unit
) {
    Box(modifier) {
        Box(Modifier.matchParentSize(), content = background)
        CompositionLocalProvider(LocalSrBackdrop provides IosBackdrop.takeIf { enabled }) {
            content(IosBackdrop)
        }
    }
}

actual fun Modifier.srGlass(backdrop: SrBackdrop?, shape: Shape, mode: SrGlassMode, tint: Color): Modifier {
    val solid = backdrop == null || mode == SrGlassMode.Solid
    return clip(shape)
        .background(if (solid) SrColors.Solid else tint.copy(alpha = maxOf(tint.alpha, .74f)))
        .border(1.dp, if (solid) SrColors.Border else SrColors.GlassEdge, shape)
}
