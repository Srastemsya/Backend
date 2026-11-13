# BE-L01 · Пакет для тестировщика

## Ревизия и сборка

- Ветка: `be-l01`, база `dev` (`c7fb434`).
- Коммит кода и документации: `6edf059`.
- Образ: `srastemsya_l01-runtime:local`, `sha256:7d3dcac56740318b5f5f7d38f6ee96ac2919bd00a705590c239175a944da6579`.
- Отчётные файлы добавляются отдельным коммитом поверх `6edf059` и не меняют сборку.

## Запуск изолированного стенда

Из каталога `backend`:

```sh
NGINX_PORT=18090 docker compose -p srastemsya_l01 -f compose.yaml -f compose.dev.yaml up --build -d --wait
```

Проверка готовности через Nginx:

```sh
curl -i http://127.0.0.1:18090/identity/health
curl -i http://127.0.0.1:18090/catalog/health
curl -i http://127.0.0.1:18090/swipes/health
```

Остановка с сохранением томов:

```sh
docker compose -p srastemsya_l01 -f compose.yaml -f compose.dev.yaml down
```

Повторный запуск той же команды использует сохранённые тома. Для независимого чистого стенда задайте своё имя проекта и свободный `NGINX_PORT`.

## Интерфейс

- Базовый URL: `http://127.0.0.1:18090`.
- Вход: `POST /v1/auth/challenges` → `POST /v1/auth/challenges/{challengeId}/verify`, OTP по умолчанию `0427`.
- Профиль: `GET /v1/me`, завершение профиля — `PUT /v1/me/registration`.
- Одиночная выдача: `GET /v1/feed/candidates`.
- Афиша: `GET /v1/events`.
- Комнаты: `POST /v1/rooms`, `GET /v1/rooms/{id}`, приглашения и голосование — по [контракту комнаты v2](../../docs/contracts/lobby-v2.md).
- Управляемое время в dev: заголовок `X-Dev-Swipes-Now` (RFC 3339) для запросов swipes и `X-Dev-Catalog-Now` для запросов каталога. Подборка передаёт часы в каталог.

## Участники

- `person1@example.test` … `person10@example.test` — dev-участники с завершённым профилем; доступны каталог, подборка и комнаты.
- `new@example.test` — отдельный участник вне десятки для проверки изоляции комнат. На чистом стенде профиль завершается через `PUT /v1/me/registration`.
- OTP по умолчанию: `0427` (`DEV_OTP` может заменить его).

## Наборы данных

Данные загружаются автоматически при запуске Compose; ручной импорт не требуется. Описание в публичном [README бэкенда](../../backend/README.md#стендовые-данные-комнаты-be-l01).

| Набор | ID карточек | Категории | Начало (UTC) | Фильтр выдачи |
|---|---|---|---|---|
| Смешанный | `dev-lobby-mix-01` … `dev-lobby-mix-35` | `dev-lobby-a`, `dev-lobby-b`, `dev-lobby-c` | 2090-02-01, с 00:01 | `kind=EVENT&localDate=2090-02-01` |
| Короткий | `dev-lobby-short-01` … `dev-lobby-short-04` | `dev-lobby-short` | 2090-03-01, с 00:01 | `kind=EVENT&categoryId=dev-lobby-short` |
| Двухраундовый | `dev-lobby-two-01` … `dev-lobby-two-14` | `dev-lobby-two` | 2090-03-02, с 00:01 | `kind=EVENT&categoryId=dev-lobby-two` |

Распределение категорий смешанного набора по номерам карточек — в таблице публичного [README бэкенда](../../backend/README.md#стендовые-данные-комнаты-be-l01) и в [BE-L01](../../docs/specs/lobby-v2/implementation.md#be-l01--стендовые-данные).

## Публичные документы

- [Спецификация комнаты v2](../../docs/specs/lobby-v2/README.md)
- [BE-L01](../../docs/specs/lobby-v2/implementation.md#be-l01--стендовые-данные)
- [Приёмка комнаты v2](../../docs/specs/lobby-v2/acceptance.md)
- [Контракт комнаты v2](../../docs/contracts/lobby-v2.md)
- [Контракт Discovery v1](../../docs/contracts/discovery-v1.md)
- [Мобильный HTTP-контракт](../../docs/contracts/mobile-api.md)
- Критерии приёмки PM: `reports/BE-L01/acceptance.md`
