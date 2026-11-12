# HTTP API для Android и iOS v0.1

Черновик контракта к [спецификации бэкенда](../specs/backend.md). Предлагаемый префикс — `/v1`. Ниже описаны согласуемые маршруты и инварианты. URL окружений и значения лимитов фиксируются перед интеграцией.

Для реализации трёх экранов см. [контракт первого релиза](discovery-v1.md). Он уточняет общие DTO и правила для этого объёма.

## Общие правила

- HTTPS, UTF-8 и JSON. Успешные чтения и изменения возвращают `200`, создание ресурса — `201`, операции без ответа — `204`. Отдельно оговорённые повторы могут возвращать исходный статус.
- Все маршруты API требуют `Authorization: Bearer <accessToken>`, кроме запроса/проверки OTP и обновления сессии. До завершения профиля действуют ограничения BE-01. Сервер извлекает пользователя из сессии.
- ID — непрозрачные строки. Временные отметки — RFC 3339 в UTC, локальные даты — `YYYY-MM-DD`, часовые пояса — IANA. Цена и бюджет представлены целым числом в минимальных единицах валюты. Для беты предлагается RUB. Координаты — десятичные градусы `latitude [-90,90]` и `longitude [-180,180]`.
- Запись вида `field?` обозначает необязательное поле запроса. Для PATCH отсутствие поля оставляет значение, явный `null` очищает только nullable-поля. Сервер проверяет вход и права на каждый объект.
- Списки возвращают `{items, nextCursor}`, где `nextCursor: null` означает конец. `cursor` привязан к пользователю, фильтрам и порядку запроса. При изменении фильтров начинать заново. Истёкший курсор даёт `409 CURSOR_EXPIRED`.
- Для POST-операций с побочными эффектами требуется `Idempotency-Key`. Клиент сохраняет ключ до определённого исхода и повторяет с тем же телом. Одинаковые ключ, операция, пользователь и тело возвращают тот же результат. Другие данные с тем же ключом дают `409 IDEMPOTENCY_CONFLICT`. Для OTP и refresh область ключа привязана к контакту, challenge или семейству сессии. Сервер хранит результаты в течение согласованного окна. PUT/DELETE устанавливают состояние ресурса и безопасны при повторе. Актуальные данные после повторного воспроизведения старого ответа доступны через GET.

```json
{
  "error": {
    "code": "EVENT_FULL",
    "message": "Свободных мест нет",
    "requestId": "req_8wq",
    "details": {"capacity": 8, "confirmedCount": 8, "remainingCount": 0}
  }
}
```

| HTTP | Коды и обработка |
|---|---|
| 400 | `BAD_REQUEST` для невалидного JSON или несовместимых параметров. |
| 401 | `UNAUTHENTICATED`, `SESSION_EXPIRED`. Для просроченного access token — одна попытка refresh, затем повтор исходной операции с тем же ключом. |
| 403 | `FORBIDDEN`, `PROFILE_INCOMPLETE`, `CHAT_ACCESS_DENIED`. |
| 404 | `NOT_FOUND` для отсутствующего ресурса или скрытого приватного ресурса. |
| 409 | `EVENT_FULL`, `EVENT_CLOSED`, `REGISTRATION_REMOVED`, `STALE_ROUND`, `INVALID_STATE`, `CURSOR_EXPIRED`, `IDEMPOTENCY_CONFLICT`. Клиент обновляет ресурс перед следующим новым действием. |
| 410 | `OTP_EXPIRED`, `INVITE_EXPIRED`. |
| 422 | `VALIDATION_ERROR` с `details.fields` как словарём «поле → код». `OTP_INVALID` для неверного кода. |
| 429 | `RATE_LIMITED` с заголовком `Retry-After` в секундах. |
| 5xx | `SERVER_ERROR`. При сетевом сбое или 5xx повторять безопасно с исходным ключом. |

## BE-01 · Вход и сессия

