package ru.srastemsya.uikit

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.kashif_e.backdrop.Backdrop

enum class SrButtonStyle { Primary, Secondary, Destructive }

@Composable
fun SrButton(
    text: String, onClick: () -> Unit, modifier: Modifier = Modifier,
    style: SrButtonStyle = SrButtonStyle.Primary, enabled: Boolean = true, loading: Boolean = false
) {
    val active = enabled && !loading
    val fill = when {
        !active -> SrColors.Tint
        style == SrButtonStyle.Primary -> SrColors.Primary
        else -> SrColors.Solid
    }
    val fg = when {
        !active -> SrColors.Muted
        style == SrButtonStyle.Primary -> SrColors.OnAction
        style == SrButtonStyle.Destructive -> SrColors.Error
        else -> SrColors.Text
    }
    val edge = when {
        active && style == SrButtonStyle.Primary -> fill
        active && style == SrButtonStyle.Destructive -> SrColors.Error
        else -> SrColors.Border
    }
    Row(
        modifier.heightIn(min = 48.dp).clip(SrShapes.Control).background(fill)
            .border(1.dp, edge, SrShapes.Control).clickable(active, role = Role.Button, onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally),
        verticalAlignment = Alignment.CenterVertically
    ) {
        if (loading) CircularProgressIndicator(Modifier.size(16.dp), color = fg, strokeWidth = 2.dp)
        Text(text, style = SrType.Label, color = fg)
    }
}

