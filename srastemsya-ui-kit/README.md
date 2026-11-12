# Срастёмся · UI Kit 2.1 для Android и iOS

Один модуль `:uikit` на Kotlin Multiplatform и Compose Multiplatform. Компоненты, темы, состояния, формы и каталог находятся в `commonMain`. В `androidMain` и `iosMain` находятся адаптеры для рендеринга и платформенных ресурсов. [UI Kit в Figma](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-8378).

## С чего начать

- Для интеграции подключите модуль `uikit`. Он содержит общий UI и адаптеры Android и iOS.
- Для просмотра установите `srastemsya-catalog-debug.apk`. «Срастёмся · UI Kit» открывает каталог компонентов, «Срастёмся · Карта» открывает демо Владивостока с поиском по локальным примерам, фильтром и живым стеклом. Сборка подписана для отладки.
- Для настройки рендерера и фонового слоя используйте [руководство по картам](MAPS.md). Исполняемый пример карты находится в модуле `catalog`.

## Сборка и подключение

Откройте этот проект в Android Studio. Для Android нужны JDK 21, Android SDK 36 и Gradle Wrapper из архива. Минимальный Android API — 23. Для iOS нужны macOS и полный Xcode 26 с iOS SDK. Цели Kotlin/Native — устройство ARM64 и симулятор ARM64. Версии в комплекте — Kotlin 2.3.0, Compose Multiplatform 1.10.3 и AGP 8.13.2.

```sh
./gradlew :catalog:installDebug
./gradlew :uikit:compileKotlinIosSimulatorArm64 :uikit:compileKotlinIosArm64
./gradlew :uikit:linkDebugFrameworkIosSimulatorArm64
```

В Windows для Android используйте `gradlew.bat`. Чтобы запустить только карту после установки на подключённое устройство, используйте:

```sh
adb shell am start -n ru.srastemsya.catalog/.MapDemoActivity
```

В Kotlin Multiplatform приложении подключите модуль через `include(":uikit")` в настройках Gradle, затем добавьте `implementation(project(":uikit"))` в `commonMain.dependencies`. У корневого проекта должны быть те же плагины из `build.gradle.kts`. Импорт компонентов — `ru.srastemsya.uikit.*`. Оберните Compose-экран в `SrTheme`.

