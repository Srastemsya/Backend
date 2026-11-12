package ru.srastemsya.catalog

import android.content.Intent
import okhttp3.OkHttpClient
import org.maplibre.android.module.http.HttpRequestUtil
import android.os.Bundle
import android.os.SystemClock
import android.view.TextureView
import android.view.View
import android.view.ViewGroup
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.RectF
import com.caverock.androidsvg.SVG
import org.maplibre.android.MapLibre
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapLibreMapOptions
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import ru.srastemsya.uikit.*
import kotlin.math.roundToInt

class MapDemoActivity : ComponentActivity() {
    private lateinit var mapView: MapView
    private var renderer: MapLibreMap? = null
    private var snapshot by mutableStateOf<ImageBitmap?>(null)
    private var points by mutableStateOf<Map<String, IntOffset>>(emptyMap())
    private var failed by mutableStateOf(false)
    private var loaded by mutableStateOf(false)
    private var moving = false
    private var generation = 0
    private var capturePending = false
    private var rendered = false
    private var fullyRenderedLastFrame = false
    private var lastCapture = 0L
    private var texture: TextureView? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        MapLibre.getInstance(this)
        HttpRequestUtil.setOkHttpClient(
            OkHttpClient.Builder().addInterceptor { chain ->
                val request = chain.request()
                chain.proceed(request.newBuilder().header("User-Agent", "SrastemsyaMapDemo/2.1 Android").build())
            }.build()
        )
        mapView = MapView(this, MapLibreMapOptions.createFromAttributes(this).textureMode(true))
        mapView.onCreate(savedInstanceState)
        mapView.addOnDidFailLoadingMapListener {
            failed = true
            loaded = false
            invalidateFrame()
        }
        mapView.addOnDidFinishRenderingFrameListener { fullyRendered, _, _ ->
            mapView.post {
                if (!isDestroyed) {
                    val completed = fullyRendered && !fullyRenderedLastFrame
                    fullyRenderedLastFrame = fullyRendered
                    rendered = true
                    captureFrame(force = completed)
                }
            }
        }
        mapView.addOnLayoutChangeListener { _, l, t, r, b, oldL, oldT, oldR, oldB ->
            if (r - l != oldR - oldL || b - t != oldB - oldT) {
                invalidateFrame()
                projectMarkers()

            }
        }
        mapView.getMapAsync { map ->
            renderer = map
            if (savedInstanceState == null) map.cameraPosition = initialCamera()
            map.setMinZoomPreference(11.0)
            map.setMaxZoomPreference(16.0)
            map.setLatLngBoundsForCameraTarget(
                org.maplibre.android.geometry.LatLngBounds.from(43.20, 132.10, 42.98, 131.77)
            )
            val bottom = (resources.displayMetrics.density * 90).roundToInt()
            map.uiSettings.setAttributionMargins(12, 0, 0, bottom)
            map.uiSettings.setLogoMargins(70, 0, 0, bottom)
            map.addOnCameraMoveStartedListener {
                moving = true
                if (texture?.isAvailable != true) invalidateFrame()
            }
            map.addOnCameraMoveListener { projectMarkers() }
            map.addOnCameraIdleListener {
                moving = false
                projectMarkers()
                captureFrame(force = true)
            }
            loadStyle()
        }
        setContent { SrTheme { MapScreen() } }
    }

    private fun initialCamera() = CameraPosition.Builder()
        .target(LatLng(43.105, 131.907)).zoom(12.2).build()

    private fun invalidateFrame() {
        generation++
        snapshot = null
        rendered = false
        fullyRenderedLastFrame = false
        capturePending = false
    }

    private fun loadStyle() {
        failed = false
        loaded = false
        invalidateFrame()
        renderer?.setStyle(Style.Builder().fromUri("asset://map/vladivostok.json")) {
            loaded = true
            projectMarkers()
        }
    }

    private fun projectMarkers() {
        val projection = renderer?.projection ?: return
        points = places.associate { place ->
            val point = projection.toScreenLocation(place.position)
            place.id to IntOffset(point.x.roundToInt(), point.y.roundToInt())
        }
    }

    private fun captureFrame(force: Boolean = false) {
        val map = renderer ?: return
        if (!loaded || !rendered || mapView.width == 0 || mapView.height == 0) return
        val surface = texture?.takeIf { it.isAvailable } ?: mapView.findTexture()?.also { texture = it }
        if (surface?.isAvailable == true) {
            val now = SystemClock.uptimeMillis()
            if (!force && ((!moving && snapshot != null) || now - lastCapture < 80)) return
            lastCapture = now
            val scale = if (moving) 3 else 2
            surface.getBitmap((surface.width / scale).coerceAtLeast(1), (surface.height / scale).coerceAtLeast(1))
                ?.let { snapshot = it.asImageBitmap() }
            return
        }
        if (moving || capturePending || snapshot != null) return
        val request = generation
        capturePending = true
        map.snapshot { frame ->
            if (request == generation && !moving && !isDestroyed) {
                capturePending = false
                snapshot = frame.asImageBitmap()
            }
        }
    }

    private fun View.findTexture(): TextureView? {
        if (this is TextureView) return this
        if (this is ViewGroup) {
            for (index in 0 until childCount) {
                getChildAt(index).findTexture()?.let { return it }
            }
        }
        return null
    }

    @Composable
    private fun MapScreen() {
        var category by rememberSaveable { mutableStateOf(Category.Events) }
        var selected by rememberSaveable { mutableStateOf<String?>(null) }
        var freeOnly by rememberSaveable { mutableStateOf(false) }
        var search by rememberSaveable { mutableStateOf(false) }
        var filters by rememberSaveable { mutableStateOf(false) }
        var detail by rememberSaveable { mutableStateOf(false) }
        val chosen = places.firstOrNull { it.id == selected }
        val visible = places.filter { it.category == category && (!freeOnly || it.price == 0) }
        val density = LocalDensity.current
        val markerOffset = with(density) { IntOffset(27.dp.roundToPx(), 64.dp.roundToPx()) }

        SrAndroidNativeMapGlassHost(
            snapshot = snapshot,
            modifier = Modifier.fillMaxSize().background(SrColors.Base).safeDrawingPadding(),
            map = { AndroidView(factory = { mapView }, modifier = Modifier.fillMaxSize()) }
        ) {
            visible.forEach { place ->
                points[place.id]?.let { point ->
                    MapPin(place, point - markerOffset, selected == place.id) { selected = place.id }
                }
            }
            Column(Modifier.align(Alignment.TopCenter).padding(horizontal = 12.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                SrTopBar("Карта", actions = {
                    SrIconButton(SrIcon.Search, "Поиск", { search = true })
                    SrIconButton(SrIcon.Filter, "Фильтры", { filters = true })
                })
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                    Category.entries.forEach { item ->
                        SrChip(item.label, selected = category == item, onClick = {
                            category = item
                            selected = null
                        })
                    }
                }
            }
            SrMapControls(
                listOf(
                    SrMapAction(SrIcon.ZoomIn, "Приблизить") { renderer?.animateCamera(CameraUpdateFactory.zoomIn()) },
                    SrMapAction(SrIcon.ZoomOut, "Отдалить") { renderer?.animateCamera(CameraUpdateFactory.zoomOut()) },
                    SrMapAction(SrIcon.Location, "Вернуться к Владивостоку") {
                        renderer?.animateCamera(CameraUpdateFactory.newCameraPosition(initialCamera()))
                    }
                ),
                Modifier.align(Alignment.CenterEnd).padding(end = 12.dp)
            )
            if (failed) {
                SrStatus(SrFeedback.Error, "Карта недоступна", "Попробуйте загрузить участок ещё раз.",
                    Modifier.align(Alignment.Center).padding(horizontal = 64.dp), "Повторить", ::loadStyle)
            }
            Column(Modifier.align(Alignment.BottomCenter).padding(horizontal = 12.dp, vertical = 8.dp),
                horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (chosen != null) {
                    SrGlassSurface(modifier = Modifier.fillMaxWidth(), mode = SrGlassMode.Frosted) {
                        SrListRow(chosen.title, Modifier.padding(6.dp), icon = SrIcon.Map,
                            onClick = { detail = true })
                    }
                }
                SrTabBar(SrTab.Map, { tab ->
                    if (tab != SrTab.Map) startActivity(Intent(this@MapDemoActivity, MainActivity::class.java))
                }, translucentFallback = true)
            }
        }
        if (search) {
            var query by rememberSaveable { mutableStateOf("") }
            AlertDialog(
                onDismissRequest = { search = false },
                title = { Text("Поиск на карте") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        SrField(query, { query = it }, "Название", placeholder = "Событие или место", kind = SrFieldKind.Search)
                        val matches = places.filter { it.title.contains(query.trim(), ignoreCase = true) }
                        if (matches.isEmpty()) Text("Ничего не найдено")
                        matches.forEach { place ->
                            SrListRow(place.title, onClick = {
                                freeOnly = false
                                category = place.category
                                selected = place.id
                                renderer?.animateCamera(CameraUpdateFactory.newLatLngZoom(place.position, 14.0))
                                search = false
                            })
                        }
                    }
                },
                confirmButton = { TextButton(onClick = { search = false }) { Text("Закрыть") } }
            )
        }
        if (filters) {
            var draft by rememberSaveable { mutableStateOf(freeOnly) }
            AlertDialog(
                onDismissRequest = { filters = false },
                title = { Text("Фильтры") },
                text = { SrSelection("Только бесплатные", draft, { draft = it }) },
                confirmButton = { TextButton(onClick = { freeOnly = draft; selected = null; filters = false }) { Text("Показать") } },
                dismissButton = { TextButton(onClick = { draft = false }) { Text("Сбросить") } }
            )
        }
        if (detail && chosen != null) {
            AlertDialog(
                onDismissRequest = { detail = false },
                title = { Text(chosen.title) },
                text = { Text(if (chosen.price == 0) "Демо · Бесплатно" else "Демо · от ${chosen.price} ₽") },
                confirmButton = { TextButton(onClick = { detail = false }) { Text("Готово") } }
            )
        }
    }

    override fun onStart() { super.onStart(); mapView.onStart() }
    override fun onResume() { super.onResume(); mapView.onResume() }
    override fun onPause() { mapView.onPause(); super.onPause() }
    override fun onStop() { mapView.onStop(); super.onStop() }
    override fun onDestroy() { invalidateFrame(); mapView.onDestroy(); super.onDestroy() }
    override fun onSaveInstanceState(outState: Bundle) { super.onSaveInstanceState(outState); mapView.onSaveInstanceState(outState) }
    override fun onLowMemory() { super.onLowMemory(); mapView.onLowMemory() }
}

