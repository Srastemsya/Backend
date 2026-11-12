package ru.srastemsya.uikit

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.error
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

@Composable
fun SrCard(
    modifier: Modifier = Modifier, backdrop: SrBackdrop? = null,
    content: @Composable ColumnScope.() -> Unit
) {
    Column(
        modifier.fillMaxWidth().srGlass(backdrop, SrShapes.Card, SrGlassMode.Frosted,
            SrColors.Solid.copy(alpha = .86f)).padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp), content = content
    )
}

enum class SrFeedback(val icon: SrIcon) {
    Loading(SrIcon.Clock), Empty(SrIcon.Search), Error(SrIcon.Warning),
    Success(SrIcon.Check), Offline(SrIcon.Warning)
}

@Composable
fun SrStatus(
    state: SrFeedback, title: String, message: String, modifier: Modifier = Modifier,
    actionLabel: String? = null, onAction: (() -> Unit)? = null
) {
    val color = when (state) {
        SrFeedback.Error -> SrColors.Error
        SrFeedback.Success -> SrColors.Success
        else -> SrColors.Primary
    }
    SrCard(modifier.semantics { liveRegion = LiveRegionMode.Polite }) {
        if (state == SrFeedback.Loading) CircularProgressIndicator(Modifier.size(20.dp), color = color, strokeWidth = 2.dp)
        else SrGlyph(state.icon, tint = color)
        Text(title, style = SrType.Title, color = SrColors.Text)
        Text(message, style = SrType.Body, color = SrColors.Muted)
        if (actionLabel != null && onAction != null && state != SrFeedback.Loading) SrButton(actionLabel, onAction)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SrSheet(
    title: String, message: String, onDismiss: () -> Unit, actionLabel: String, onAction: () -> Unit,
    modifier: Modifier = Modifier, dismissLabel: String? = null
) {
    ModalBottomSheet(onDismissRequest = onDismiss, modifier = modifier, containerColor = SrColors.Solid) {
        Column(Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = SrType.Heading, color = SrColors.Text)
            Text(message, style = SrType.Body, color = SrColors.Muted)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                SrButton(actionLabel, onAction, Modifier.weight(1f))
                if (dismissLabel != null) SrButton(dismissLabel, onDismiss, Modifier.weight(1f), SrButtonStyle.Secondary)
            }
        }
    }
}

@Composable
fun SrAvatar(initials: String, modifier: Modifier = Modifier, name: String? = null) {
    Box(
        modifier.size(32.dp).clip(SrShapes.Pill).background(SrColors.Tint)
            .then(if (name != null) Modifier.semantics { contentDescription = name } else Modifier),
        contentAlignment = Alignment.Center
    ) {
        Text(initials, style = SrType.Caption, color = SrColors.Primary, maxLines = 1, overflow = TextOverflow.Clip)
    }
}

@Composable
fun SrAvatarGroup(initials: List<String>, modifier: Modifier = Modifier, onInvite: (() -> Unit)? = null) {
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
        initials.take(4).forEach { SrAvatar(it) }
        if (initials.size > 4) SrAvatar("+${initials.size - 4}", name = "Ещё ${initials.size - 4}")
        if (onInvite != null) SrIconButton(SrIcon.Plus, "Пригласить", onInvite)
    }
}

enum class SrRoomState(val title: String) {
    Open("Пригласить друзей"), Voting("Продолжить выбор"), Waiting("Ожидаем участников"), Matched("Смотреть матч")
}

@Composable
fun SrRoomSummary(
    title: String, subtitle: String, initials: List<String>, state: SrRoomState, onAction: () -> Unit,
    modifier: Modifier = Modifier
) {
    SrCard(modifier) {
        Text(title, style = SrType.Heading, color = SrColors.Text)
        Text(subtitle, style = SrType.Body, color = SrColors.Muted)
        SrAvatarGroup(initials)
        SrButton(state.title, onAction, Modifier.fillMaxWidth(), enabled = state != SrRoomState.Waiting)
    }
}

enum class SrInviteState { Link, Copied, Expired }

