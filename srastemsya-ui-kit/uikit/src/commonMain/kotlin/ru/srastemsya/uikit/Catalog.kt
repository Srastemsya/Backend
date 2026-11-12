package ru.srastemsya.uikit

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable
internal fun Catalog(glassDescription: String) {
    var tab by rememberSaveable { mutableStateOf(SrTab.Feed) }
    var glass by rememberSaveable { mutableStateOf(true) }
    var sheet by rememberSaveable { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val notify: (String) -> Unit = { message -> scope.launch { snackbar.showSnackbar(message) }; Unit }
    SrGlassHost(
        background = { Box(Modifier.fillMaxSize().srGlassBackground()) },
        modifier = Modifier.fillMaxSize(),
        enabled = glass
    ) {
        Column(Modifier.fillMaxSize().safeDrawingPadding()) {
            val scroll = rememberScrollState()
            LaunchedEffect(tab) { scroll.scrollTo(0) }
            Column(
                Modifier.weight(1f).fillMaxWidth().verticalScroll(scroll).padding(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text("Срастёмся", style = SrType.Display, color = SrColors.Text)
                Text("Каталог компонентов Android", style = SrType.Body, color = SrColors.Muted)
                SrSelection("Жидкое стекло", glass, { glass = it })
                Text(
                    when {
                        !glass -> "Сплошные поверхности"
                        else -> glassDescription
                    },
                    style = SrType.Caption, color = SrColors.Text
                )
                GlassSample(glass)
                key(tab) {
                    when (tab) {
                        SrTab.Home -> Foundations(notify) { sheet = true }
                        SrTab.Map -> Forms()
                        SrTab.Feed -> Rooms(notify)
                        SrTab.Events -> Events(notify)
                        SrTab.Profile -> Profile(notify)
                    }
                }
            }
            Box(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
                contentAlignment = Alignment.Center) {
                SrTabBar(tab, { tab = it })
            }
        }
        SnackbarHost(snackbar, Modifier.align(Alignment.BottomCenter).safeDrawingPadding().padding(bottom = 88.dp))
    }
    if (sheet) SrSheet("Подтверждение", "Пример диалога из UI Kit", { sheet = false }, "Подтвердить", {
        sheet = false
        notify("Подтверждено")
    }, dismissLabel = "Отмена")
}

@Composable
private fun GlassSample(glass: Boolean) {
    var active by rememberSaveable { mutableStateOf(SrTab.Feed) }
    var dateParts by rememberSaveable { mutableStateOf("") }
    val date = dateParts.split(".").takeIf { it.size == 3 }?.let { (d, m, y) -> SrDate(y.toInt(), m.toInt(), d.toInt()) }
    SrGlassHost(
        background = {
            Box(Modifier.fillMaxSize().srGlassBackground(146.71f))
            SrArtwork(SrIllustration.GlassDemo, Modifier.fillMaxSize().padding(start = 28.dp))
        },
        modifier = Modifier.fillMaxWidth().height(230.dp).clip(SrShapes.Card),
        enabled = glass
    ) {
        SrDateField(date, { dateParts = it.formatted() }, "Дата события",
            Modifier.align(Alignment.TopCenter).widthIn(max = 350.dp).padding(horizontal = 14.dp, vertical = 24.dp))
        SrTabBar(active, { active = it },
            Modifier.align(Alignment.BottomCenter).padding(horizontal = 10.dp, vertical = 18.dp))
    }
}

@Composable
private fun Foundations(notify: (String) -> Unit, onSheet: () -> Unit) {
    SrTopBar("Действия", actions = { SrIconButton(SrIcon.Bell, "Уведомления", { notify("Уведомления") }) })
    SrButton("Присоединиться", { notify("Действие выполнено") }, Modifier.fillMaxWidth())
    SrButton("Показать на карте", { notify("Карта") }, Modifier.fillMaxWidth(), SrButtonStyle.Secondary)
    SrButton("Сбросить", onSheet, Modifier.fillMaxWidth(), SrButtonStyle.Destructive)
    SrButton("Отправляем…", {}, Modifier.fillMaxWidth(), loading = true)
    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        listOf(SrIcon.Filter, SrIcon.Location, SrIcon.ZoomIn, SrIcon.ZoomOut, SrIcon.Back,
            SrIcon.Close, SrIcon.Save, SrIcon.Share).forEach { icon ->
            SrIconButton(icon, icon.name, { notify(icon.name) })
        }
    }
    var selected by rememberSaveable { mutableStateOf(false) }
    var chipVisible by rememberSaveable { mutableStateOf(true) }
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        SrChip("Вечером", selected = selected, onClick = { selected = !selected })
        SrChip("Завтра", enabled = false, onClick = {})
        if (chipVisible) SrChip("До 1000 ₽", onRemove = { chipVisible = false })
    }
    SrNotificationRow("В комнате найден матч", "Только что", true, { notify("Уведомление открыто") })
    SrFeedback.entries.forEach { state ->
        val title = when (state) {
            SrFeedback.Loading -> "Загрузка"
            SrFeedback.Empty -> "Ничего не найдено"
            SrFeedback.Error -> "Не удалось загрузить"
            SrFeedback.Success -> "Готово"
            SrFeedback.Offline -> "Нет подключения"
        }
        SrStatus(state, title, "Пример состояния",
            actionLabel = if (state == SrFeedback.Error || state == SrFeedback.Offline) "Повторить" else null,
            onAction = { notify("Повтор") })
    }
}

