package ru.srastemsya.uikit

import android.app.DatePickerDialog
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import java.util.Calendar

@Composable
internal actual fun SrPlatformDatePicker(value: SrDate?, onSelect: (SrDate) -> Unit, onDismiss: () -> Unit) {
    val onDismissLatest by rememberUpdatedState(onDismiss)
    val context = LocalContext.current
    val onSelectLatest by rememberUpdatedState(onSelect)
    DisposableEffect(context) {
        val today = Calendar.getInstance()
        val initial = value ?: SrDate(today.get(Calendar.YEAR), today.get(Calendar.MONTH) + 1, today.get(Calendar.DAY_OF_MONTH))
        val dialog = DatePickerDialog(context, { _, y, m, d ->
            onSelectLatest(SrDate(y, m + 1, d))
        }, initial.year, initial.month - 1, initial.day)
        dialog.setOnDismissListener { onDismissLatest() }
        dialog.show()
        onDispose { dialog.setOnDismissListener(null); dialog.dismiss() }
    }
}
