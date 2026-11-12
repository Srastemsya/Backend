package ru.srastemsya.uikit

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.error
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp

enum class SrFieldKind { Text, Number, Phone, Search, Multiline }

@Composable
private fun FieldFrame(
    label: String, errorMessage: String?, modifier: Modifier, content: @Composable () -> Unit
) {
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        if (label.isNotEmpty()) Text(label, style = SrType.Label, color = if (errorMessage == null) SrColors.Text else SrColors.Error)
        content()
        if (errorMessage != null) Text(errorMessage, style = SrType.Caption, color = SrColors.Error)
    }
}

private fun Modifier.fieldSurface(backdrop: SrBackdrop?, enabled: Boolean, focused: Boolean, invalid: Boolean): Modifier {
    val edge = when {
        invalid -> SrColors.Error
        focused -> SrColors.Primary
        else -> SrColors.Border
    }
    return (if (enabled) srGlass(backdrop, SrShapes.Control, SrGlassMode.Frosted, SrColors.Solid.copy(alpha = .78f))
            else clip(SrShapes.Control).background(SrColors.Tint))
        .border(if (focused || invalid) 1.5.dp else 1.dp, edge, SrShapes.Control)
}

@Composable
fun SrField(
    value: String, onValueChange: (String) -> Unit, label: String,
    modifier: Modifier = Modifier, placeholder: String = "", kind: SrFieldKind = SrFieldKind.Text,
    enabled: Boolean = true, errorMessage: String? = null, backdrop: SrBackdrop? = LocalSrBackdrop.current,
    leading: SrIcon? = if (kind == SrFieldKind.Search) SrIcon.Search else null
) {
    var focused by remember { mutableStateOf(false) }
    val multi = kind == SrFieldKind.Multiline
    FieldFrame(label, errorMessage, modifier) {
        BasicTextField(
            value = value, onValueChange = onValueChange, enabled = enabled, singleLine = !multi,
            minLines = if (multi) 3 else 1, maxLines = if (multi) 8 else 1,
            textStyle = SrType.Body.copy(color = if (enabled) SrColors.Text else SrColors.Muted),
            cursorBrush = SolidColor(SrColors.Primary),
            keyboardOptions = KeyboardOptions(keyboardType = when (kind) {
                SrFieldKind.Number -> KeyboardType.Number
                SrFieldKind.Phone -> KeyboardType.Phone
                else -> KeyboardType.Text
            }),
            modifier = Modifier.fillMaxWidth().onFocusChanged { focused = it.isFocused }
                .semantics {
                    if (label.isNotEmpty()) contentDescription = label
                    errorMessage?.let { error(it) }
                },
            decorationBox = { editor ->
                Row(
                    Modifier.fillMaxWidth().heightIn(min = if (multi) 104.dp else 49.dp)
                        .fieldSurface(backdrop, enabled, focused, errorMessage != null)
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = if (multi) Alignment.Top else Alignment.CenterVertically
                ) {
                    if (leading != null) SrGlyph(leading)
                    Box(Modifier.weight(1f)) {
                        if (value.isEmpty()) Text(placeholder, style = SrType.Body, color = SrColors.Muted)
                        editor()
                    }
                }
            }
        )
    }
}

@Composable
private fun FieldTrigger(
    value: String?, label: String, placeholder: String, icon: SrIcon,
    backdrop: SrBackdrop?, enabled: Boolean, focused: Boolean, errorMessage: String?, onClick: () -> Unit
) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 49.dp).fieldSurface(backdrop, enabled, focused, errorMessage != null)
            .clickable(enabled, role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; errorMessage?.let { error(it) } }
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(value ?: placeholder, Modifier.weight(1f), style = SrType.Body,
            color = if (value == null || !enabled) SrColors.Muted else SrColors.Text)
        SrGlyph(icon, size = 16.dp)
    }
}

@Composable
fun SrSelect(
    value: String?, options: List<String>, onSelect: (String) -> Unit, label: String,
    modifier: Modifier = Modifier, placeholder: String = "Выберите вариант", enabled: Boolean = true,
    errorMessage: String? = null, backdrop: SrBackdrop? = LocalSrBackdrop.current
) {
    var expanded by rememberSaveable { mutableStateOf(false) }
    FieldFrame(label, errorMessage, modifier) {
        Box {
            FieldTrigger(value, label, placeholder, SrIcon.Expand, backdrop, enabled, enabled && expanded, errorMessage) { expanded = true }
            DropdownMenu(expanded && enabled, { expanded = false }, shape = SrShapes.Control,
                containerColor = SrColors.Solid) {
                if (options.isEmpty()) {
                    DropdownMenuItem(text = { Text("Нет вариантов", style = SrType.Body) }, onClick = {}, enabled = false)
                }
                options.forEach { option ->
                    DropdownMenuItem(text = { Text(option, style = SrType.Body) }, onClick = {
                        expanded = false
                        onSelect(option)
                    }, trailingIcon = if (option == value) ({ SrGlyph(SrIcon.Check, tint = SrColors.Primary) }) else null)
                }
            }
        }
    }
}

@Composable
fun SrComboBox(
    query: String, onQueryChange: (String) -> Unit, suggestions: List<String>, onSelect: (String) -> Unit,
    label: String, modifier: Modifier = Modifier, placeholder: String = "Начните вводить",
    enabled: Boolean = true, errorMessage: String? = null, backdrop: SrBackdrop? = LocalSrBackdrop.current
) {
    var expanded by rememberSaveable { mutableStateOf(false) }
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        SrField(query, { onQueryChange(it); expanded = true }, label, placeholder = placeholder,
            enabled = enabled, errorMessage = errorMessage, backdrop = backdrop)
        if (expanded && enabled && query.isNotBlank()) {
            Column(Modifier.fillMaxWidth().clip(SrShapes.Control).background(SrColors.Solid)
                .border(1.dp, SrColors.Border, SrShapes.Control)) {
                if (suggestions.isEmpty()) {
                    Text("Нет результатов", Modifier.padding(12.dp), style = SrType.Body, color = SrColors.Muted)
                }
                suggestions.take(5).forEach { option ->
                    SrListRow(option, onClick = { expanded = false; onSelect(option) })
                }
            }
        }
    }
}

data class SrDate(val year: Int, val month: Int, val day: Int) {
    init {
        require(year in 1..9999 && month in 1..12)
        val days = when (month) {
            2 -> if (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)) 29 else 28
            4, 6, 9, 11 -> 30
            else -> 31
        }
        require(day in 1..days)
    }
    fun formatted(): String = listOf(day.toString().padStart(2, '0'), month.toString().padStart(2, '0'),
        year.toString().padStart(4, '0')).joinToString(".")
}

@Composable
fun SrDateField(
    value: SrDate?, onSelect: (SrDate) -> Unit, label: String,
    modifier: Modifier = Modifier, enabled: Boolean = true,
    errorMessage: String? = null, backdrop: SrBackdrop? = LocalSrBackdrop.current
) {
    var open by rememberSaveable { mutableStateOf(false) }
    if (open && enabled) {
        SrPlatformDatePicker(value, onSelect, onDismiss = { open = false })
    }
    FieldFrame(label, errorMessage, modifier) {
        FieldTrigger(value?.formatted(), label, "ДД.ММ.ГГГГ", SrIcon.Events, backdrop, enabled, open && enabled, errorMessage) { open = true }
    }
}

@Composable
internal expect fun SrPlatformDatePicker(value: SrDate?, onSelect: (SrDate) -> Unit, onDismiss: () -> Unit)
