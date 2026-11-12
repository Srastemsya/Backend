@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package ru.srastemsya.uikit

import androidx.compose.ui.window.ComposeUIViewController
import platform.UIKit.UIViewController

fun SrCatalogViewController(): UIViewController = ComposeUIViewController {
    SrTheme { Catalog(if (hasNativeGlass()) "Системный Liquid Glass" else "Полупрозрачность") }
}