| Метод и путь | Вход → выход |
|---|---|
| `POST /auth/challenges` | `{channel: SMS\|EMAIL, destination}` → `{challengeId, expiresAt, resendAvailableAt}`. Повторная отправка создаёт новый challenge после разрешённого времени. Ответ не раскрывает наличие аккаунта. |
| `POST /auth/challenges/{id}/verify` | `{code: string}` → `Session`. Код из четырёх цифр сохраняет ведущие нули. |
| `POST /auth/refresh` | `{refreshToken}` → новая `Session`. |
| `DELETE /auth/session` | Отзывает текущую сессию → `204`. |
| `GET /me` | Возвращает `Profile`, в том числе незавершённый. |
| `PUT /me/registration` | `{displayName, birthDate}` → `Profile` с `profileComplete=true`. Поле `birthDate` — предложение до согласования различия макетов возраста и даты рождения. |

`Session = {accessToken, accessExpiresAt, refreshToken, refreshExpiresAt, userId, profileComplete}`.

`Profile = {id, profileComplete, displayName: string|null, birthDate: date|null, city: string|null, bio: string|null, avatar: MediaRef|null, stats: {eventsCount, roomsCount}}`. Для черновика счётчики отражают количество уникальных событий, где пользователь был автором или имеет подтверждённую запись, и комнат, в которых пользователь участвовал.

## BE-02–03 · Каталог, события и запись

`CatalogRef = {kind: EVENT|PLACE|ACTIVITY, id}`. `Location = {latitude, longitude, address}`. `Money = {amountMinor, currency}`. `MediaRef = {id, url, expiresAt}`, где URL может быть временным и не служит идентификатором.

`CatalogCard = {ref: CatalogRef, title, categoryId, cover: MediaRef|null, location: Location, price: Money|null, startsAt: timestamp|null, admission: Admission|null}`.

`Admission` — одно из двух состояний:

```json
{"type":"OPEN"}
```

```json
{"type":"REGISTRATION","capacity":8,"confirmedCount":4,"remainingCount":4}
```

`Event = {id, organizerId, title, description, categoryId, cover: MediaRef|null, location, price: Money|null, startsAt, endsAt, timeZone, admission, phase: UPCOMING|ONGOING|PAST, viewer: {role: ORGANIZER|ATTENDEE|VISITOR, registration: Registration|null, canRegister, canReadChat, canPostChat, saved}}`.

`Registration = {id, eventId, userId, status: CONFIRMED|REMOVED, createdAt, removedAt: timestamp|null}`. `phase` определяется серверными часами. Запись разрешается до начала события по рабочему правилу v0.1. Бесплатное событие передаёт сумму 0, неизвестная стоимость — `null`. Положительная цена описывает условие входа. Платная запись включается после согласования оплаты или внешнего способа расчёта.

| Метод и путь | Вход → выход |
|---|---|
| `GET /home` | `{quickCategories: Category[], collections: Collection[], upcoming: CatalogCard[]}`. |
| `GET /catalog/categories` | `{items: Category[]}`. |
| `GET /catalog/map` | `bbox=west,south,east,north&kind=EVENT\|PLACE\|ACTIVITY` и фильтры → страницы `CatalogCard`. |
| `GET /catalog/search/suggestions` | `q?` → `{items: [{label, query}]}`. Без текста список пуст. С текстом возвращается до 20 уникальных названий опубликованных объектов каталога, содержащих запрос без учёта регистра. Недавние запросы хранятся на устройстве. |
| `GET /catalog/search` | `q` (необязателен для подборок Discovery v1), `kind?`, фильтры → страницы `CatalogCard`. |
| `GET /catalog/{kind}/{id}` | `EVENT` → тот же `Event`, что и в деталях афиши. Другие типы → `{card: CatalogCard, description}`. |
| `GET /events` | Афиша, фильтры и курсор → страницы `CatalogCard`, по умолчанию предстоящие по `startsAt, id`. |
| `GET /events/{id}` | `Event` с полями текущего пользователя. |
| `POST /events` | `CreateEvent` → опубликованный `Event`. Повтор возвращает тот же ID. |
| `POST /events/{id}/registrations` | Пустое тело → `{registration, admission}`. Существующая активная запись возвращается без увеличения счётчика. |
| `GET /events/{id}/registrations` | Только организатор. Страницы `{registration, participant: {id, displayName, avatar}}` для активных записей. |
| `DELETE /events/{id}/registrations/{registrationId}` | Только организатор. → `{registration, admission}`. Повтор возвращает снятую запись и текущую вместимость. |