@Composable
fun SrIconButton(
    icon: SrIcon, description: String, onClick: () -> Unit, modifier: Modifier = Modifier,
    backdrop: Backdrop? = LocalSrBackdrop.current, enabled: Boolean = true, primary: Boolean = false
) {
    Box(
        modifier.size(48.dp).clickable(enabled, role = Role.Button, onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        val surface = if (primary) Modifier.clip(SrShapes.Control).background(SrColors.Primary)
        else Modifier.srGlass(backdrop, SrShapes.Control)
        Box(Modifier.size(42.dp).then(surface), contentAlignment = Alignment.Center) {
            SrGlyph(icon, description = description, tint = when {
                primary && enabled -> SrColors.OnAction
                enabled -> SrColors.Muted
                else -> SrColors.Muted.copy(alpha = .50f)
            })
        }
    }
}

enum class SrTab(val title: String, val icon: SrIcon) {
    Home("Главная", SrIcon.Home), Map("Карта", SrIcon.Map), Feed("Лента", SrIcon.Feed),
    Events("События", SrIcon.Events), Profile("Профиль", SrIcon.Profile)
}

@Composable
fun SrTabBar(
    selected: SrTab, onSelect: (SrTab) -> Unit, modifier: Modifier = Modifier,
    backdrop: Backdrop? = LocalSrBackdrop.current, mode: SrGlassMode = SrGlassMode.Liquid
) {
    Row(
        modifier.widthIn(max = 358.dp).fillMaxWidth().heightIn(min = 72.dp)
            .srGlass(backdrop, SrShapes.Nav, mode).padding(horizontal = 8.dp, vertical = 8.dp)
            .selectableGroup(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        SrTab.entries.forEach { tab ->
            val active = tab == selected
            val fg = if (active) SrColors.Primary else SrColors.Muted
            Column(
                Modifier.weight(1f).heightIn(min = 48.dp).clip(SrShapes.Control)
                    .then(if (active) Modifier.background(SrColors.Tint) else Modifier)
                    .selectable(active, role = Role.Tab, onClick = { onSelect(tab) })
                    .padding(vertical = 3.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(3.dp, Alignment.CenterVertically)
            ) {
                val variant = if (tab == SrTab.Feed && active) "f8420_img" else tab.icon.file
                FigmaSvg(variant, Modifier.size(22.dp), tint = fg)
                Text(tab.title, style = SrType.Caption, color = fg, maxLines = 2, overflow = TextOverflow.Ellipsis)
            }
        }
    }
}

@Composable
fun SrTopBar(
    title: String, modifier: Modifier = Modifier, backdrop: Backdrop? = LocalSrBackdrop.current,
    onBack: (() -> Unit)? = null, actions: @Composable RowScope.() -> Unit = {}
) {
    Row(
        modifier.fillMaxWidth().heightIn(min = 52.dp).srGlass(backdrop, SrShapes.Control)
            .padding(horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        if (onBack != null) SrIconButton(SrIcon.Back, "Назад", onBack)
        Text(title, Modifier.weight(1f).padding(horizontal = 8.dp), style = SrType.Title, color = SrColors.Text)
        actions()
    }
}

@Composable
fun SrSegments(
    labels: List<String>, selected: Int, onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier, backdrop: Backdrop? = LocalSrBackdrop.current
) {
    Row(modifier.srGlass(backdrop, SrShapes.Pill).padding(2.dp).selectableGroup()) {
        labels.forEachIndexed { index, label ->
            val active = index == selected
            Box(
                Modifier.heightIn(min = 48.dp).clip(SrShapes.Pill)
                    .background(if (active) SrColors.Primary else SrColors.Tint)
                    .selectable(active, role = Role.Tab, onClick = { onSelect(index) })
                    .padding(horizontal = 12.dp, vertical = 6.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(label, style = SrType.Label, color = if (active) SrColors.OnAction else SrColors.Text)
            }
        }
    }
}

@Composable
fun SrChip(
    label: String, modifier: Modifier = Modifier, selected: Boolean = false, enabled: Boolean = true,
    onClick: (() -> Unit)? = null, onRemove: (() -> Unit)? = null
) {
    val fg = when {
        !enabled -> SrColors.Muted
        selected -> SrColors.OnAction
        else -> SrColors.Text
    }
    val action = onRemove ?: onClick
    val interaction = when {
        action == null -> Modifier
        onRemove != null -> Modifier.clickable(enabled, onClickLabel = "Убрать $label", role = Role.Button, onClick = action)
        else -> Modifier.selectable(selected, enabled, role = Role.Checkbox, onClick = action)
    }
    Box(modifier.heightIn(min = if (action != null) 48.dp else 36.dp).clip(SrShapes.Pill).then(interaction),
        contentAlignment = Alignment.Center) {
        Row(
            Modifier.heightIn(min = 36.dp).clip(SrShapes.Pill)
                .background(if (selected && enabled) SrColors.Primary else SrColors.Tint)
                .padding(horizontal = 12.dp, vertical = 5.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(label, style = SrType.Label, color = fg)
            if (onRemove != null) SrGlyph(SrIcon.Close, tint = fg, size = 14.dp)
        }
    }
}

@Composable
fun SrSelection(label: String, checked: Boolean, onChange: (Boolean) -> Unit,
                modifier: Modifier = Modifier, enabled: Boolean = true) {
    Row(
        modifier.heightIn(min = 48.dp).toggleable(checked, enabled = enabled, role = Role.Switch, onValueChange = onChange),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        FigmaSvg(
            if (checked && enabled) "f9159_img1" else "f9159_img",
            Modifier.size(48.dp, 28.dp)
        )
        Text(label, style = SrType.Label, color = if (enabled) SrColors.Text else SrColors.Muted)
    }
}

@Composable
fun SrListRow(
    title: String, modifier: Modifier = Modifier, value: String? = null, icon: SrIcon? = null,
    destructive: Boolean = false, onClick: (() -> Unit)? = null
) {
    Row(
        modifier.fillMaxWidth().heightIn(min = 48.dp).clip(SrShapes.Small).background(SrColors.Solid)
            .then(if (onClick != null) Modifier.clickable(role = Role.Button, onClick = onClick) else Modifier)
            .padding(10.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        val fg = if (destructive) SrColors.Error else SrColors.Text
        icon?.let { SrGlyph(it, tint = fg) }
        Text(title, Modifier.weight(1f), style = SrType.Label, color = fg)
        value?.let { Text(it, style = SrType.Caption, color = SrColors.Muted) }
        if (onClick != null && value == null) SrGlyph(SrIcon.Next)
    }
}
