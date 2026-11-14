# BE-L01 · Отчёт разработчика

## Ревизия и сборка

- Ветка: `be-l01` от `dev` (`c7fb434`).
- Коммит кода и документации: `6edf059` — `BE-L01: add lobby dev participants and card sets`.
- Образ стенда: `srastemsya_l01-runtime:local`, `sha256:7d3dcac56740318b5f5f7d38f6ee96ac2919bd00a705590c239175a944da6579` (linux/arm64).
- Стенд: изолированный Compose-проект `srastemsya_l01`, Nginx на `127.0.0.1:18090`.

## Изменения

1. `backend/runtime/identity.py` — dev-контакты расширены до `person1@example.test` … `person10@example.test`. Идентификаторы считаются детерминированно, вставка осталась идемпотентной; данные участников 1–5 не менялись.
2. `backend/runtime/catalog_schema.py` — добавлена идемпотентная загрузка стендовых данных комнаты: категории `dev-lobby-a`, `dev-lobby-b`, `dev-lobby-c` (позиции 92–94), `dev-lobby-short` (95), `dev-lobby-two` (96); 35 событий `dev-lobby-mix-01` … `35`; 4 события `dev-lobby-short-01` … `04`; 14 событий `dev-lobby-two-01` … `14`. Все вставки с `ON CONFLICT DO NOTHING`.
3. `backend/README.md` — обновлён список dev-участников и добавлен раздел «Стендовые данные комнаты BE-L01»: участники, посторонний, ID наборов, категории, даты, фильтры и идемпотентность повторного запуска. Ссылки ведут на контракт комнаты v2 и спецификацию BE-L01.

Логика комнат, одиночной выдачи, приглашений, long polling, идемпотентности и каталога не менялась. Правила BE-L02+ не реализовывались. Существующие наборы `dev-swipe-*` и `dev-vlad-*` не изменены. Файлы тестировщика (`backend/services/matching/tests/`, `backend/services/catalog/tests/`, `backend/tests/`, `backend/tests/release-e2e/`) не редактировались.

## Соответствие правилам

- **workflow/rules/testing.md.** Для BE-L01 модульный набор ещё не предусмотрен (он создаётся в BE-L03), поэтому выполнены ручные HTTP-проверки через Nginx на изолированном стенде. Отчёты тестировщика и их ожидания не читались и не изменялись; новых тестовых файлов в чужих каталогах нет.
- **workflow/rules/backend-architecture.md.** Новых сервисов, баз, таблиц, Kafka-топиков, HTTP-маршрутов и DTO нет. Данные каталога остаются в PostgreSQL каталога, межсервисные вызовы не добавлены. Секреты не логировались и не выводились.
- **workflow/rules/runtime-heal.md.** `GET /health` каждого сервиса отвечает `200`; Compose-healthchecks всех контейнеров прошли при двух запусках. `DATABASE_URL`, health-проверки и heal-скрипт не менялись, новые сервисы не добавлялись.
- **workflow/rules/docs-with-code.md.** Публичный HTTP-контракт не менялся, поэтому контракты не переписывались. Изменение dev-данных и README вошли в один коммит `6edf059`.
- **Правила для всех пакетов.** Сделаны только шаги 1–6 BE-L01. Не менялись маршруты, статусы ошибок, приглашения, long polling, идемпотентность и размер страницы одиночной выдачи.

## Выполненные команды и результаты

```sh
cd backend
python3 -m py_compile runtime/catalog_schema.py runtime/identity.py
# ok

NGINX_PORT=18090 docker compose -p srastemsya_l01 -f compose.yaml -f compose.dev.yaml up --build -d --wait
# все сервисы и healthchecks готовы; запуск выполнен дважды поверх сохранённых томов

curl -sS -i http://127.0.0.1:18090/identity/health
# 200 {"status":"ok"}
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18090/catalog/health   # 200
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18090/swipes/health    # 200
```

Ручная проверка через Nginx (два прогона, второй — после повторного `up` на тех же томах):