private enum class Category(val label: String) {
    Events("События"), Places("Заведения"), Activities("Активности")
}

private enum class Pin(val outline: String, val glyph: String) {
    Activity("img2", "imgmountain"), Place("img3", "imgdrink"),
    Quiz("img4", "imgtrophy"), Event("img5", "imggroup")
}

private data class Place(val id: String, val title: String, val position: LatLng, val category: Category, val pin: Pin, val price: Int)

private val places = listOf(
    Place("walk", "Прогулка у Токаревского маяка", LatLng(43.078, 131.850), Category.Activities, Pin.Activity, 0),
    Place("quiz", "Квиз на Светланской", LatLng(43.119, 131.904), Category.Events, Pin.Quiz, 700),
    Place("meet", "Встреча на набережной", LatLng(43.121, 131.871), Category.Events, Pin.Event, 0),
    Place("bar", "Бар «Миллионка»", LatLng(43.116, 131.883), Category.Places, Pin.Place, 850),
    Place("coffee", "Кофе у Золотого моста", LatLng(43.110, 131.929), Category.Places, Pin.Place, 350),
    Place("trail", "Маршрут на Русском острове", LatLng(43.032, 131.900), Category.Activities, Pin.Activity, 0)
)

@Composable
private fun MapPin(place: Place, offset: IntOffset, active: Boolean, onClick: () -> Unit) {
    val outline = markerArtwork(place.pin.outline)
    val glyph = markerArtwork(place.pin.glyph)
    Box(Modifier.offset { offset }.size(54.dp, 64.dp).clickable(role = Role.Button, onClick = onClick)) {
        Image(outline, place.title, Modifier.align(Alignment.TopCenter).size(54.dp, 64.dp))
        Image(glyph, null, Modifier.align(Alignment.TopCenter).padding(top = 15.dp).size(24.dp))
        if (active) Box(Modifier.align(Alignment.TopEnd).padding(top = 5.dp).size(10.dp)
            .clip(SrShapes.Pill).background(SrColors.Primary))
    }
}

@Composable
private fun markerArtwork(file: String): ImageBitmap {
    val assets = LocalContext.current.assets
    val density = LocalDensity.current.density
    return remember(assets, file, density) {
        val svg = assets.open("map/$file.svg").use(SVG::getFromInputStream)
        val width = svg.documentWidth
        val height = svg.documentHeight
        Bitmap.createBitmap((width * density).roundToInt(), (height * density).roundToInt(),
            Bitmap.Config.ARGB_8888).also { bitmap ->
            val canvas = Canvas(bitmap)
            canvas.scale(bitmap.width / width, bitmap.height / height)
            svg.renderToCanvas(canvas, RectF(0f, 0f, width, height))
        }.asImageBitmap()
    }
}