`Category = {id, label, kinds: Kind[]}`. `Collection = {id, title, cover: MediaRef|null, filters: CatalogFilters}`. Фильтры каталога — `{kind?, categoryId?, localDate?, maxPriceMinor?, onlyWithSeats?}`. Дата фильтрует дату начала события в `Asia/Vladivostok`. Ограничение цены исключает неизвестную цену. `onlyWithSeats=true` оставляет события по записи с положительным остатком.

`CreateEvent = {title, description, categoryId, coverMediaId?, location, price?, startsAt, endsAt, timeZone, admission: {type: OPEN}|{type: REGISTRATION, capacity}}`. `endsAt > startsAt`, время начала при публикации находится в будущем. В Discovery v1 `endsAt` можно опустить, тогда сервер прибавляет к началу два часа. Для афиши Владивостока `timeZone=Asia/Vladivostok`. См. [правила публикации и участия](discovery-v1.md#афиша-публикация-и-участие). Счётчики, владелец и права вычисляются сервером.

## BE-04 · Подборка и комната

`FeedFilters = {kind: PLACE|EVENT, categoryId?, localDate?, budgetTotal: Money|null, partySize?}`. Предложение для сравнения общей суммы с ценой на человека — передавать `partySize` при заданном бюджете, сверять `price.amountMinor * partySize <= budgetTotal.amountMinor`. Для комнаты берётся размер зафиксированного состава. Правила источников цены и неизвестной стоимости подлежат согласованию.

`Room = {id, name: string|null, ownerId, state: LOBBY|VOTING|REFRESHING|MATCHED|EXHAUSTED|CLOSED, version, members: [{userId, displayName}], filters: FeedFilters|null, round: Round|null, result: {winner: CatalogRef}|null}`.

`Round = {id, memberCount, finishedCount, candidates: CatalogCard[], myVotes: [{candidate: CatalogRef, choice: LIKE|PASS}], myFinished: boolean}`. В `LOBBY` раунд равен `null`. Чужие голоса в snapshot отсутствуют. Победитель один после согласования tie-break. Для тестового стенда предлагается максимум лайков, при равенстве — порядок в пуле. До утверждения правила этот порядок является тестовым.

| Метод и путь | Вход → выход |
|---|---|
| `GET /feed/candidates` | Фильтры и `cursor?` → страницы `CatalogCard`. В рамках одной выдачи карточки не повторяются. |
| `POST /rooms` | `{name?}` → `Room` в `LOBBY`, создатель уже участник. |
| `POST /rooms/{id}/invites` | Только владелец в `LOBBY` → `{url, expiresAt}`. |
| `POST /room-invites/join` | `{token}` → `Room`. Только до старта, уже состоящий участник получает текущий snapshot. |
| `GET /rooms/{id}` | Только участник → текущий `Room`. Клиент может опрашивать при ожидании и после переподключения. |
| `POST /rooms/{id}/start` | Только владелец в `LOBBY`, тело `{filters}` → `Room`. Пул и состав фиксируются атомарно. |
| `PUT /rooms/{id}/rounds/{roundId}/votes/{kind}/{candidateId}` | `{choice: LIKE\|PASS}` → `Room`. Изменение голоса до завершения своего прохода — рабочее предложение. |
| `PUT /rooms/{id}/rounds/{roundId}/completion` | Пустое тело → `Room`. Проверить наличие голоса по каждой карточке. Повтор уже принятого завершения возвращает текущий snapshot даже после смены раунда. |

Каждое изменение snapshot, включая сохранение голоса, повышает `version`. Клиент игнорирует snapshot с меньшей версией. Состав, пулы и результаты сохраняются на сервере. Новый голос для завершённого раунда возвращает `409 STALE_ROUND`. До согласования тайм-аута и выхода из раунда контракт описывает happy path с восстановлением соединения.

## BE-05 · История, отправка и вложения

В истории сообщения отсортированы по серверному `sequence` внутри диалога. История принимает `beforeSequence?` или `afterSequence?` и `limit?`. Без границы возвращается последняя страница. Ответ `{items, hasMore}`. При догрузке прошлого использовать минимальный полученный sequence, при обновлении — максимальный. Элементы внутри страницы идут от меньшего sequence к большему.

`Message = {id, clientMessageId, sequence, sender: {id, displayName, avatar}, sentAt, content: MessageContent}`.

```json
{"clientMessageId":"client_19","content":{"type":"PHOTOS","mediaIds":["m1","m2"]}}
```

Остальные типы отправки — `{type:"TEXT", text}` и `{type:"LOCATION", location: Location}`. Для фото ответ содержит дополнительно `media: MediaRef[]` в порядке `mediaIds`. Вариант PHOTOS с одним ID отображается как фото, с несколькими — как альбом. Дедупликация по «диалог, отправитель, clientMessageId». Повтор с изменённым содержимым даёт `409 IDEMPOTENCY_CONFLICT`.

| Метод и путь | Вход → выход |
|---|---|
| `GET /events/{id}/chat/messages` | История по sequence. Только пользователи с правом чтения. |
| `POST /events/{id}/chat/messages` | `{clientMessageId, content}` → `Message`. Только пользователи с правом отправки. |
| `POST /media/uploads` | `{purpose: AVATAR\|CHAT_PHOTO\|EVENT_COVER, contentType, sizeBytes, eventId?}` → `{mediaId, uploadUrl, uploadHeaders, expiresAt}`. Для CHAT_PHOTO обязателен eventId и проверяется право отправки. |
| `PUT <uploadUrl>` | Байты файла и возвращённые заголовки без access token API → успешный ответ хранилища. |
| `POST /media/uploads/{mediaId}/complete` | Пустое тело → `{mediaId, status: READY}` после серверной проверки. |
| `GET /media/{mediaId}/access` | Новый `MediaRef` при актуальном доступе к объекту-владельцу или собственному неопубликованному файлу. |

Пустой текст после удаления пробелов даёт `422`. Файл из другого чата или другого назначения не принимается. Отправка повторно проверяет права, даже если пользователь уже загрузил фото. Если право потеряно между загрузкой и отправкой, файл останется непривязанным до очистки.

## BE-06 · Профиль, списки и поддержка

| Метод и путь | Вход → выход |
|---|---|
| `PATCH /me` | `{displayName?, city?, bio?, avatarMediaId?}` → `Profile`. Поля `city`, `bio` и `avatarMediaId` принимают `null`. Дата рождения меняется отдельным согласованным процессом. |
| `GET /me/events?bucket=UPCOMING\|PAST\|SAVED` | Страницы `{card: CatalogCard, role, registration: Registration\|null, canReview}`. В UPCOMING попадают также текущие события. |
| `PUT /me/saved-events/{eventId}` | Идемпотентно сохраняет событие → `204`. Подтверждённая запись исключает его из выдачи SAVED независимо от сохранённого флага. |
| `DELETE /me/saved-events/{eventId}` | Снимает сохранение → `204`. |
| `PUT /events/{id}/my-review` | `{rating, comment?}` → `{eventId, rating, comment: string\|null, createdAt}`. Тот же отзыв повторяется безопасно, отличающееся тело после первого успешного сохранения даёт `409 INVALID_STATE` до согласования редактирования. |
| `GET /me/support/messages` | История по правилам sequence. |
| `POST /me/support/messages` | `{clientMessageId, content: {type: TEXT, text}}` → `Message`. Диалог создаётся при первой успешной отправке. |

## Проверки контракта для интеграции

1. OTP с ведущим нулём, повтор verify после потери ответа, обновление сессии и отказ после отзыва.
2. Публикация с повтором и один ID на карте, в афише и пуле другого аккаунта. Оба типа входа сериализуются согласно `Admission`.
3. Два запроса на последнее место, повтор записи, снятие записи и отказ в доступе к закрытому чату.
4. Комната из четырёх пользователей. Два лайка, новый пул, три лайка, один результат при параллельном завершении, восстановление личных голосов после переподключения.
5. История чата в обе стороны без дубликатов, повтор отправки и альбом в порядке выбора.
6. Отклонение чужого вложения, незавершённой загрузки, отзыва без записи и запроса к приватной комнате от постороннего пользователя.

### Локальный BE-D00

Команда Compose, URL эмуляторов, синтетические контакты и проверки готовности описаны в [README бэкенда](../../backend/README.md). Правила OTP, refresh и завершения регистрации для этого пакета определены в [контракте Discovery v1](discovery-v1.md#вход-и-регистрация).