- Вход `person1` … `person10`, `GET /v1/me`: `profileComplete=true`.
- `GET /v1/home`: `200` для всех десяти; `POST /v1/rooms` → `201`, `GET /v1/rooms/{id}` → `200`.
- `GET /v1/feed/candidates?kind=EVENT&localDate=2090-02-01`: 35 карточек `dev-lobby-mix-01` … `35`, порядок по возрастанию номера, `startsAt` = `2090-02-01T00:00:00Z + N минут`, цена 1000 копеек, категории по таблице BE-L01, страницы 20 + 15.
- `GET /v1/feed/candidates?kind=EVENT&categoryId=dev-lobby-short`: 4 карточки `dev-lobby-short-01` … `04`, `startsAt` = `2090-03-01T00:00:00Z + N минут`.
- `GET /v1/feed/candidates?kind=EVENT&categoryId=dev-lobby-two`: 14 карточек `dev-lobby-two-01` … `14`, `startsAt` = `2090-03-02T00:00:00Z + N минут`.
- `GET /v1/feed/candidates?kind=PLACE&categoryId=dev-swipe-places` и `kind=EVENT&categoryId=dev-swipe-events`: по 22 уникальные карточки; у событий первая страница 20 и курсор, вторая — 2. Одиночная выдача по-прежнему отдаёт страницы по 20.
- `GET /v1/events`: `200`, афиша доступна через Nginx.
- Идентификаторы `userId` участников 1–10 после повторного запуска Compose совпали с первым запуском.
- Все проверки обоих прогонов завершились без ошибок.

Контроль данных в PostgreSQL каталога после двух запусков:

```text
dev-lobby-a       14 строк, 14 уникальных id
dev-lobby-b       13 строк, 13 уникальных id
dev-lobby-c        8 строк,  8 уникальных id
dev-lobby-short    4 строки,  4 уникальных id
dev-lobby-two     14 строк, 14 уникальных id
категории dev-lobby-*: 5
dev-swipe-events  22 строки, 22 уникальных id
dev-swipe-places  22 строки, 22 уникальных id
```

Порты стенда: опубликован только `127.0.0.1:18090->80/tcp` (Nginx). PostgreSQL, Redis и Kafka имеют только внутренние порты Compose и наружу не публикуются.

Остановка без удаления томов:

```sh
docker compose -p srastemsya_l01 -f compose.yaml -f compose.dev.yaml down
# контейнеры и сеть удалены, тома srastemsya_l01_* сохранены
```

## Ограничения

- Отдельная сборка предыдущего пакета для L01-01 не поднималась: стабильность `userId` проверена повторным запуском новой сборки поверх сохранённых томов. Идентификаторы dev-участников детерминированы, а вставка идемпотентна по контакту, поэтому тома прежней сборки сохраняют ID участников 1–5.
- Пакеты BE-L02 … BE-L07 не реализовывались: пул комнаты остаётся прежним, порог, срок раунда, веса и итог по баллам не менялись.
- Посторонний для проверки изоляции комнат — существующий dev-контакт `new@example.test`, описанный в README. Он не входит в десятку участников; профиль завершается документированным `PUT /v1/me/registration`.

## Публичные документы

- [Спецификация комнаты v2](../../docs/specs/lobby-v2/README.md)
- [BE-L01 в спецификации разработки](../../docs/specs/lobby-v2/implementation.md#be-l01--стендовые-данные)
- [Приёмка комнаты v2](../../docs/specs/lobby-v2/acceptance.md#be-l01--стендовые-данные)
- [Контракт комнаты v2](../../docs/contracts/lobby-v2.md)
- [Контракт Discovery v1](../../docs/contracts/discovery-v1.md)
- [Мобильный HTTP-контракт](../../docs/contracts/mobile-api.md)
- [README бэкенда: dev-данные комнаты BE-L01](../../backend/README.md#стендовые-данные-комнаты-be-l01)
- Критерии приёмки PM: `reports/BE-L01/acceptance.md`
- Пакет для тестировщика: `reports/BE-L01/test_packet.md`
