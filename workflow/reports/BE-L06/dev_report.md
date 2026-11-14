# BE-L06 Developer

Кандидат `691b00643525f01c528592e8c68f18a36e294103` в `be-l06`, база BE-L05 `40646e999fe679de330b2ab623e641f3bc310511`. Образ локальной проверки `srastemsya_l06_developer-runtime:local`, собран Compose из кандидата.

При исчерпании кандидатов swipes выбирает победителя по сохранённым итогам завершённых раундов. При равном максимуме сохраняется порядок раундов и карточек. При нуле лайков или пустом старте возвращается `EXHAUSTED`. Код и четыре обновления документации входят в один коммит.

## Проверки

- `sh backend/services/swipes/tests/run.sh` — 10 passed, 0 failed, 0 skipped. [Отчёт запуска](../../../backend/services/swipes/tests/reports/20261113T062028Z-25757.md).
- `git diff --check` — без ошибок.
- Из каталога `backend`: `NGINX_PORT=18196 docker compose -p srastemsya_l06_developer -f compose.yaml -f compose.dev.yaml up --build -d --wait` — запуск на чистом проекте и повторный запуск успешны. `curl -fsi http://127.0.0.1:18196/swipes/health` — HTTP 200. Для доступа к Docker и loopback потребовался запуск вне песочницы.
- HTTP-проверка через Nginx: три участника, `dev-lobby-two`, карточки 03 и 12 получили по два лайка. Все участники увидели `MATCHED`, `round=null`, победителя `dev-lobby-two-03`, `basis=TOP_SCORE`, `likes=2`, `memberCount=3`.
- Повторный запуск завершился успешным readiness. Отдельная проверка количества записей после повтора входит в независимую приёмку. Стенд Developer остановлен через `docker compose -p srastemsya_l06_developer -f compose.yaml -f compose.dev.yaml down` без удаления томов.

## Архитектура

Изменение выполняется в существующей транзакции финализации. Чтение строки комнаты блокируется через `FOR UPDATE`, результат и версия записываются вместе в PostgreSQL swipes, уведомление Redis публикуется после выхода из контекста транзакции. Новый внешний вызов, SQL к чужим БД, изменения JWT, служебных маршрутов, Redis, Kafka и Compose отсутствуют. Проверка конкуренции, повторов, long polling и регрессии прошлых пакетов остаётся за независимым Tester. Проверка production-политик браузерных сессий и runtime heal за рамками пакета.

[Swipes](../../../docs/services/swipes.md) · [Discovery v1](../../../docs/contracts/discovery-v1.md#свайпы-в-комнате) · [BE-04](../../../docs/specs/backend.md#be-04--подборки-и-комнаты) · [Mobile HTTP](../../../docs/contracts/mobile-api.md#be-04--подборка-и-комната)
