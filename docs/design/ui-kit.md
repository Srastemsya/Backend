# UI Kit · Liquid Glass

[Секция в Figma](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=69-583). Библиотека для мобильных макетов «Срастёмся». Общие мастера, формы и навигация находятся в этой секции. [Компоненты карты](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=33-884) и [компоненты главной](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=36-338) доступны из того же файла.

Для Android и iOS доступен [единый Kotlin Multiplatform UI Kit](../../srastemsya-ui-kit/README.md) с [инструкцией по рендерингу карт](../../srastemsya-ui-kit/MAPS.md). [Актуальная секция UI Kit](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-8378).

| Группа | Figma |
|---|---|
| 01 · Основы и иконки | [Открыть](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-686) |
| 02 · Навигация и выбор | [Открыть](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-857) |
| 03 · Формы и состояния | [Открыть](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1065) |
| 04 · Комнаты и свайпы | [Открыть](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1150) |
| 05 · События и участие | [Открыть](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1499) |
| 06 · Профиль и отзывы | [Открыть](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1658) |
| 07 · Примеры сборки | [Открыть](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1817) |
| 08 · Действия, фильтры и обратная связь | [Открыть](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=165-1303) |
| 09 · Карточки событий профиля | [Открыть](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=202-2538) |

## Токены и компоновка

- Светлая тема использует семантические переменные `color/text/*`, `color/action/*`, `color/surface/*`, `color/border/*` и `color/feedback/*`. Базовые цвета карты переиспользуются через алиасы. В веб-реализации сохраняй синтаксис из Figma, например `var(--color-action-primary)`.
- Отступы и радиусы используют `space/*` и `radius/*`. Текст опирается на Inter и стили `Type / display`, `heading`, `title`, `body`, `label` и `caption`.
- Стиль `Surface / Liquid Glass` использует преломление фона, полупрозрачную заливку `color/surface/glass`, светлую кромку `color/border/glass` и мягкую тень. На [стенде материала](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=179-1346) видно, как поле и таббар преломляют иллюстрацию. Градиент `gradient/glass/backdrop` используется как подложка для проверки. Для платформы с ограниченной поддержкой эффекта используй читаемую подложку из `color/surface/solid`.
- Статусы обозначаются и текстом, и цветом. В приложении связывай ошибки с полем, объявляй загрузку и ошибки ассистивным технологиям, поддерживай фокус и доступные имена действий с иконками. Повторная отправка доступна после ошибки, а во время запроса действие блокируется.

Исходные мастера обновлены на месте. Для основных и дополнительных действий используй [Button/Base](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=66-561), [Button/Actions](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=69-582) и [Button/IconActions](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=69-581). Поля `Input`, `Select`, `Number`, `Date`, `Phone` и `Combobox` используют те же токены и стекло, что и новые поля. Синий контур обозначает фокус, красный контур и подпись обозначают ошибку, приглушённая подложка обозначает недоступность. Раскрытые списки и календарь используют общую стеклянную поверхность.

## Как собирать сценарии

Порядок вкладок — Главная → Карта → Лента → События → Профиль. Используй [единый Navigation/TabBar](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=66-555) и соответствующий активный вариант. Вкладка «Лента» открывает [выбор устройства](feed.md), затем подборку мест или событий. Групповой сценарий начинается из «Ленты» через выбор устройства. Вкладка «События» с иконкой календаря предназначена для отдельной вертикальной афиши Владивостока. Экран, переходы и правила публикации описаны в [афише](events.md).

| Сценарий | Экземпляры и состояния | Действия и переходы |
|---|---|---|
| Главная, карта, поиск | [Пример сборки](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-2062), [Field/Search](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=165-1387), [Control/Chip](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1038), [Feedback/Status](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1132) | Главная открывает подборку или событие. Карта открывает сводку по метке. При изменении запроса или фильтров обновляются результаты, отдельно показываются пустая выдача и ошибка. Подробнее в [главной](home.md) и [карте](map.md). |
| Комната и выбор | [Пример сборки](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1821), [Room/Summary](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1260), [Room/Invite](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1643), [Navigation/RoomTabs](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1026), [Vote/PlaceCard](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1414), [Vote/Actions](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1415), [Vote/Result](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1498) | Создать комнату → поделиться ссылкой → открыть выбор → пройти карточки. Действия «нравится» и «пропустить» доступны свайпом и кнопками. Каждый участник проходит весь пул и после последней карточки ждёт остальных. По завершении раунда показать матч по большинству или автоматически загрузить новый пул. |
| Создание и участие | [Пример сборки](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1948), [Media/EventCover](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1561), [Field/TextArea](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1102), [Event/PublishBar](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1657), [Event/Participation](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1625) | Добавить обложку и данные события, указать дату, время, число мест и бюджет → опубликовать. При ошибке сохранить введённые данные и предложить повтор. В деталях события показывать доступность участия, заполненность и отмену. Подробнее в [событии](event.md). |
| Лента событий и профиль | [Пример сборки](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1979), [активная Лента](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=66-492), [иконка карточек](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=169-1266), [действия свайпа](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=164-1415) | В [Ленте](feed.md) тип подборки меняется в фильтрах. Первый лайк на одном устройстве сразу открывает результат. В комнате матч большинства определяется после того, как все участники прошли весь пул. После пула без выбора или матча загружаются новые варианты. В Профиле доступны сохранённое и мои события. |
| Регистрация и уведомления | [Существующие экраны регистрации](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=129-1481), [Auth/Code](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=165-1432), [Notification/Row](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=165-1406), [Feedback/Toast](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=165-1368) | Поля регистрации и код опираются на выбранный способ входа. Уведомление открывает связанный объект. Подтверждение операции показывается отдельным коротким сообщением. |

Примеры в UI Kit показывают состав блоков и состояния. Переходы, проверка ввода, голосование и доставка уведомлений реализуются на уровне приложения. Иллюстрации заимствованы из текущих макетов, аватары показывают инициалы. Имена, даты, цены и показатели служат примерами.

## Требует решения

- Лента событий. Уточнить, куда сохраняется отметка «нравится», и когда доступны отмена свайпа и повторный просмотр.
- Комнаты. Где размещается чат, когда закрывается голосование и можно ли изменить отправленный выбор.
- Бронирование и совместная оплата. Согласовать маршрут кнопки брони и объём интеграции. Сплит через СБП в описании проекта отмечен как гипотеза.
- Регистрация, отзывы и карма. Согласовать способы входа, правила публикации и модерации отзывов и расчёт кармы. Код подтверждения в библиотеке — визуальный вариант.