@Composable
private fun Forms() {
    var name by rememberSaveable { mutableStateOf("") }
    var phone by rememberSaveable { mutableStateOf("") }
    var count by rememberSaveable { mutableStateOf("") }
    var selected by rememberSaveable { mutableStateOf<String?>(null) }
    var query by rememberSaveable { mutableStateOf("") }
    var description by rememberSaveable { mutableStateOf("") }
    var search by rememberSaveable { mutableStateOf("") }
    var dateParts by rememberSaveable { mutableStateOf("") }
    val date = dateParts.split(".").takeIf { it.size == 3 }?.let { (d, m, y) -> SrDate(y.toInt(), m.toInt(), d.toInt()) }
    val choices = listOf("Спорт", "Настольные игры", "Концерт", "Выставка")
    SrField(name, { name = it }, "Имя пользователя", placeholder = "Введите имя",
        errorMessage = if (name.length == 1) "Введите хотя бы два символа" else null)
    SrField("Только чтение", {}, "Недоступно", enabled = false)
    SrSelect(selected, choices, { selected = it }, "Категория")
    SrField(count, { count = it.filter(Char::isDigit) }, "Участники", kind = SrFieldKind.Number, placeholder = "0")
    SrDateField(date, { dateParts = it.formatted() }, "Дата события")
    SrField(phone, { phone = it }, "Номер телефона", kind = SrFieldKind.Phone, placeholder = "+7 900 000-00-00")
    SrComboBox(query, { query = it }, choices.filter { it.contains(query, ignoreCase = true) }, { query = it }, "Тип")
    SrField(search, { search = it }, "Поиск", kind = SrFieldKind.Search, placeholder = "Поиск по карте")
    SrField(description, { description = it }, "Описание", kind = SrFieldKind.Multiline, placeholder = "Расскажите о встрече")
}

