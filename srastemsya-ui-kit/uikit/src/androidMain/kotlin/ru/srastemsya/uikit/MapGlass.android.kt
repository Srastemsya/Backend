package ru.srastemsya.uikit

import android.os.Build
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.unit.IntSize
import com.kashif_e.backdrop.backdrops.layerBackdrop
import com.kashif_e.backdrop.backdrops.rememberLayerBackdrop
import kotlin.math.roundToInt

/**
 * The live renderer stays interactive. A camera-aligned snapshot is recorded only into the
 * glass layer. Pass null while the camera is moving or the viewport is changing.
 */
@Composable
fun SrAndroidNativeMapGlassHost(
    snapshot: ImageBitmap?,
    map: @Composable BoxScope.() -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    controls: @Composable BoxScope.() -> Unit
) {
    val backdrop = rememberLayerBackdrop {
        snapshot?.let {
            val width = size.width.roundToInt()
            val height = size.height.roundToInt()
            if (width > 0 && height > 0) drawImage(it, dstSize = IntSize(width, height))
        }
    }
    val canSample = enabled && snapshot != null && Build.VERSION.SDK_INT >= 31
    Box(modifier) {
        Box(Modifier.matchParentSize(), content = map)
        if (canSample) Box(Modifier.matchParentSize().layerBackdrop(backdrop))
        CompositionLocalProvider(LocalSrBackdrop provides backdrop.takeIf { canSample }) {
            controls()
        }
    }
}
