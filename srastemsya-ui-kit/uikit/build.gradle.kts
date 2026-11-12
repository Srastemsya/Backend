plugins {
    id("org.jetbrains.kotlin.multiplatform")
    id("com.android.kotlin.multiplatform.library")
    id("org.jetbrains.compose")
    id("org.jetbrains.kotlin.plugin.compose")
}

kotlin {
    jvmToolchain(21)
    androidLibrary {
        namespace = "ru.srastemsya.uikit"
        compileSdk = 36
        minSdk = 23
        androidResources.enable = true
        compilerOptions {
            jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_21)
        }
    }
    listOf(iosArm64(), iosSimulatorArm64()).forEach {
        it.binaries.framework {
            baseName = "SrastemsyaUIKit"
            isStatic = true
        }
    }
    sourceSets {
        commonMain.dependencies {
            api(compose.foundation)
            api("org.jetbrains.compose.material3:material3:1.9.0")
            implementation(compose.components.resources)
            implementation("org.jetbrains.kotlinx:kotlinx-datetime:0.7.1")
        }
        androidMain.dependencies {
            api("io.github.kashif-mehmood-km:backdrop-android:0.0.1-alpha02")
            implementation("com.caverock:androidsvg-aar:1.4")
        }
    }
}

compose.resources {
    packageOfResClass = "ru.srastemsya.uikit.resources"
}
