package ru.srastemsya.uikit

import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import kotlinx.datetime.LocalDate

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal actual fun SrPlatformDatePicker(value: SrDate?, onSelect: (SrDate) -> Unit, onDismiss: () -> Unit) {
    val state = rememberDatePickerState(
        initialSelectedDateMillis = value?.let { LocalDate(it.year, it.month, it.day).toEpochDays() * 86_400_000L },
        yearRange = 1..9999
    )
    DatePickerDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(enabled = state.selectedDateMillis != null, onClick = {
                state.selectedDateMillis?.let {
                    val date = LocalDate.fromEpochDays((it / 86_400_000L).toInt())
                    onSelect(SrDate(date.year, date.month.ordinal + 1, date.day))
                }
                onDismiss()
            }) { Text("Готово") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Отмена") } }
    ) { DatePicker(state) }
}
