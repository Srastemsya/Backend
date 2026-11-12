# Бэкенд Discovery v1

В каталоге backend запустите Docker Compose.

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build -d --wait
```

Nginx публикует HTTP на 127.0.0.1:8080. На Android Emulator используйте http://10.0.2.2:8080, в iOS Simulator используйте http://127.0.0.1:8080. PostgreSQL, Redis и Kafka доступны в сети Compose. Каждый сервис использует отдельный PostgreSQL. Повторный запуск сохраняет записи и применяет миграции и dev-данные без дублей. Остановка с сохранением данных выполняется командой `docker compose -f compose.yaml -f compose.dev.yaml down`.

В dev используйте существующие `person1@example.test` … `person5@example.test`, а для новой регистрации `new@example.test` и `+15550100100`. Код по умолчанию — `0427`. Укажите `DEV_OTP`, чтобы заменить его четырьмя цифрами. Между отправками кода на один контакт выдержите 60 секунд.

Проверки готовности через Nginx доступны по `/identity/health`, `/catalog/health` и `/swipes/health`. С завершённым профилем доступны открытия и каталог. `GET /v1/rooms` возвращает пустой список до реализации комнат.

## Стендовый каталог BE-D01

В dev загружаются категории, подборки и объекты Владивостока. Первая подборка `culture-events` содержит события категории `culture`. В точках с долготой 131.87–131.91 и широтой 43.10–43.13 доступны события обоих режимов входа, места и активность. Для чтения можно использовать идентификаторы `dev-vlad-exhibit`, `dev-vlad-workshop`, `dev-vlad-museum` и `dev-vlad-walk`. Черновик `dev-vlad-draft` предназначен для проверки видимости. При первом запуске время начала рассчитывается относительно времени загрузки данных и сохраняется в томе. На чистом стенде `person1@example.test` — организатор, `person2@example.test` имеет подтверждённую запись на мастер-класс. Существующие ID аккаунтов на томах BE-D00 сохраняются при обновлении.

Catalog владеет PostgreSQL с категориями, подборками, объектами, записями и сохранениями. Redis хранит метаданные с TTL 5 минут и курсоры с TTL 30 минут. Ревизия в PostgreSQL меняется транзакционно вместе с каталогом, поэтому после изменения категории, подборки или опубликованности чтения используют новый ключ метаданных. Текущая вместимость и поля зрителя читаются из PostgreSQL. Публикация и изменения записи добавляют сообщение в outbox каталога. См. [контракт интеграции и Kafka](../docs/contracts/catalog-integration.md).

Для локальной конфигурации возьмите `.env.example`. Базовый Compose запускается с выключенным mock OTP. Запуск identity вне dev с `MOCK_OTP=true` завершается ошибкой. Сервисы проверяют JWT отдельным публичным ключом, доступ к подписи есть только у identity. Admin UI каждого сервиса доступен на `/<service>/admin` с отдельным Bearer JWT (HS256, аудитория `srastemsya-admin`, срок `exp`, ключ `ADMIN_JWT_KEY`).

Запускайте `scripts/heal-compose-runtime.sh` каждые 30–60 секунд системным таймером из того же проекта Compose. Для dev установите `SR_ALWAYS_DEV=1` в окружении таймера. Скрипт пересоздаёт приложение с ограничением частоты и сохраняет тома.

[Мобильный HTTP-контракт](../docs/contracts/mobile-api.md) · [Контракт Discovery v1](../docs/contracts/discovery-v1.md).

Если порт 8080 занят, задайте `NGINX_PORT` перед командой запуска. Для проверки отказа mock OTP используйте отдельное имя проекта и базовую конфигурацию, например `APP_ENV=production MOCK_OTP=true docker compose -p srastemsya-mock-check -f compose.yaml up -d --build --wait identity`.


## Стендовые обложки и часы BE-D02

В dev синтетические идентификаторы `dev-event-cover-person1` и `dev-event-cover-person2` принадлежат соответственно `person1@example.test` и `person2@example.test`. Обе обложки имеют тип `EVENT_COVER` и статус `READY`. `dev-event-cover-pending` и `dev-event-cover-wrong-purpose` принадлежат первому аккаунту и проверяют статус и назначение. URL с доменом `media.example.test` служат синтетическими значениями DTO. Протокол реальной загрузки подключается в BE-05.

Для проверки границ времени отправьте `X-Dev-Catalog-Now: <RFC 3339 timestamp>` в запросе афиши, публикации, деталей, записи, снятия или внутреннего снимка. Время применяется только к конкретному запросу в `APP_ENV=dev`. В других окружениях сервер использует собственные часы. Токены и срок сессии всегда используют собственные часы identity.

Афиша и список активных записей используют курсор на 30 минут. Успешные ответы идемпотентных операций хранятся в базе каталога и переживают перезапуск. Для изменений регистрации API проверяет актуальное состояние, если клиент отправляет новый ключ.

Для проверки снимка запустите запрос из контейнера swipes в сети Compose. В переменной `ACCESS_TOKEN` используйте токен dev-аккаунта с завершённым профилем.

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec -T -e ACCESS_TOKEN swipes python -c '
import os
from urllib.request import Request, urlopen
request = Request("http://catalog:8000/internal/catalog/candidates?kind=EVENT",
                  headers={"Authorization": "Bearer " + os.environ["ACCESS_TOKEN"]})
print(urlopen(request).read().decode())
'
```

Просмотр опубликованных сообщений Kafka из сети Compose.

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 --topic catalog.changed.v1 --from-beginning --timeout-ms 5000
```

Проверки разработчика на изолированном dev-стенде запускаются командой `D02_PROJECT=<проект> tests/run-be-d02-architecture.sh` из каталога backend. Проверка создаёт синтетические события и сообщения Kafka в этом проекте.