@Composable
fun SrRoomInvite(
    title: String, message: String, state: SrInviteState, onAction: () -> Unit,
    modifier: Modifier = Modifier
) {
    SrCard(modifier.semantics { liveRegion = LiveRegionMode.Polite }) {
        SrGlyph(if (state == SrInviteState.Copied) SrIcon.Check else SrIcon.Link, tint = SrColors.Primary)
        Text(title, style = SrType.Title, color = SrColors.Text)
        Text(message, style = SrType.Body, color = SrColors.Muted)
        when (state) {
            SrInviteState.Link -> SrButton("Скопировать ссылку", onAction)
            SrInviteState.Expired -> SrButton("Создать ссылку", onAction)
            SrInviteState.Copied -> Unit
        }
    }
}

enum class SrVoteCardSize(internal val ratio: Float) { Compact(238f / 142), Tall(238f / 205), Full(238f / 300) }
enum class SrVoteMark { None, Like, Pass }

@Composable
fun SrVoteCard(
    title: String, metadata: List<String>, cover: @Composable BoxScope.() -> Unit,
    modifier: Modifier = Modifier, size: SrVoteCardSize = SrVoteCardSize.Compact,
    mark: SrVoteMark = SrVoteMark.None, description: String? = null
) {
    SrCard(modifier) {
        Box(Modifier.fillMaxWidth().aspectRatio(size.ratio).clip(SrShapes.Control), content = cover)
        Text(title, style = SrType.Heading, color = SrColors.Text)
        if (metadata.isNotEmpty()) {
            @OptIn(ExperimentalLayoutApi::class)
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(4.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                metadata.forEach { item ->
                    Text(item, Modifier.clip(SrShapes.Pill).background(SrColors.Tint).padding(horizontal = 6.dp, vertical = 3.dp),
                        style = SrType.Caption, color = SrColors.Text)
                }
            }
        }
        description?.let { Text(it, style = SrType.Body, color = SrColors.Muted) }
        when (mark) {
            SrVoteMark.Like -> Text("Нравится", style = SrType.Label, color = SrColors.Success)
            SrVoteMark.Pass -> Text("Пропущено", style = SrType.Label, color = SrColors.Muted)
            SrVoteMark.None -> Unit
        }
    }
}

@Composable
fun SrVoteActions(
    onPass: () -> Unit, onLike: () -> Unit, modifier: Modifier = Modifier,
    onUndo: (() -> Unit)? = null, progress: Float? = null, backdrop: SrBackdrop? = LocalSrBackdrop.current
) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SrIconButton(SrIcon.Undo, "Отменить выбор", { onUndo?.invoke() }, backdrop = backdrop, enabled = onUndo != null)
            SrIconButton(SrIcon.Close, "Пропустить", onPass, backdrop = backdrop)
            SrIconButton(SrIcon.Heart, "Нравится", onLike, primary = true)
        }
        progress?.takeIf { it.isFinite() }?.coerceIn(0f, 1f)?.let {
            androidx.compose.material3.LinearProgressIndicator(progress = { it }, modifier = Modifier.width(160.dp))
        }
    }
}

@Composable
fun SrVoteResult(
    matched: Boolean, title: String, message: String, actionLabel: String, onAction: () -> Unit,
    modifier: Modifier = Modifier, details: @Composable ColumnScope.() -> Unit = {}
) {
    SrCard(modifier) {
        SrGlyph(if (matched) SrIcon.Spark else SrIcon.People, tint = SrColors.Primary)
        Text(title, style = SrType.Heading, color = SrColors.Text)
        Text(message, style = SrType.Body, color = SrColors.Muted)
        details()
        SrButton(actionLabel, onAction)
    }
}

@Composable
fun SrEventCover(
    modifier: Modifier = Modifier, onUpload: (() -> Unit)? = null,
    cover: (@Composable BoxScope.() -> Unit)? = null
) {
    Box(Modifier.then(modifier).fillMaxWidth().aspectRatio(264f / 120f).clip(SrShapes.Control)
        .background(SrColors.Tint)
        .then(if (cover == null && onUpload != null) Modifier.clickable(role = Role.Button, onClick = onUpload) else Modifier),
        contentAlignment = Alignment.Center) {
        if (cover != null) cover()
        else Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
            SrGlyph(SrIcon.Photo, size = 24.dp)
            Text(if (onUpload != null) "Добавить обложку" else "Без обложки", style = SrType.Label)
        }
    }
}

enum class SrParticipation { Join, Joined, Full, Cancelled }

