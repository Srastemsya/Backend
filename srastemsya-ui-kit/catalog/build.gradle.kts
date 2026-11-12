plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "ru.srastemsya.catalog"
    compileSdk = 36
    defaultConfig {
        applicationId = "ru.srastemsya.catalog"
        minSdk = 23
        targetSdk = 36
        versionCode = 4
        versionName = "2.1"
    }
    buildFeatures { compose = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
}
kotlin { jvmToolchain(21) }
dependencies {
    implementation(project(":uikit"))
    implementation("org.maplibre.gl:android-sdk:13.6.1")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.caverock:androidsvg-aar:1.4")
    implementation("androidx.activity:activity-compose:1.12.2")
}
