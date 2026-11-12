@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class, androidx.compose.ui.ExperimentalComposeUiApi::class)

package ru.srastemsya.uikit

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.UIKitInteropInteractionMode
import androidx.compose.ui.viewinterop.UIKitInteropProperties
import androidx.compose.ui.viewinterop.UIKitView
import kotlinx.cinterop.useContents
import platform.CoreGraphics.CGRectMake
import platform.UIKit.UIColor
import platform.UIKit.UIView

/**
 * Hosts an MLNMapView, MKMapView, or another UIView-based map with native glass controls.
 * The caller owns the renderer's setup, camera, attribution, and delegates.
 */
@Composable
fun SrIosNativeMapGlassHost(
    mapFactory: () -> UIView,
    actions: List<SrMapAction>,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    updateMap: (UIView) -> Unit = {},
    releaseMap: (UIView) -> Unit = {}
) {
    UIKitView(
        factory = { NativeMapHost(mapFactory()) },
        modifier = modifier,
        update = {
            updateMap(it.map)
            it.update(actions, enabled)
        },
        onRelease = { releaseMap(it.map) },
        properties = UIKitInteropProperties(
            interactionMode = UIKitInteropInteractionMode.NonCooperative,
            isNativeAccessibilityEnabled = true,
            placedAsOverlay = true
        )
    )
}

private class NativeMapHost(val map: UIView) : UIView(frame = CGRectMake(0.0, 0.0, 0.0, 0.0)) {
    private data class Item(val surface: UIView, val control: NativeControl)
    private var items = emptyList<Item>()
    private var labelsAndIcons = emptyList<Pair<String, SrIcon>>()
    private var glassEnabled = false

    init { addSubview(map) }

    fun update(actions: List<SrMapAction>, enabled: Boolean) {
        val keys = actions.map { it.label to it.icon }
        if (keys != labelsAndIcons || glassEnabled != enabled) {
            items.forEach { it.surface.removeFromSuperview() }
            items = actions.map { action ->
                val button = NativeControl(action.label, action.icon.mapSymbol, showsTitle = false)
                val surface = if (enabled) {
                    nativeGlass(cornerRadius = 16.0, interactive = true).apply { contentView.addSubview(button) }
                } else {
                    UIView(frame = CGRectMake(0.0, 0.0, 0.0, 0.0)).apply {
                        backgroundColor = UIColor.whiteColor
                        layer.cornerRadius = 16.0
                        addSubview(button)
                    }
                }
                addSubview(surface)
                Item(surface, button)
            }
            labelsAndIcons = keys
            glassEnabled = enabled
            setNeedsLayout()
        }
        items.zip(actions).forEach { (item, action) -> item.control.action = action.onClick }
    }

    override fun layoutSubviews() {
        super.layoutSubviews()
        map.setFrame(bounds)
        val width = bounds.useContents { size.width }
        val x = (width - safeAreaInsets.useContents { right } - 60.0).coerceAtLeast(0.0)
        val y = safeAreaInsets.useContents { top } + 12.0
        items.forEachIndexed { index, item ->
            item.surface.setFrame(CGRectMake(x, y + index * 54.0, 48.0, 48.0))
            item.control.setFrame(item.surface.bounds)
        }
    }
}

private val SrIcon.mapSymbol: String
    get() = when (this) {
        SrIcon.Location -> "location"
        SrIcon.Filter -> "line.3.horizontal.decrease"
        SrIcon.ZoomIn, SrIcon.Plus -> "plus"
        SrIcon.ZoomOut -> "minus"
        SrIcon.Map -> "map"
        SrIcon.Search -> "magnifyingglass"
        SrIcon.Save -> "bookmark"
        SrIcon.Close -> "xmark"
        SrIcon.Back -> "chevron.left"
        else -> "ellipsis"
    }