@Composable
fun SrEventParticipation(
    title: String, schedule: String, capacity: String, state: SrParticipation,
    onJoin: () -> Unit, modifier: Modifier = Modifier, joinLabel: String = "Присоединиться"
) {
    SrCard(modifier) {
        Text(title, style = SrType.Title, color = SrColors.Text)
        EventMeta(SrIcon.Events, schedule)
        EventMeta(SrIcon.People, capacity)
        when (state) {
            SrParticipation.Join -> SrButton(joinLabel, onJoin)
            SrParticipation.Joined -> EventMeta(SrIcon.Check, "Вы участвуете")
            SrParticipation.Full -> Text("Мест нет", style = SrType.Label, color = SrColors.Muted)
            SrParticipation.Cancelled -> Text("Событие отменено", style = SrType.Label, color = SrColors.Error)
        }
    }
}

@Composable
private fun EventMeta(icon: SrIcon, text: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
        SrGlyph(icon, size = 14.dp)
        Text(text, style = SrType.Caption, color = SrColors.Muted)
    }
}

enum class SrPublishState { Ready, Disabled, Submitting, Error }

@Composable
fun SrPublishBar(
    state: SrPublishState, onPublish: () -> Unit, modifier: Modifier = Modifier,
    errorMessage: String = "Не удалось опубликовать", label: String = "Опубликовать"
) {
    SrCard(modifier.semantics { liveRegion = LiveRegionMode.Polite }) {
        if (state == SrPublishState.Error) Text(errorMessage, style = SrType.Caption, color = SrColors.Error)
        SrButton(when (state) {
            SrPublishState.Error -> "Повторить"
            SrPublishState.Submitting -> "Публикуем…"
            else -> label
        }, onPublish, Modifier.fillMaxWidth(), enabled = state != SrPublishState.Disabled,
            loading = state == SrPublishState.Submitting)
    }
}

@Composable
fun SrProfileIdentity(
    name: String, subtitle: String, initials: String, modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null
) {
    SrCard(modifier) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 48.dp).clip(SrShapes.Small)
                .then(if (onClick != null) Modifier.clickable(role = Role.Button, onClick = onClick) else Modifier),
            horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically
        ) {
            SrAvatar(initials)
            Column(Modifier.weight(1f)) {
                Text(name, style = SrType.Title, color = SrColors.Text)
                Text(subtitle, style = SrType.Caption, color = SrColors.Primary)
            }
            if (onClick != null) SrGlyph(SrIcon.Next)
        }
    }
}

@Composable
fun SrProfileStats(stats: List<Pair<String, String>>, modifier: Modifier = Modifier) {
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        stats.forEach { (value, label) ->
            Column(Modifier.weight(1f).srGlass(null, SrShapes.Small).padding(8.dp),
                horizontalAlignment = Alignment.CenterHorizontally) {
                Text(value, style = SrType.Title, color = SrColors.Text)
                Text(label, style = SrType.Caption, color = SrColors.Muted)
            }
        }
    }
}

@Composable
fun SrRating(value: Int, modifier: Modifier = Modifier, onChange: ((Int) -> Unit)? = null) {
    require(value in 0..5)
    val semantics = if (onChange == null) Modifier.semantics { contentDescription = "Оценка: $value из 5" }
                    else Modifier.selectableGroup()
    Row(modifier.then(semantics), horizontalArrangement = Arrangement.spacedBy(2.dp)) {
        (1..5).forEach { rating ->
            val selected = value >= rating
            Box(
                if (onChange == null) Modifier.size(22.dp)
                else Modifier.size(48.dp).clip(SrShapes.Small).selectable(value == rating,
                    role = Role.RadioButton, onClick = { onChange(rating) })
                    .semantics { contentDescription = "$rating из 5" },
                contentAlignment = Alignment.Center
            ) {
                SrGlyph(if (selected) SrIcon.Star else SrIcon.StarOutline,
                    tint = if (selected) SrColors.Primary else SrColors.Muted, size = 16.dp)
            }
        }
    }
}

@Composable
fun SrReviewEditor(
    rating: Int, onRatingChange: (Int) -> Unit, comment: String, onCommentChange: (String) -> Unit,
    onSubmit: () -> Unit, modifier: Modifier = Modifier, submitting: Boolean = false,
    errorMessage: String? = null
) {
    SrCard(modifier) {
        Text("Как всё прошло?", style = SrType.Heading, color = SrColors.Text)
        SrRating(rating, onChange = if (submitting) null else onRatingChange)
        SrField(comment, onCommentChange, "Комментарий", kind = SrFieldKind.Multiline,
            placeholder = "Расскажите о встрече", enabled = !submitting, errorMessage = errorMessage)
        SrButton(if (submitting) "Отправляем…" else "Оставить отзыв", onSubmit, enabled = rating > 0, loading = submitting)
    }
}