Для проверки на iOS вызовите `SrCatalogViewController()` из Kotlin iOS-цели или передайте возвращённый `UIViewController` в существующий UIKit-хост через framework `SrastemsyaUIKit`. При прямой интеграции с Xcode добавьте фазу сборки `./gradlew :uikit:embedAndSignAppleFrameworkForXcode` из каталога KMP проекта. Она подготавливает framework и ресурсы Compose для приложения. Отдельный SwiftUI UI Kit не требуется. [Интеграция KMP с Xcode](https://kotlinlang.org/docs/multiplatform/multiplatform-direct-integration.html).

## Стекло по платформам

| Поверхность | Android | iOS |
|---|---|---|
| `SrTabBar` внутри `SrGlassHost` | KMPLiquidGlass, включая преломление с API 33 и размытие с API 31 | Системный UIKit `UIGlassEffect` на iOS 26+, полупрозрачная поверхность ниже iOS 26 |
| Кнопки поверх нативной карты | KMPLiquidGlass через снимок рендерера | Системный UIKit `UIGlassEffect` на iOS 26+, `UIBlurEffect` на предыдущих версиях |
| Общие Compose-поля, карточки и произвольные поверхности | Стекло при наличии фона и соответствующем режиме, матовая поверхность для карточек по умолчанию | Матовые или полупрозрачные поверхности Compose |

`SrGlassHost` разделяет задний план и передние элементы. Дайте ему размер и положите фон в слот `background`. `SrTabBar` и другие компоненты автоматически получают фон ближайшего хоста. `SrGlassHost(enabled = false)` переключает каталог на сплошные поверхности. Для произвольного слоя карты выберите адаптер из [инструкции по рендерингу карт](MAPS.md).

Используемые эффекты — [KMPLiquidGlass](https://github.com/Kashif-E/KMPLiquidGlass) и [Apple UIGlassEffect](https://developer.apple.com/documentation/uikit/uiglasseffect).

## Компоненты и Figma

| Секция | API |
|---|---|
| [Основы](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-8950) | `SrTheme`, `SrColors`, `SrType`, `SrShapes`, `SrGlyph`, `SrArtwork`, `SrGlassHost`, `SrGlassSurface` |
| [Кнопки](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-8480), [навигация](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-8379), [выбор](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9093) | `SrButton` (основная, вторичная, опасная, загрузка, недоступная), `SrIconButton`, `SrTabBar`, `SrTopBar`, `SrSegments`, `SrChip`, `SrListRow` |
| [Поля](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-8520), [формы и состояния](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9156) | `SrField` (текст, число, телефон, поиск, многострочное), `SrSelect`, `SrDateField`, `SrComboBox`, `SrSelection`, `SrStatus`, `SrSheet` |
| [Комнаты и выбор](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9241) | `SrAvatar`, `SrAvatarGroup`, `SrRoomSummary`, `SrRoomInvite`, `SrVoteCard`, `SrVoteActions`, `SrVoteResult` |
| [События и участие](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9463), [карточки профиля](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9846) | `SrEventCover`, `SrEventParticipation`, `SrPublishBar`, `SrEventListCard`, `SrCard` |
| [Профиль и отзывы](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9602), [обратная связь](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9756) | `SrProfileIdentity`, `SrProfileStats`, `SrRating`, `SrReviewEditor`, `SrAuthCode`, `SrNotificationRow`. Для коротких сообщений каталог показывает `SnackbarHost`. |

Цвета и шрифты централизованы в `Theme.kt`. Размеры в Compose заданы в dp и sp. Активные зоны большинства компактных элементов увеличены до 48 dp. Оригинальные SVG лежат в ресурсах Android и iOS; примеры обложек используют их локально, а компоненты карточек принимают слот для изображения из приложения. Inter поставляется вместе с [лицензией OFL](INTER-OFL.txt).

## Состояния и обработчики

- Компоненты получают данные и состояние снаружи. Передавайте `value` и обновляйте его в `onValueChange`. Для ошибки передавайте `errorMessage`; номер телефона, формат и бизнес-правила проверяет приложение. `SrComboBox` получает уже отфильтрованные подсказки и показывает до пяти.
- Календарь использует системный диалог Android и Material 3 на iOS. Обе версии отдают `SrDate` без часового пояса. Выпадающее меню и модальный лист используют Material 3. Их расположение и внешний вид могут отличаться от Figma.
- Обрабатывайте публикацию, повторную отправку, вступление, навигацию и права доступа в приложении. `SrPublishBar` блокирует повторное нажатие в `Submitting`, а в `Error` предлагает повтор. `SrAuthCode` оставляет в вводе только ASCII-цифры, длина задаётся параметром; запрос кода, таймер и проверка принадлежат приложению.
- Для свайпа применяйте жест на уровне экрана, а карточке и кнопкам передавайте общий результат `Like` или `Pass`. Это оставляет те же действия доступными без жеста. Карточка отображает статус, кнопки вызывают обработчики, приложение определяет матч и очередь карточек.
- Цветовую тему, оптические параметры, платформенные меню и крупный системный шрифт сверяйте на целевых устройствах. Переключение режимов в каталоге удобно для сравнения с [образцом материала](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9078).

## Что проверено

- Android APK собран из исходников комплекта. Демо карты запущено на телефоне с Android 16. Живое обновление стекла во время жеста проверено на эмуляторе Android 15.
- Общий код и Kotlin/Native исходники для iOS ARM64 и симулятора ARM64 скомпилированы. Линковку framework и визуальную проверку iOS нужно выполнить в полном Xcode 26 с установленным iOS SDK.
- Демо использует локальные примеры событий и заведений. Основная подложка карты требует интернета, резервный набор тайлов покрывает ограниченный участок.
