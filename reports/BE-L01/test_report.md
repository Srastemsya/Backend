# BE-L01 · Отчёт независимого Tester

**Итог: PASS.** Все обязательные AC-01…AC-08 фактически проверены через Nginx; провалов нет.
Критерии: `reports/BE-L01/acceptance.md`. Стенд по `reports/BE-L01/test_packet.md`.
Исходники приложения не читались; проверки — публичный HTTP и метаданные процессов Compose.

## Ревизия и сборка

- Ветка `be-l01`, HEAD `96a4965` (код и документы `6edf059`, база `dev` `c7fb434`);
  отчётные коммиты сборку не меняют.
- Локально собранный образ основного стенда:
  `srastemsya_l01_accept-runtime:local` `sha256:6d02a9ec285dcb4b2b78b197caf086bc5f7dae930ed71b282ab16e266c142ba9`.
- Чистый стенд INT-00: `srastemsya_l01_clean-runtime:local`
  `sha256:673e0f7b1677425228dd82b2fe415b9076156de18299cc3cc69e54ffb1444e45`.
- Основной стенд: проект `srastemsya_l01_accept`, `127.0.0.1:18093`, путь «прежняя сборка
  (`c7fb434`) на чистых томах → be-l01 на тех же томах». Чистый: `srastemsya_l01_clean`,
  `127.0.0.1:18094`. Управляемое время — `X-Dev-Swipes-Now` / `X-Dev-Catalog-Now`.

## Маппинг AC → тесты и фактические результаты

Основной прогон: `backend/tests/reports/20261113T022245Z-4473-be-l01.md` — 8/8, exit 0.
Дополнительный INT-00 на чистом проекте:
`backend/tests/reports/20261113T022439Z-4649-be-l01.md` — 3/3, exit 0.

| AC | Тест | Результат |
|---|---|---|
| AC-01 | `test_ac01_login_participants_and_stable_ids` | PASS: person6…person10 входят, профили завершены, каталог/афиша/подборка/комнаты доступны; `userId` person1…person5 совпали со снимком прежней сборки на тех же томах |
| AC-02 | `test_ac02_mixed_set` | PASS: 2 страницы, ровно 35 карточек `dev-lobby-mix-01…35` по возрастанию; начало `2090-02-01T00:00:00Z + N мин`; цена 1000; категории по таблице BE-L01; дублей нет |
| AC-03 | `test_ac03_short_and_two_sets` | PASS: `dev-lobby-short` — 4 карточки, `dev-lobby-two` — 14, по возрастанию; начало `2090-03-01/02T00:00:00Z + N мин` |
| AC-04 | `test_ac04_idempotent_restart_and_int00` + `be_l01_int00.py` | PASS: повторный Compose без дублей (mix 35, short 4, two 14, swipe-events 22, swipe-places 22); health 200; регистрация, афиша, комнаты через Nginx; PostgreSQL/Redis/Kafka портов не публикуют, Nginx только loopback. INT-00 повторён на чистом проекте |
| AC-05 | `test_ac05_readme_documents_sets_and_links` | PASS: раздел README описывает person6…person10, три набора (ID, категории, даты, фильтры), таблицу категорий; локальные ссылки/якоря разрешаются, внешние ссылки отвечают 200 |
| AC-06 | `test_ac06_public_api_unchanged` | PASS: 401 `UNAUTHENTICATED`, 403 `PROFILE_INCOMPLETE` и регистрация, выдача 20 + курсор → 2 без повторов, повтор курсора идемпотентен, 409 `CURSOR_EXPIRED`, идемпотентность комнаты и 409 `IDEMPOTENCY_CONFLICT`, 410 `INVITE_EXPIRED`, long polling доставляет новую версию без токена приглашения |
| AC-07 | `test_ac07_existing_dev_data_and_single_room_pass` | PASS: `dev-swipe-*` (22+22, цены 1000/500/null, даты) и `dev-vlad-*` не изменены, черновик скрыт; одиночный проход комнаты на прежнем наборе как в Discovery v1: пул 20, 409 `INVALID_STATE`, замена голоса, следующий раунд 2 карточки, 409 `STALE_ROUND`, затем `EXHAUSTED`, `round=null`, `result=null` |
| AC-08 | `test_ac08_outsider_available_for_isolation` | PASS: `new@example.test` регистрируется, видит каталог, создаёт комнату; приватные комнаты недоступны постороннему в обе стороны (404) |

