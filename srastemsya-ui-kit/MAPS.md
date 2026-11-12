# Карты и Liquid Glass

Для карты с **живым стеклом во время жеста** используйте MapLibre Native. На Android выберите **TextureView**. Он даёт приложению доступ к кадру, который нужен для размытия и преломления. Если достаточно обновлять стекло после остановки камеры, используйте **SurfaceView** со снимком. На iOS используйте **MLNMapView** и `SrIosNativeMapGlassHost`. Адаптер размещает карту и стеклянные кнопки в одной UIKit-иерархии. Для продуктового экрана рекомендуются векторные тайлы на данных OSM. Поставщик, стиль и кэш настраиваются в приложении. [Режимы рендера MapLibre](https://maplibre.org/maplibre-compose/api/lib/maplibre-compose/org.maplibre.compose.map/-android-render-mode/index.html), [MLNMapView](https://maplibre.org/maplibre-native/ios/latest/documentation/maplibre/mlnmapview/).

| Как рисуется карта | Как подключить стекло | Когда выбирать |
|---|---|---|
| MapLibre Native или MapLibre Compose на Android, `SurfaceView` | `SrAndroidNativeMapGlassHost` и снимок текущей камеры | Подходит, если достаточно обновлять стекло после остановки камеры. |
| MapLibre Android, `TextureView` | Тот же адаптер, кадр через `TextureView.bitmap` или API снимка MapLibre | Когда нужно обновлять стекло во время перетаскивания и масштабирования либо применять трансформации к карте. MapLibre указывает на дополнительную стоимость рендера. |
| osmdroid или другой Android `View` | Снимок viewport через API рендерера или `View.draw(Canvas)` для обычного View | Если карта уже встроена в приложение. `View.draw` не захватывает отдельную поверхность `SurfaceView`. |
| MapLibre Native или MapKit на iOS | `SrIosNativeMapGlassHost` с фабрикой `MLNMapView` или `MKMapView` | Для системного стекла на iOS 26+. Для MapLibre Compose, который сам создаёт native view, используйте этот путь, если стекло должно брать фон с карты. |
| Карта, которая рисуется прямо в Compose Canvas | `SrMapGlassHost` | Когда карта уже реализована в Compose. Android может захватывать её как фон. Нативные кнопки над нативной картой iOS подключаются через UIKit-адаптер. |

## Android

### TextureView для живого стекла

Создайте `MapView` с `MapLibreMapOptions.textureMode(true)` и разместите его в `AndroidView`. После отрисовки кадра читайте `TextureView.getBitmap(width, height)` на UI-потоке и передавайте `bitmap.asImageBitmap()` в `SrAndroidNativeMapGlassHost`. Кадр должен соответствовать области карты, её повороту и масштабу. Рабочий пример с обработчиками жизненного цикла находится в [MapDemoActivity.kt](catalog/src/main/kotlin/ru/srastemsya/catalog/MapDemoActivity.kt).

- Во время движения демо делает захват с интервалом от 80 мс, то есть до 12,5 кадра в секунду. Ширина и высота кадра уменьшаются втрое. Это ограничение относится к захвату для стекла. Рендерер карты управляет своей частотой отдельно.
- После остановки камеры демо обновляет фон кадром половинного размера. При смене стиля или размера карты прежний кадр сбрасывается.
- При отсутствии TextureView адаптер может получить снимок через `MapLibreMap.snapshot` после остановки камеры. Снимок предыдущего положения отбрасывается, если камера уже ушла дальше.

### SurfaceView для снимка после жеста

Оставьте `SurfaceView` в существующем `AndroidView` или Compose-обёртке. После завершения движения и отрисовки запросите `MapLibreMap.snapshot`. Для MapLibre Compose используйте snapshotter с тем же стилем и положением камеры. При начале движения, смене стиля или размера сбрасывайте снимок. Перед применением результата проверьте, что запрос относится к актуальной камере и области карты. [MapLibreMap.snapshot](https://maplibre.org/maplibre-native/android/api/-map-libre%20-native%20-android/org.maplibre.android.maps/-map-libre-map/index.html), [снимки MapLibre Compose](https://maplibre.org/maplibre-compose/snapshotter/).

Оба способа используют один хост. В примере `ExistingMapLibreMap` обозначает карту приложения.

```kotlin
SrAndroidNativeMapGlassHost(
    snapshot = snapshotForCurrentViewport, // Bitmap.asImageBitmap()
    map = { ExistingMapLibreMap(Modifier.fillMaxSize()) },
    modifier = Modifier.fillMaxSize()
) {
    SrMapControls(
        actions = listOf(
            SrMapAction(SrIcon.Filter, "Фильтры", onFilters),
            SrMapAction(SrIcon.Location, "Моё местоположение", onLocate),
            SrMapAction(SrIcon.ZoomIn, "Приблизить", onZoomIn)
        ),
        modifier = Modifier.align(Alignment.TopEnd).padding(12.dp)
    )
    SrTabBar(
        selected = SrTab.Map,
        onSelect = onTabSelected,
        modifier = Modifier.align(Alignment.BottomCenter).padding(12.dp),
        translucentFallback = true
    )
}
```

Кадр записывается в графический слой для стекла, поэтому живая карта продолжает получать жесты. При `translucentFallback = true` у таббара сохраняется полупрозрачная поверхность, пока кадр недоступен. Когда фон готов, панель берёт цвета и контуры с карты. `SrGlassMode.Solid` явно включает сплошной режим.

Android API 33+ поддерживает размытие и преломление. На API 31–32 доступно размытие. Для нативной карты на API 23–30 хост использует прозрачную основу таббара с `translucentFallback = true` и сплошную подложку кнопок.

Проверены два режима MapLibre Native 13.6.1 на эмуляторе Android 15. На `SurfaceView` стекло размывает линию из снимка. На `TextureView` фон внутри таббара меняется во время перетаскивания. Загрузка Владивостока и отрисовка стекла также проверены на подключённом телефоне с Android 16.

## iOS

Передайте фабрику существующей карты в iOS-части приложения. UI Kit принимает любой `UIView`, поэтому Gradle-модуль не фиксирует версию MapLibre. Для MapLibre SDK должен быть уже подключён в приложении или доступен через его Kotlin cinterop. `updateMap` обновляет настройки карты, `releaseMap` позволяет снять делегаты и подписки.

```kotlin
SrIosNativeMapGlassHost(
    mapFactory = { createConfiguredMapLibreView() }, // MLNMapView : UIView
    actions = actions,
    modifier = Modifier.fillMaxSize(),
    releaseMap = { map -> releaseMapDelegates(map) }
)
```

Адаптер размещает элементы управления поверх карты как соседние UIKit view. Нативный эффект на iOS 26+ работает в пределах правил системного композитора. Поведение с конкретным Metal-рендерером и стилем карты проверьте на устройстве. На более ранней iOS используется системный `UIBlurEffect`.

OpenStreetMap предоставляет данные. Стиль, сервер тайлов, кэш, лицензирование и видимая атрибуция остаются в настройках карты приложения. Убедитесь, что кнопки не перекрывают атрибуцию. [Политика тайлов OpenStreetMap](https://operations.osmfoundation.org/policies/tiles/).

## Демо на Android

Установите APK каталога и откройте «Срастёмся · Карта». Экран использует MapLibre Native в режиме TextureView и открывает Владивосток. Во время движения карты демо захватывает фон не чаще 12,5 раза в секунду с уменьшенным разрешением. В покое берёт более чёткий кадр. Основная подложка демо загружается с OpenStreetMap. APK также содержит небольшой резервный набор векторных тайлов OpenFreeMap с ограниченным покрытием. Если захват кадра ещё недоступен, нижняя панель остаётся полупрозрачной. Метки, цены, поиск и фильтр работают с локальными демонстрационными данными. Кнопка с мишенью возвращает к стартовому виду Владивостока. [Источник подложки](https://openfreemap.org/quick_start/).
