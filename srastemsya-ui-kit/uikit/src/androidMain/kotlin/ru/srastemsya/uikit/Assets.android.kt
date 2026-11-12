package ru.srastemsya.uikit

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.RectF
import androidx.compose.foundation.Image
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import com.caverock.androidsvg.SVG
import kotlin.math.roundToInt

@Composable
internal actual fun FigmaSvg(
    file: String,
    modifier: Modifier,
    description: String?,
    tint: Color?,
    scale: ContentScale
) {
    val context = LocalContext.current
    val density = LocalDensity.current.density
    val bitmap = remember(context.assets, file, density) {
        val svg = context.assets.open("figma/$file.svg").use { SVG.getFromInputStream(it) }
        val naturalWidth = svg.documentWidth.coerceAtLeast(1f)
        val naturalHeight = svg.documentHeight.coerceAtLeast(1f)
        val width = (naturalWidth * density).roundToInt().coerceIn(1, 2400)
        val height = (naturalHeight * density).roundToInt().coerceIn(1, 2400)
        Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888).also {
            val canvas = Canvas(it)
            canvas.scale(width / naturalWidth, height / naturalHeight)
            svg.renderToCanvas(canvas, RectF(0f, 0f, naturalWidth, naturalHeight))
        }.asImageBitmap()
    }
    Image(bitmap, description, modifier, contentScale = scale, colorFilter = tint?.let { ColorFilter.tint(it) })
}

@Composable
internal actual fun srInter() = androidx.compose.ui.text.font.FontFamily(
    androidx.compose.ui.text.font.Font(R.font.inter_400, androidx.compose.ui.text.font.FontWeight.Normal),
    androidx.compose.ui.text.font.Font(R.font.inter_600, androidx.compose.ui.text.font.FontWeight.SemiBold),
    androidx.compose.ui.text.font.Font(R.font.inter_700, androidx.compose.ui.text.font.FontWeight.Bold),
    androidx.compose.ui.text.font.Font(R.font.inter_800, androidx.compose.ui.text.font.FontWeight.ExtraBold)
)
