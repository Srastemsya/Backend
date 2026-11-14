# Срастёмся · Android UI Kit

Библиотека Kotlin / Jetpack Compose для [актуальной секции UI Kit в Figma](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-8378). Содержит светлую тему, исходные иконки и иллюстрации, компоненты с состояниями и отдельное демонстрационное приложение.

## Открыть и собрать

Откройте корень этой папки в Android Studio. Для Gradle выберите **JDK 21**, установите **Android SDK 36** и укажите путь к SDK через Android Studio или переменную `ANDROID_HOME`. Минимальная версия для установки — Android 6.0 (API 23). При первой сборке Gradle скачает зависимости из Google Maven, Maven Central и Gradle Plugin Portal.

```sh
./gradlew :catalog:installDebug
./gradlew :uikit:assembleRelease
./gradlew :uikit:check :catalog:lintDebug
```

В Windows замените `./gradlew` на `gradlew.bat`. Для запуска из Android Studio выберите конфигурацию **catalog**. В каталоге вкладки открывают основы, формы, комнаты, события и профиль; переключатель «Жидкое стекло» сравнивает режимы на одном фоне. В верхнем образце навигация лежит поверх иллюстрации маяка из Figma: особенно хорошо видно, как линии иллюстрации меняются под панелью. Для просмотра без сборки установите приложенный к архиву `srastemsya-catalog-debug.apk`. В версии 1.1 оба режима проверены на эмуляторе Android 15 (API 35): в режиме стекла линии маяка видны под панелью и искажаются у её кромки.

## Подключить к приложению

1. Скопируйте папку `uikit` в корень Android-проекта и добавьте `include(":uikit")` в `settings.gradle.kts`.
2. В зависимостях приложения добавьте `implementation(project(":uikit"))`. В настройках проекта должны быть `google()` и `mavenCentral()`. Версии в этом комплекте: AGP 8.13.2, Kotlin и Compose compiler plugin 2.3.0, Compose Foundation 1.10.0, Material 3 1.4.0. В существующем приложении согласуйте версии Compose между модулями.
3. Оберните экран в `SrTheme`. Импорты компонентов — `ru.srastemsya.uikit.*`. Для фона со стеклом используйте `SrGlassHost`.

```kotlin
@Composable
fun MeetingTabs(selected: SrTab, onSelect: (SrTab) -> Unit) {
    SrTheme {
        SrGlassHost(
            modifier = Modifier.fillMaxSize(),
            background = {
                SrArtwork(SrIllustration.GlassDemo, Modifier.fillMaxSize())
            }
        ) {
            SrTabBar(
                selected = selected,
                onSelect = onSelect,
                modifier = Modifier.align(Alignment.BottomCenter)
                    .navigationBarsPadding().padding(16.dp)
            )
        }
    }
}
```

`SrGlassHost` захватывает только содержимое слота `background`. Размещайте стеклянные компоненты в слоте `content`: `SrTabBar`, `SrTopBar`, `SrIconButton`, `SrSegments`, поля и `SrGlassSurface` берут захваченный фон из ближайшего `SrGlassHost` по умолчанию. Указывать `backdrop` вручную нужно только при выборе другого источника. `SrGlassHost(enabled = false)` отключает автоматический фон; `SrCard` по умолчанию остаётся матовой, как карточки в Figma. Фоновый слой не участвует в измерении: задайте размер контейнеру или основному содержимому. Для собственного элемента используйте `Modifier.srGlass(backdrop)` либо `SrGlassSurface(backdrop)`.

| Режим | Что видно на Android |
|---|---|
| `Liquid`, API 33+ | Размытие, преломление и светлая кромка |
| `Liquid`, API 31–32 | Размытие и светлая кромка |
| `Frosted`, API 31+ | Более выраженное размытие без преломления; подходит для фоновой прокрутки |
| API 23–30 с фоном | Полупрозрачная заливка и светлая кромка без размытия и преломления |
| `Solid`, явный `backdrop = null` или компонент вне `SrGlassHost` | Белая сплошная поверхность с обводкой |

