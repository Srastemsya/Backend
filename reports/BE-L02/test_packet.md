# BE-L02 · Пакет для тестировщика

## Ревизия и сборка

- Ветка: `be-l02`, база `be-l01` (`b81f61c`).
- Коммит кода и документации: `37e0e64`.
- Образ: `srastemsya_l02-runtime:local`, `sha256:d22797f22859f8944fb0c3016548859c18cf5ad069635daf6f0ef0afaf6ef6d2`.
- Отчётные файлы добавляются отдельным коммитом поверх `37e0e64` и не меняют сборку.

## Запуск изолированного стенда

Из каталога `backend` (имя проекта и порт — свои для пакета, не пересекаются с другими стендами):

```sh
NGINX_PORT=18092 docker compose -p srastemsya_l02 -f compose.yaml -f compose.dev.yaml up --build -d --wait
```

Проверка готовности через Nginx:

```sh
curl -i http://127.0.0.1:18092/identity/health
curl -i http://127.0.0.1:18092/catalog/health
curl -i http://127.0.0.1:18092/swipes/health
```

Остановка с сохранением томов:

```sh
docker compose -p srastemsya_l02 -f compose.yaml -f compose.dev.yaml down
```

Повторный запуск той же команды поднимает стенд без ошибок и дублей данных.

## Интерфейс

- Базовый URL: `http://127.0.0.1:18092` (все проверки через Nginx).
- Вход: `POST /v1/auth/challenges` → `POST /v1/auth/challenges/{challengeId}/verify`, dev-OTP по умолчанию `0427`. Между отправками кода на один контакт выдержите 60 секунд.
- Профиль: `GET /v1/me`, завершение профиля — `PUT /v1/me/registration`.
- Одиночная выдача: `GET /v1/feed/candidates` — страницы по 20 карточек с `nextCursor`, без изменений.
- Комнаты: `POST /v1/rooms`, `GET /v1/rooms/{id}` (long polling `?afterVersion=&waitSeconds=`), приглашения, старт, голоса и завершение — по [контракту комнаты v2](../../docs/contracts/lobby-v2.md) и [BE-04 мобильного контракта](../../docs/contracts/mobile-api.md#be-04--подборка-и-комната).
- Новое в этом пакете: пул раунда комнаты содержит не больше 10 карточек; в DTO `Round` появилось поле `number` — порядковый номер раунда в комнате, начиная с 1.
- Управляемое время в dev: заголовок `X-Dev-Swipes-Now` (RFC 3339) для запросов swipes; подборка передаёт часы в каталог, также принимается `X-Dev-Catalog-Now`. Срок комнаты в этом пакете — по-прежнему 30 минут от старта первого раунда.

## Участники

- `person1@example.test` … `person10@example.test` — dev-участники с завершённым профилем; каталог, подборка и комнаты доступны сразу.
- `new@example.test` — посторонний участник вне десятки для проверки изоляции комнат (`404` для чужой комнаты). На чистом стенде профиль завершается через `PUT /v1/me/registration`.
- OTP по умолчанию: `0427` (`DEV_OTP` может заменить его).

## Наборы данных

Данные загружаются автоматически при запуске Compose; ручной импорт не требуется. Описание — в публичном [README бэкенда](../../backend/README.md).

| Набор | ID карточек | Фильтр | Комментарий |
|---|---|---|---|
| События BE-D03 | `dev-swipe-event-01` … `dev-swipe-event-22` | `kind=EVENT&categoryId=dev-swipe-events` | 22 карточки; начало 2 января 2090, 00:01–00:22 UTC; основной набор AC этого пакета |
| Места BE-D03 | `dev-swipe-place-01` … `dev-swipe-place-22` | `kind=PLACE&categoryId=dev-swipe-places` | 22 карточки; карточка 21 — цена 500, карточка 22 — цена неизвестна |
| Смешанный BE-L01 | `dev-lobby-mix-01` … `dev-lobby-mix-35` | `kind=EVENT&localDate=2090-02-01` | 35 карточек, категории `dev-lobby-a/b/c` |
| Короткий BE-L01 | `dev-lobby-short-01` … `dev-lobby-short-04` | `kind=EVENT&categoryId=dev-lobby-short` | 4 карточки |
| Двухраундовый BE-L01 | `dev-lobby-two-01` … `dev-lobby-two-14` | `kind=EVENT&categoryId=dev-lobby-two` | 14 карточек |
| Пустой пул | — | бюджет 0 в `dev-swipe-events` или `dev-swipe-places` | старт возвращает `EXHAUSTED`, `round=null` |

Порядок карточек набора событий в каталоге — по возрастанию номера (для EVENT — `startsAt, id`).

## Публичные документы

- [Спецификация комнаты v2](../../docs/specs/lobby-v2/README.md)
- [BE-L02](../../docs/specs/lobby-v2/implementation.md#be-l02--пул-из-10-и-номер-раунда)
- [Приёмка комнаты v2](../../docs/specs/lobby-v2/acceptance.md)
- [Контракт комнаты v2](../../docs/contracts/lobby-v2.md) — приоритетный для комнат
- [Контракт Discovery v1](../../docs/contracts/discovery-v1.md#свайпы-в-комнате)
- [Мобильный HTTP-контракт](../../docs/contracts/mobile-api.md#be-04--подборка-и-комната)
- [README бэкенда](../../backend/README.md)
- Критерии приёмки PM: `reports/BE-L02/acceptance.md`
- Регрессия Discovery v1: `docs/specs/discovery-v1/acceptance.md`