@Composable
private fun Rooms(notify: (String) -> Unit) {
    var segment by rememberSaveable { mutableIntStateOf(0) }
    var mark by rememberSaveable { mutableStateOf(SrVoteMark.None) }
    var invite by rememberSaveable { mutableStateOf(SrInviteState.Link) }
    Text("Комната и выбор", style = SrType.Heading, color = SrColors.Text)
    SrTopBar("Выбор места", backdrop = null, onBack = { notify("Комната") })
    SrRoomSummary("Вечер пятницы", "Сегодня, 19:00 · 7 участников",
        listOf("АК", "ОВ", "ДА", "ЕР", "ЮА", "ДН", "АВ"), SrRoomState.Voting,
        { notify("Выбор места") }, Modifier.widthIn(max = 268.dp))
    SrSegments(listOf("Выбор места", "Чат", "Инфо"), segment, { segment = it })
    SrVoteCard("Бар «Миллионка»", listOf("Бар", "₽₽", "Светланская, 13"),
        cover = { SrArtwork(SrIllustration.VoteCompact, Modifier.fillMaxSize()) },
        modifier = Modifier.widthIn(max = 262.dp), mark = mark, description = "Азиатские настойки и музыка.")
    SrVoteActions({ mark = SrVoteMark.Pass }, { mark = SrVoteMark.Like },
        onUndo = if (mark != SrVoteMark.None) ({ mark = SrVoteMark.None }) else null, progress = .4f)
    SrVoteResult(true, "Матч найден!", "Все выбрали это место", "Открыть детали", { notify("Место открыто") },
        modifier = Modifier.widthIn(max = 294.dp))
    Text("Другие состояния комнаты", style = SrType.Heading, color = SrColors.Text)
    SrRoomState.entries.filter { it != SrRoomState.Voting }.forEach { state ->
        SrRoomSummary("Вечер пятницы", "Сегодня, 19:00 · 7 участников", listOf("АК", "ОВ", "ДА"), state,
            { notify(state.title) }, Modifier.widthIn(max = 268.dp))
    }
    SrRoomInvite("Пригласить в комнату", "Отправьте ссылку друзьям", invite, { invite = SrInviteState.Copied })
}

@Composable
private fun Events(notify: (String) -> Unit) {
    SrEventCover { SrArtwork(SrIllustration.Indoor, Modifier.fillMaxSize()) }
    SrEventCover { SrArtwork(SrIllustration.Outdoor, Modifier.fillMaxSize()) }
    SrEventCover(onUpload = { notify("Запрос выбора обложки") })
    var joined by rememberSaveable { mutableStateOf(false) }
    SrEventParticipation("Сапы на Тобизина", "05.06 · 11:00", "5 из 8 мест",
        if (joined) SrParticipation.Joined else SrParticipation.Join, { joined = true })
    listOf(SrParticipation.Full, SrParticipation.Cancelled).forEach {
        SrEventParticipation("Сапы на Тобизина", "05.06 · 11:00", "8 из 8 мест", it, {})
    }
    var publish by rememberSaveable { mutableStateOf(SrPublishState.Ready) }
    SrPublishBar(publish, { publish = if (publish == SrPublishState.Error) SrPublishState.Ready else SrPublishState.Error })
    SrPublishBar(SrPublishState.Submitting, {})
    SrPublishBar(SrPublishState.Disabled, {})
}

@Composable
private fun Profile(notify: (String) -> Unit) {
    var rating by rememberSaveable { mutableIntStateOf(0) }
    var comment by rememberSaveable { mutableStateOf("") }
    var code by rememberSaveable { mutableStateOf("") }
    SrProfileIdentity("Даниил", "Мой профиль", "ДА", onClick = { notify("Профиль") })
    SrProfileStats(listOf("12" to "События", "8" to "Отзывы", "24" to "Карма"))
    SrEventListState.entries.forEach { state ->
        SrEventListCard("Встреча на Тобизина", "05.06 · Владивосток", state, { notify("Событие") },
            cover = { SrArtwork(SrIllustration.EventThumbnail, Modifier.fillMaxSize()) },
            onReview = { notify("Открыть форму отзыва") })
    }
    SrReviewEditor(rating, { rating = it }, comment, { comment = it }, { notify("Отзыв отправлен") })
    SrAuthCode(code, { code = it }, { notify("Новый код запрошен") })
}
