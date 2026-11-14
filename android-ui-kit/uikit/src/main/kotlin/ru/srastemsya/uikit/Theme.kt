package ru.srastemsya.uikit

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

object SrColors {
    val Primary = Color(0xFF3D48FA)
    val Text = Color(0xFF141425)
    val Muted = Color(0xFF60617B)
    val OnAction = Color.White
    val Base = Color(0xFFF8F8FD)
    val Tint = Color(0xFFECECFF)
    val Solid = Color.White
    val Glass = Color.White.copy(alpha = .13f)
    val GlassCloud = Color(0xFFF6F5FF)
    val GlassIris = Color(0xFFBDC5FF)
    val GlassSea = Color(0xFFC5E8F5)
    val GlassRose = Color(0xFFE7DBFC)
    val GlassEdge = Color.White.copy(alpha = .66f)
    val Border = Color(0xFFDDDFF2)
    val Shadow = Color(0xFF343A67).copy(alpha = .13f)
    val Error = Color(0xFFB9283B)
    val Success = Color(0xFF17694D)
}

object SrShapes {
    val Small = RoundedCornerShape(12.dp)
    val Control = RoundedCornerShape(16.dp)
    val Panel = RoundedCornerShape(20.dp)
    val Card = RoundedCornerShape(24.dp)
    val Nav = RoundedCornerShape(26.dp)
    val Pill = RoundedCornerShape(50)
}

private val Inter = FontFamily(
    Font(R.font.inter_400, FontWeight.Normal),
    Font(R.font.inter_600, FontWeight.SemiBold),
    Font(R.font.inter_700, FontWeight.Bold),
    Font(R.font.inter_800, FontWeight.ExtraBold)
)

private fun type(size: Int, line: Int, weight: FontWeight) =
    TextStyle(fontFamily = Inter, fontSize = size.sp, lineHeight = line.sp, fontWeight = weight)

object SrType {
    val Display = type(30, 36, FontWeight.ExtraBold)
    val Heading = type(20, 26, FontWeight.ExtraBold)
    val Title = type(16, 22, FontWeight.Bold)
    val Body = type(14, 20, FontWeight.Normal)
    val Label = type(13, 18, FontWeight.SemiBold)
    val Caption = type(11, 16, FontWeight.SemiBold)
}

@Composable
fun SrTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = SrColors.Primary, onPrimary = SrColors.OnAction,
            surface = SrColors.Solid, onSurface = SrColors.Text, onSurfaceVariant = SrColors.Muted,
            background = SrColors.Base, onBackground = SrColors.Text, outline = SrColors.Border,
            error = SrColors.Error, secondaryContainer = SrColors.Tint
        ),
        typography = Typography(
            displaySmall = SrType.Display, headlineSmall = SrType.Heading,
            titleMedium = SrType.Title, bodyLarge = SrType.Body, bodyMedium = SrType.Body,
            labelLarge = SrType.Label, labelSmall = SrType.Caption
        ),
        content = content
    )
}
