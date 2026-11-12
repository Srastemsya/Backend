# Catalog

Владеет объектами каталога, категориями, подборками, записями и ревизией каталога в собственной PostgreSQL. Использует Redis для метаданных и курсоров. Публикует события Kafka в `catalog.changed.v1`. В Compose доступен как `catalog:8000`.

Публичные маршруты требуют Bearer JWT и завершённый профиль. POST требует `Idempotency-Key`.

| Метод и путь | Вход | Успешный ответ |
|---|---|---|
| `GET /v1/home` | Без параметров | `200 {quickCategories, collections, upcoming}` |
| `GET /v1/catalog/categories` | Без параметров | `200 {items: Category[]}` |
| `GET /v1/catalog/search` | `q` необязателен, фильтры каталога, `cursor` | `200 {items: CatalogCard[], nextCursor}` |
| `GET /v1/catalog/search/suggestions` | Необязательный `q` | `200 {items: [{label, query}]}` |
| `GET /v1/catalog/map` | `kind`, `bbox=west,south,east,north`, фильтры и `cursor` | `200 {items: CatalogCard[], nextCursor}` |
| `GET /v1/catalog/{kind}/{id}` | Тип и ID | `200 Event` для EVENT, иначе `200 {card: CatalogCard, description}` |
| `GET /v1/events` | `categoryId, localDate, maxPriceMinor, onlyWithSeats, cursor` | `200 {items: CatalogCard[], nextCursor}` |
| `GET /v1/events/{id}` | ID события | `200 Event` |
| `POST /v1/events` | `CreateEvent` | `201 Event` |
| `POST /v1/events/{id}/registrations` | Пустое тело | `201 {registration, admission}` или `200` для существующей активной записи |
| `GET /v1/events/{id}/registrations` | Организатор, `cursor` | `200 {items, nextCursor}` |
| `DELETE /v1/events/{id}/registrations/{registrationId}` | Организатор, пустое тело | `200 {registration, admission}` |
| `GET /internal/catalog/candidates` | Сеть Compose, Bearer JWT завершённого профиля, фильтры свайпов | `200 {items: CatalogCard[]}`, полный снимок |

Просроченный курсор возвращает `409 CURSOR_EXPIRED`. Состояния записи включают `EVENT_FULL`, `EVENT_CLOSED`, `REGISTRATION_REMOVED` и `INVALID_STATE`. Обложки dev-карточек описаны в публичном контракте.

[Публичные DTO, фильтры и ошибки](../contracts/discovery-v1.md) · [Общие DTO](../contracts/mobile-api.md) · [Внутренний API и Kafka](../contracts/catalog-integration.md) · [Служебные маршруты](README.md#служебные-маршруты)