Эффект рисует [KMPLiquidGlass](https://github.com/Kashif-E/KMPLiquidGlass), Android-артефакт `io.github.kashif-mehmood-km:backdrop-android:0.0.1-alpha02` (Apache 2.0). Версия предварительная и закреплена в Gradle. KMPLiquidGlass поддерживает несколько платформ; этот комплект рассчитан на Android. Для `MapView`, видео и других отдельно отрисовываемых поверхностей сначала проверьте захват фона; если нужный фон не попадает в Compose-слой, передайте `null`. На одном экране старайтесь переиспользовать один backdrop.

## Компоненты и Figma

| Секция | API |
|---|---|
| [Основы](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-8950) | `SrTheme`, `SrColors`, `SrType`, `SrShapes`, `SrGlyph`, `SrArtwork`, `SrGlassHost`, `SrGlassSurface` |
| [Кнопки](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-8480), [навигация](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-8379), [выбор](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9093) | `SrButton` (основная, вторичная, опасная, загрузка, недоступная), `SrIconButton`, `SrTabBar`, `SrTopBar`, `SrSegments`, `SrChip`, `SrListRow` |
| [Поля](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-8520), [формы и состояния](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9156) | `SrField` (текст, число, телефон, поиск, многострочное), `SrSelect`, `SrDateField`, `SrComboBox`, `SrSelection`, `SrStatus`, `SrSheet` |
| [Комнаты и выбор](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9241) | `SrAvatar`, `SrAvatarGroup`, `SrRoomSummary`, `SrRoomInvite`, `SrVoteCard`, `SrVoteActions`, `SrVoteResult` |
| [События и участие](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9463), [карточки профиля](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9846) | `SrEventCover`, `SrEventParticipation`, `SrPublishBar`, `SrEventListCard`, `SrCard` |
| [Профиль и отзывы](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9602), [обратная связь](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9756) | `SrProfileIdentity`, `SrProfileStats`, `SrRating`, `SrReviewEditor`, `SrAuthCode`, `SrNotificationRow`. Для коротких сообщений каталог показывает `SnackbarHost`. |

Цвета и шрифты централизованы в `Theme.kt`. В Android-размерах использованы dp и sp. Активные зоны большинства компактных элементов увеличены до 48 dp. Оригинальные SVG лежат в `uikit/src/main/assets`; примеры обложек используют их локально, а компоненты карточек принимают слот для изображения из приложения. Inter поставляется вместе с [лицензией OFL](INTER-OFL.txt).

## Состояния и обработчики

- Компоненты получают данные и состояние снаружи. Передавайте `value` и обновляйте его в `onValueChange`. Для ошибки передавайте `errorMessage`; номер телефона, формат и бизнес-правила проверяет приложение. `SrComboBox` получает уже отфильтрованные подсказки и показывает до пяти.
- Календарь открывается системным диалогом Android и отдаёт `SrDate` без часового пояса. Выпадающее меню и модальный лист используют Material 3. Их расположение и внешний вид могут отличаться от Figma.
- Обрабатывайте публикацию, повторную отправку, вступление, навигацию и права доступа в приложении. `SrPublishBar` блокирует повторное нажатие в `Submitting`, а в `Error` предлагает повтор. `SrAuthCode` оставляет в вводе только ASCII-цифры, длина задаётся параметром; запрос кода, таймер и проверка принадлежат приложению.
- Для свайпа применяйте жест на уровне экрана, а карточке и кнопкам передавайте общий результат `Like` или `Pass`. Это оставляет те же действия доступными без жеста. Карточка отображает статус, кнопки вызывают обработчики, приложение определяет матч и очередь карточек.
- Цветовую тему, оптические параметры, платформенные меню и крупный системный шрифт сверяйте на целевых устройствах. Переключение режимов в каталоге удобно для сравнения с [образцом материала](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9078).
