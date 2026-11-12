# Swipes

Владеет снимками одиночной выдачи, курсорами и состоянием комнат в собственной PostgreSQL. Получает кандидатов и публичные данные участников через внутренние HTTP-маршруты catalog и identity. Redis Pub/Sub передаёт номер версии комнаты для пробуждения long polling. В Compose доступен как `swipes:8000`.

Все маршруты требуют Bearer JWT завершённого профиля. POST требует `Idempotency-Key`.

| Метод и путь | Вход | Успешный ответ |
|---|---|---|
| `GET /v1/feed/candidates` | `kind`, опционально `categoryId, localDate, budgetTotalMinor, partySize, cursor` | `200 {items: CatalogCard[], nextCursor}` |
| `POST /v1/rooms` | Опциональное тело `{name}` | `201 Room` |
| `POST /v1/rooms/{id}/invites` | Владелец, пустое тело | `201 {url, expiresAt}` |
| `POST /v1/room-invites/join` | `{token}` из ссылки | `200 Room` |
| `POST /v1/rooms/{id}/start` | Владелец, `{filters: FeedFilters}` | `200 Room` |
| `PUT /v1/rooms/{id}/rounds/{roundId}/votes/{kind}/{candidateId}` | `{choice: "LIKE" \| "PASS"}` | `200 Room` |
| `PUT /v1/rooms/{id}/rounds/{roundId}/completion` | Пустое тело | `200 Room` |
| `GET /v1/rooms/{id}` | Опционально `afterVersion` и `waitSeconds` | `200 Room` или `204` без изменений |

Long polling использует `afterVersion` последнего снимка и ожидание до 25 секунд. Для постороннего комната скрыта с `404 NOT_FOUND`. Истёкшая ссылка для нового участника даёт `410 INVITE_EXPIRED`. Голос для старого раунда даёт `409 STALE_ROUND`, завершение без всех голосов — `409 INVALID_STATE`.

[Одиночная выдача и комнаты](../contracts/discovery-v1.md#свайпы-на-одном-устройстве) · [DTO Room и FeedFilters](../contracts/mobile-api.md#be-04--подборка-и-комната) · [Интеграция с catalog и identity](../contracts/catalog-integration.md) · [Служебные маршруты](README.md#служебные-маршруты)