@Composable
fun SrAuthCode(
    code: String, onCodeChange: (String) -> Unit, onResend: () -> Unit, modifier: Modifier = Modifier,
    length: Int = 6, canResend: Boolean = true, enabled: Boolean = true, errorMessage: String? = null,
    instruction: String = "Введите код из сообщения"
) {
    require(length in 4..8)
    var focused by remember { mutableStateOf(false) }
    SrCard(modifier) {
        Text("Введите код", style = SrType.Heading, color = SrColors.Text)
        Text(instruction, style = SrType.Body, color = SrColors.Muted)
        BasicTextField(
            value = code, onValueChange = { onCodeChange(it.filter { c -> c in '0'..'9' }.take(length)) },
            modifier = Modifier.fillMaxWidth().onFocusChanged { focused = it.isFocused }.semantics {
                contentDescription = "Код подтверждения"
                errorMessage?.let { error(it) }
            },
            textStyle = SrType.Title.copy(color = Color.Transparent), enabled = enabled, singleLine = true,
            cursorBrush = SolidColor(Color.Transparent), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            decorationBox = { editor ->
                Box {
                    Row(Modifier.fillMaxWidth().clearAndSetSemantics {}, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        repeat(length) { i ->
                            Box(Modifier.weight(1f).heightIn(min = 48.dp).clip(SrShapes.Small)
                                .background(SrColors.Base).border(1.dp, when {
                                    errorMessage != null -> SrColors.Error
                                    i == code.length && enabled && focused -> SrColors.Primary
                                    else -> SrColors.Border
                                }, SrShapes.Small), contentAlignment = Alignment.Center) {
                                code.getOrNull(i)?.let { Text(it.toString(), style = SrType.Title, color = SrColors.Text) }
                            }
                        }
                    }
                    Box(Modifier.matchParentSize().alpha(0f), contentAlignment = Alignment.CenterStart) { editor() }
                }
            }
        )
        errorMessage?.let { Text(it, style = SrType.Caption, color = SrColors.Error) }
        SrButton("Отправить код ещё раз", onResend, style = SrButtonStyle.Secondary, enabled = canResend && enabled)
    }
}

enum class SrEventListState(val label: String) { Registered("Записан"), Completed("Завершён"), Saved("Сохранён") }

@Composable
fun SrEventListCard(
    title: String, subtitle: String, state: SrEventListState, onOpen: () -> Unit,
    modifier: Modifier = Modifier, cover: @Composable BoxScope.() -> Unit,
    onReview: (() -> Unit)? = null
) {
    SrCard(modifier) {
        Row(Modifier.fillMaxWidth().clip(SrShapes.Small).clickable(role = Role.Button, onClick = onOpen),
            horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(92.dp, 82.dp).clip(SrShapes.Small), content = cover)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(state.label, style = SrType.Caption, color = SrColors.Primary)
                Text(title, style = SrType.Title, color = SrColors.Text)
                Text(subtitle, style = SrType.Caption, color = SrColors.Muted)
            }
            SrGlyph(SrIcon.Next)
        }
        if (state == SrEventListState.Completed && onReview != null) {
            SrButton("Оставить отзыв", onReview, Modifier.fillMaxWidth())
        }
    }
}

@Composable
fun SrNotificationRow(
    title: String, subtitle: String, unread: Boolean, onOpen: () -> Unit,
    modifier: Modifier = Modifier, icon: SrIcon = SrIcon.Bell
) {
    Row(modifier.fillMaxWidth().clip(SrShapes.Control)
        .background(if (unread) SrColors.Tint else SrColors.Solid)
        .clickable(role = Role.Button, onClick = onOpen)
        .semantics { if (unread) contentDescription = "Непрочитанное уведомление" }
        .padding(12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically) {
        SrGlyph(icon, tint = SrColors.Primary)
        Column(Modifier.weight(1f)) {
            Text(title, style = SrType.Label, color = SrColors.Text)
            Text(subtitle, style = SrType.Caption, color = SrColors.Muted)
        }
        SrGlyph(SrIcon.Next)
    }
}
