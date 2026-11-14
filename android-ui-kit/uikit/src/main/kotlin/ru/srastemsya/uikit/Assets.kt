package ru.srastemsya.uikit

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.RectF
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.caverock.androidsvg.SVG
import kotlin.math.roundToInt

enum class SrIcon(internal val file: String, internal val naturalSize: Int) {
    Home("f8380_imghome", 22), Map("f8380_imgpin", 22), Feed("f8380_img", 22),
    Events("f8380_imgcalendar", 22), Profile("f8380_imguser", 22),
    Filter("f8487_imgfilter", 21), Location("f8490_imgtarget", 21),
    ZoomIn("f8493_imgplus", 21), ZoomOut("f8496_imgminus", 21),
    Back("f8499_imgback", 21), Close("f8502_imgclose", 21), Save("f8505_imgbookmark", 21),
    Share("f8508_imgshare", 21), More("f9096_imgdots", 20), Bell("f9096_imgbell", 20),
    Next("f9140_imgnext", 16), Expand("f8585_imgchevrondown", 20), Search("f9194_imgsearch", 24),
    Clock("f9194_imgclock", 24), Warning("f9194_imgalert", 24), Check("f9244_imgcheck", 18),
    Plus("f9244_imgplus", 18), People("f9255_imgusers", 24), Link("f9570_imglink", 24),
    Spark("f9445_imgspark", 24), Undo("f9444_imgundo", 24), Heart("f9444_imgheart", 24),
    Photo("f9466_imgphoto", 24), Star("f9607_imgstar", 20), StarOutline("f9607_imgstar1", 20)
}

@Composable
fun SrGlyph(
    icon: SrIcon,
    modifier: Modifier = Modifier,
    description: String? = null,
    tint: Color = SrColors.Muted,
    size: Dp = icon.naturalSize.dp
) = FigmaSvg(icon.file, modifier.size(size), description, tint)

enum class SrIllustration(internal val file: String) {
    Indoor("f9466_img"), Outdoor("f9466_img1"), GlassDemo("f9078_img1"),
    VoteCompact("f9290_img"), VoteTall("f9290_img1"), VoteFull("f9290_img2"),
    EventThumbnail("f9846_img")
}

@Composable
fun SrArtwork(artwork: SrIllustration, modifier: Modifier = Modifier, description: String? = null) =
    FigmaSvg(artwork.file, modifier, description, scale = ContentScale.Crop)

@Composable
internal fun FigmaSvg(
    file: String,
    modifier: Modifier,
    description: String? = null,
    tint: Color? = null,
    scale: ContentScale = ContentScale.Fit
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
