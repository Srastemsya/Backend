# Сервисы Discovery v1

- [Identity](identity.md) — вход, профиль и сессии.
- [Catalog](catalog.md) — главная, каталог, афиша, публикация и запись.
- [Swipes](swipes.md) — одиночная выдача и комнаты.

Реестр описывает маршруты первого релиза. Базовый URL и запуск приведены в [README бэкенда](../../backend/README.md). Общие форматы запросов, DTO и ошибок описаны в [мобильном контракте](../contracts/mobile-api.md) с уточнениями [Discovery v1](../contracts/discovery-v1.md).

## Служебные маршруты

| Запрос через Nginx | Доступ и ответ |
|---|---|
| `GET /health` | Без токена. `200` с текстом `ok`, проверяет шлюз. |
| `GET /{service}/health` | Без токена. `200 {"status":"ok"}` или `503 {"status":"error","reason":"…"}` при неготовности сервиса. |
| `GET /{service}/admin` | Отдельный Bearer JWT HS256 с аудиторией `srastemsya-admin` и сроком `exp`. `200` HTML или `401 UNAUTHENTICATED`. |
| `GET /dev-media/{filename}` | Без токена. `200 image/jpeg` для обложек из dev-архива или `404`. URL фото разрешается относительно origin API. |

В путях `{service}` принимает `identity`, `catalog` или `swipes`. Внутренние HTTP-маршруты доступны в сети Compose.