Дополнительно проверены негативные/граничные случаи: неверные и повторные запросы
идемпотентности, истёкшие курсор и приглашение, голос в старый раунд, неполный проход,
скрытый черновик, дубли в выдачах.

## Сырые доказательства и review

- `backend/tests/reports/20261113T022245Z-4473-be-l01.md` — основной прогон AC-01…AC-08.
- `backend/tests/reports/20261113T022439Z-4649-be-l01.md` — INT-00 на чистом проекте.
- `backend/tests/reports/20261113T022219Z-4409-be-l01-prev-ids.json` — `userId`/`profileId`
  person1…person5, снятые с прежней сборки до обновления.
- `backend/tests/reviews/20261113T022517Z.md` — оценка покрытия, пробелы, замечания.
- Сохранённые ранние артефакты: `20261113T021810Z-3825-be-l01.md` (черновой прогон с
  дефектами самого теста, заменён финальным) и `20261113T021438Z-3474-be-l01-prev-ids.json`.

## Воспроизведение

```sh
# 1. Прежняя сборка на изолированном проекте
git archive c7fb434 backend | tar -x -C <prev-dir>
cd <prev-dir>/backend
NGINX_PORT=18093 docker compose -p srastemsya_l01_accept \
  -f compose.yaml -f compose.dev.yaml up --build -d --wait
cd <be-l01>/backend/tests
python3 be_l01_prev_capture.py http://127.0.0.1:18093 \
  reports/$(date -u +%Y%m%dT%H%M%SZ)-be-l01-prev-ids.json

# 2. Проверяемая сборка на тех же томах
cd <be-l01>/backend
NGINX_PORT=18093 docker compose -p srastemsya_l01_accept \
  -f compose.yaml -f compose.dev.yaml up --build -d --wait

# 3. Приёмка: run.sh повторяет Compose и пишет timestamped-отчёт
cd tests
BE_L01_COMPOSE_PROJECT=srastemsya_l01_accept BE_L01_NGINX_PORT=18093 \
  BE_L01_BASE_URL=http://127.0.0.1:18093 ./run-be-l01.sh

# 4. Чистый INT-00
cd <be-l01>/backend
NGINX_PORT=18094 docker compose -p srastemsya_l01_clean \
  -f compose.yaml -f compose.dev.yaml up --build -d --wait
cd tests
BE_L01_COMPOSE_PROJECT=srastemsya_l01_clean BE_L01_NGINX_PORT=18094 \
  BE_L01_BASE_URL=http://127.0.0.1:18094 ./run-be-l01.sh python3 be_l01_int00.py
```

`run-be-l01.sh` сам берёт последний `reports/*-be-l01-prev-ids.json`; повторный запуск
без пересоздания томов использует сохранённые данные. Тесты не изменяют реализацию.

## Ограничения

- Применение миграций проверено поведенчески (готовность и ожидаемые данные через API),
  без чтения служебных таблиц БД.
- Локальный digest образа отличается от указанного в `test_packet.md` — сборка выполнена
  локально из коммита `6edf059`/HEAD `96a4965`.
- UUID участников 1–5 детерминированы сидом dev-данных; AC-01 проверен сравнением со
  снимком прежней сборки на тех же томах.

## Аттестация финальной ревизии

Ревизия `b42079d` (`git diff --stat 3af1cbe..b42079d`: добавлен только
`reports/BE-L01/pm_handoff.md`, +14 строк; производственный код и документация
от `6edf059` не менялись). Результаты AC-01…AC-08, полученные на сборке `6edf059`,
действительны для `b42079d`. Аттестовано 2026-11-13.
