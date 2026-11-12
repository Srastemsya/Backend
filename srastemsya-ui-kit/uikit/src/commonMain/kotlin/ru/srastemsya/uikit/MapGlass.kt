package ru.srastemsya.uikit

import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

data class SrMapAction(val icon: SrIcon, val label: String, val onClick: () -> Unit)

/** For maps painted into the Compose draw pass. For native views use the platform adapter. */
@Composable
fun SrMapGlassHost(
    map: @Composable BoxScope.() -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    controls: @Composable BoxScope.() -> Unit
) = SrGlassHost(map, modifier, enabled) { controls() }

@Composable
fun SrMapControls(actions: List<SrMapAction>, modifier: Modifier = Modifier) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        actions.forEach { action -> SrIconButton(action.icon, action.label, action.onClick) }
    }
}
