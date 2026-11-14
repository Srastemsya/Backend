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
        versionCode = 2
        versionName = "1.1"
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
    implementation("androidx.activity:activity-compose:1.12.2")
}
