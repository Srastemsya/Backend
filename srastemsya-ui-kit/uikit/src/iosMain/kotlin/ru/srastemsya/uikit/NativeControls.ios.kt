@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class, androidx.compose.ui.ExperimentalComposeUiApi::class)

package ru.srastemsya.uikit

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.widthIn
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.UIKitInteropProperties
import androidx.compose.ui.viewinterop.UIKitView
import kotlinx.cinterop.BetaInteropApi
import kotlinx.cinterop.ObjCAction
import kotlinx.cinterop.useContents
import platform.CoreGraphics.CGRectMake
import platform.Foundation.NSSelectorFromString
import platform.UIKit.*

@Composable
internal actual fun SrNativeTabBar(selected: SrTab, onSelect: (SrTab) -> Unit, modifier: Modifier): Boolean {
    if (!hasNativeGlass()) return false
    UIKitView(
        factory = { NativeTabBar() },
        modifier = modifier.widthIn(max = 358.dp).fillMaxWidth().height(72.dp),
        update = { it.update(selected, onSelect) },
        properties = UIKitInteropProperties(isNativeAccessibilityEnabled = true, placedAsOverlay = true)
    )
    return true
}

internal fun nativeGlass(cornerRadius: Double, interactive: Boolean = false): UIVisualEffectView {
    if (hasNativeGlass()) {
        val effect = UIGlassEffect.effectWithStyle(UIGlassEffectStyle.UIGlassEffectStyleRegular)
        effect.interactive = interactive
        return UIVisualEffectView(effect = effect).apply {
            cornerConfiguration = UICornerConfiguration.configurationWithUniformRadius(
                UICornerRadius.fixedRadius(cornerRadius)
            )
        }
    }
    return UIVisualEffectView(effect = UIBlurEffect.effectWithStyle(UIBlurEffectStyle.UIBlurEffectStyleSystemMaterialLight)).apply {
        layer.cornerRadius = cornerRadius
        clipsToBounds = true
    }
}

private val accent = UIColor(red = .239, green = .282, blue = .980, alpha = 1.0)
private val muted = UIColor(red = .376, green = .380, blue = .482, alpha = 1.0)

private class NativeTabBar : UIView(frame = CGRectMake(0.0, 0.0, 0.0, 0.0)) {
    private val glass = nativeGlass(cornerRadius = 26.0)
    private val tabs = SrTab.entries.map { tab ->
        NativeControl(tab.title, tab.symbol).apply { glass.contentView.addSubview(this) }
    }

    init { addSubview(glass) }

    fun update(selected: SrTab, onSelect: (SrTab) -> Unit) {
        SrTab.entries.zip(tabs).forEach { (tab, button) ->
            button.action = { onSelect(tab) }
            button.setTabSelected(selected == tab)
        }
    }

    override fun layoutSubviews() {
        super.layoutSubviews()
        glass.setFrame(bounds)
        val width = bounds.useContents { size.width }
        val height = bounds.useContents { size.height }
        val itemWidth = ((width - 16.0) / tabs.size).coerceAtLeast(0.0)
        tabs.forEachIndexed { index, control ->
            control.setFrame(CGRectMake(8.0 + itemWidth * index, (height - 48.0) / 2.0, itemWidth, 48.0))
        }
    }
}

internal class NativeControl(
    name: String,
    symbol: String,
    private val showsTitle: Boolean = true
) : UIControl(frame = CGRectMake(0.0, 0.0, 0.0, 0.0)) {
    var action: () -> Unit = {}
    private val icon = UIImageView(image = UIImage.systemImageNamed(symbol))
    private val caption = UILabel().apply {
        text = name
        font = UIFont.systemFontOfSize(11.0, weight = UIFontWeightSemibold)
        textAlignment = NSTextAlignmentCenter
        adjustsFontSizeToFitWidth = true
        minimumScaleFactor = .75
        isAccessibilityElement = false
    }

    init {
        isAccessibilityElement = true
        accessibilityLabel = name
        accessibilityTraits = UIAccessibilityTraitButton
        layer.cornerRadius = 16.0
        icon.contentMode = UIViewContentMode.UIViewContentModeScaleAspectFit
        icon.tintColor = muted
        addSubview(icon)
        if (showsTitle) addSubview(caption)
        addTarget(this, NSSelectorFromString("invokeAction"), UIControlEventTouchUpInside)
    }

    fun setTabSelected(active: Boolean) {
        icon.tintColor = if (active) accent else muted
        caption.textColor = if (active) accent else muted
        backgroundColor = if (active) UIColor(red = .925, green = .925, blue = 1.0, alpha = .75) else UIColor.clearColor
        accessibilityTraits = UIAccessibilityTraitButton or (if (active) UIAccessibilityTraitSelected else 0uL)
    }

    @OptIn(BetaInteropApi::class)
    @ObjCAction
    fun invokeAction() = action()

    override fun layoutSubviews() {
        super.layoutSubviews()
        val width = bounds.useContents { size.width }
        val height = bounds.useContents { size.height }
        icon.setFrame(CGRectMake((width - 22.0) / 2.0, if (showsTitle) 3.0 else (height - 22.0) / 2.0, 22.0, 22.0))
        caption.setFrame(CGRectMake(1.0, 27.0, (width - 2.0).coerceAtLeast(0.0), 18.0))
    }
}

private val SrTab.symbol: String
    get() = when (this) {
        SrTab.Home -> "house"
        SrTab.Map -> "mappin.and.ellipse"
        SrTab.Feed -> "rectangle.on.rectangle"
        SrTab.Events -> "calendar"
        SrTab.Profile -> "person.crop.circle"
    }
