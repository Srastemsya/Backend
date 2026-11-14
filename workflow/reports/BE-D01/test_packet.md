# BE-D01 · Стенд

- Базовая ревизия `1c336da`, образ запущенного catalog `sha256:909195b301d5dbd268e5b24d6e135863b5da81a9ddda35a115bcf5941b68cd21`.
- Шлюз `http://127.0.0.1:18082`, версия API `/v1`, готовность `/catalog/health`.
- Проект Compose `srastemsya-be-d01` в каталоге `backend`. Команда запуска `NGINX_PORT=18082 docker compose -p srastemsya-be-d01 -f compose.yaml -f compose.dev.yaml up --build -d --wait`.
- [Контракт Discovery v1](../../../docs/contracts/discovery-v1.md), [мобильный HTTP-контракт](../../../docs/contracts/mobile-api.md), [доступ к синтетическим данным](../../../backend/README.md#стендовый-каталог-be-d01).

## Варианты тестовых данных

- `http://127.0.0.1:18082` — вариант без опубликованных объектов. Используйте штатную dev-авторизацию и `GET /v1/home`. Идентификатор образа указан выше.
- `http://127.0.0.1:18083` — основной стенд Tester с обычными dev-данными. Для сценария с более чем 20 совпадениями используйте `GET /v1/catalog/search?kind=EVENT&categoryId=outdoors`. Идентификатор сборки этого стенда фиксирует Tester.
- После проверки пустого варианта на 18082 восстановлены обычные dev-данные. Для чтения курсоров использованы `GET /v1/catalog/search?kind=EVENT&categoryId=outdoors` и `GET /v1/catalog/map?kind=EVENT&bbox=131.87,43.10,131.91,43.13`. Для двух выделенных курсоров выполнено контролируемое сокращение срока действия. Образ catalog тот же, что указан выше.
