plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "ru.srastemsya.uikit"
    compileSdk = 36
    defaultConfig { minSdk = 23 }
    buildFeatures { compose = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
}
kotlin { jvmToolchain(21) }
dependencies {
    api("androidx.compose.foundation:foundation:1.10.0")
    api("androidx.compose.material3:material3:1.4.0")
    api("io.github.kashif-mehmood-km:backdrop-android:0.0.1-alpha02")
    implementation("com.caverock:androidsvg-aar:1.4")
    implementation("androidx.core:core-ktx:1.17.0")
}
