package ru.srastemsya.uikit

import androidx.compose.foundation.Image
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import org.jetbrains.compose.resources.Font
import org.jetbrains.compose.resources.painterResource
import ru.srastemsya.uikit.resources.*

@Composable
internal actual fun srInter() = FontFamily(
    Font(Res.font.inter_400, FontWeight.Normal),
    Font(Res.font.inter_600, FontWeight.SemiBold),
    Font(Res.font.inter_700, FontWeight.Bold),
    Font(Res.font.inter_800, FontWeight.ExtraBold)
)

@Composable
internal actual fun FigmaSvg(
    file: String, modifier: Modifier, description: String?, tint: Color?, scale: ContentScale
) {
    val asset = when (file) {
        "f8380_img" -> Res.drawable.f8380_img
        "f8380_imgcalendar" -> Res.drawable.f8380_imgcalendar
        "f8380_imghome" -> Res.drawable.f8380_imghome
        "f8380_imgpin" -> Res.drawable.f8380_imgpin
        "f8380_imguser" -> Res.drawable.f8380_imguser
        "f8420_img" -> Res.drawable.f8420_img
        "f8487_imgfilter" -> Res.drawable.f8487_imgfilter
        "f8490_imgtarget" -> Res.drawable.f8490_imgtarget
        "f8493_imgplus" -> Res.drawable.f8493_imgplus
        "f8496_imgminus" -> Res.drawable.f8496_imgminus
        "f8499_imgback" -> Res.drawable.f8499_imgback
        "f8502_imgclose" -> Res.drawable.f8502_imgclose
        "f8505_imgbookmark" -> Res.drawable.f8505_imgbookmark
        "f8508_imgshare" -> Res.drawable.f8508_imgshare
        "f8585_imgchevrondown" -> Res.drawable.f8585_imgchevrondown
        "f9078_img1" -> Res.drawable.f9078_img1
        "f9096_imgbell" -> Res.drawable.f9096_imgbell
        "f9096_imgdots" -> Res.drawable.f9096_imgdots
        "f9140_imgnext" -> Res.drawable.f9140_imgnext
        "f9159_img" -> Res.drawable.f9159_img
        "f9159_img1" -> Res.drawable.f9159_img1
        "f9194_imgalert" -> Res.drawable.f9194_imgalert
        "f9194_imgclock" -> Res.drawable.f9194_imgclock
        "f9194_imgsearch" -> Res.drawable.f9194_imgsearch
        "f9244_imgcheck" -> Res.drawable.f9244_imgcheck
        "f9244_imgplus" -> Res.drawable.f9244_imgplus
        "f9255_imgusers" -> Res.drawable.f9255_imgusers
        "f9290_img" -> Res.drawable.f9290_img
        "f9290_img1" -> Res.drawable.f9290_img1
        "f9290_img2" -> Res.drawable.f9290_img2
        "f9444_imgheart" -> Res.drawable.f9444_imgheart
        "f9444_imgundo" -> Res.drawable.f9444_imgundo
        "f9445_imgspark" -> Res.drawable.f9445_imgspark
        "f9466_img" -> Res.drawable.f9466_img
        "f9466_img1" -> Res.drawable.f9466_img1
        "f9466_imgphoto" -> Res.drawable.f9466_imgphoto
        "f9570_imglink" -> Res.drawable.f9570_imglink
        "f9607_imgstar" -> Res.drawable.f9607_imgstar
        "f9607_imgstar1" -> Res.drawable.f9607_imgstar1
        "f9846_img" -> Res.drawable.f9846_img
        else -> error("Unknown UI Kit asset: $file")
    }
    Image(painterResource(asset), description, modifier, contentScale = scale,
        colorFilter = tint?.let { ColorFilter.tint(it) })
}
