# Бэкенд Discovery v1

В каталоге backend запустите Docker Compose.

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build -d --wait
```

Nginx публикует HTTP на 127.0.0.1:8080. На Android Emulator используйте http://10.0.2.2:8080, в iOS Simulator используйте http://127.0.0.1:8080. PostgreSQL, Redis и Kafka доступны в сети Compose. Каждый сервис использует отдельный PostgreSQL. Повторный запуск сохраняет записи и применяет миграции и dev-данные без дублей. Остановка с сохранением данных выполняется командой `docker compose -f compose.yaml -f compose.dev.yaml down`.

В dev используйте существующие `person1@example.test` … `person5@example.test`, а для новой регистрации `new@example.test` и `+15550100100`. Код по умолчанию — `0427`. Укажите `DEV_OTP`, чтобы заменить его четырьмя цифрами. Между отправками кода на один контакт выдержите 60 секунд.

Проверки готовности через Nginx доступны по `/identity/health`, `/catalog/health` и `/swipes/health`. С завершённым профилем доступны каталог, подборка кандидатов и комнаты.

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


## Подборка и комнаты BE-D03

Подборка `GET /v1/feed/candidates` и комнаты доступны через Nginx. Для комнаты создайте её через `POST /v1/rooms`, выпустите приглашение через `POST /v1/rooms/{id}/invites` и передайте параметр `token` из URL в тело `POST /v1/room-invites/join`. Ожидание изменений начинается с `GET /v1/rooms/{id}?afterVersion=<version>&waitSeconds=25`. Маршруты и статусы описаны в [контракте Discovery v1](../docs/contracts/discovery-v1.md#свайпы-в-комнате).

Для проверки используйте два набора по 22 карточки в категориях `dev-swipe-places` и `dev-swipe-events`. ID идут от `dev-swipe-place-01` до `dev-swipe-place-22` и от `dev-swipe-event-01` до `dev-swipe-event-22`. Цена на человека в копейках RUB равна 1000 для карточек 01–20 и 500 для карточки 21. У карточки 22 цена неизвестна. События начинаются 2 января 2090 года в 00:01–00:22 UTC. Для стартового пустого пула задайте бюджет 0 в одной из этих категорий.

Заголовок `X-Dev-Swipes-Now` принимает RFC 3339 timestamp и задаёт время конкретного запроса в dev. Создайте выдачу либо запустите раунд с временем `2089-01-01T00:00:00Z`, затем прочитайте курсор либо комнату с временем `2089-01-01T00:30:00Z` для проверки истечения срока. Тот же заголовок позволяет проверить срок приглашения. Запросы подбора передают эти часы в catalog. При наличии `X-Dev-Catalog-Now` время для фильтра каталога задаёт этот заголовок. Identity проверяет сессию по собственным часам. Вне dev часы задаёт сервер.

Swipes хранит снимки выдачи, комнаты и повторяемые ответы POST в своей PostgreSQL. Новые снимки пула читаются из catalog, имена новых участников читаются из identity. Обновления версии комнаты после commit передаются через Redis Pub/Sub. PostgreSQL остаётся источником состояния для повторного чтения. Подробности см. в [контракте внутренней интеграции](../docs/contracts/catalog-integration.md).

[Справочник по сервисам и маршрутам](../docs/services/README.md).

## GitHub Actions и стенды мероприятия

| Событие | Проверки и сборка | Деплой на сервер |
| --- | --- | --- |
| PR в `dev` или `main` | Сборка Docker-образа и проверка readiness трёх сервисов | — |
| Push в `dev` | Повторная сборка и readiness | `srastemsya-staging` на `127.0.0.1:18080` |
| Push в `main`, включая merge PR | Новая сборка из коммита `main` и readiness | `srastemsya-demo` на `127.0.0.1:8080` |

Обе копии используют `compose.dev.yaml` с mock OTP и демоданными.
У них отдельные контейнеры, сети, базы, тома и серверные настройки.
Actions передаёт собранный образ через SSH. Сервер импортирует образ и запускает
Compose с `--no-build`. Обновление сохраняет тома и проверяет readiness после запуска.

### Подключение сервера

1. На Linux x86-64 подготовьте Docker Engine, актуальный Docker Compose,
   Bash, curl и пользователя SSH с доступом к Docker. Убедитесь, что порты
   8080 и 18080 свободны и GitHub-hosted runner может подключиться по SSH.
2. В GitHub создайте Environments `staging` и `demo`. Ограничьте деплой
   ветками `dev` и `main` соответственно. Для обоих задайте variables
   `SSH_HOST`, `SSH_USER` и при необходимости `SSH_PORT`. Добавьте secrets
   `SSH_PRIVATE_KEY` (отдельный ключ автоматизации для CI) и `SSH_KNOWN_HOSTS`
   (проверенная запись публичного host key сервера). Публичный ключ CI
   добавьте в `authorized_keys` пользователя деплоя.
3. В домашнем каталоге этого пользователя создайте
   `~/srastemsya/staging/.env` и `~/srastemsya/demo/.env` с правами `0600`.
   В каждом задайте отдельные случайные URL-safe значения
   `IDENTITY_DB_PASSWORD`, `CATALOG_DB_PASSWORD` и `SWIPES_DB_PASSWORD`.
   При необходимости задайте `DEV_OTP`. После первой инициализации томов
   смена паролей в env-файле требует соответствующей смены паролей в PostgreSQL.
4. Добавьте в каждом GitHub Environment secret `API_DOMAIN` со своим
   DNS-именем в нижнем регистре, без схемы и порта. Оба имени должны указывать
   на сервер. Откройте входящие 80 и 443 для HTTP-01 и HTTPS. На сервере
   установите Nginx, Certbot с плагином Nginx и `flock`. Включите Nginx
   и автоматическое продление сертификатов Certbot через пакетный таймер.

5. Администратор сервера один раз устанавливает проверенную копию скрипта
   из `backend/` и разрешает пользователю деплоя запуск именно этого файла
   через `sudo -n`. Файл должен оставаться доступным для записи только root.

   ```sh
   sudo install -o root -g root -m 0755 scripts/configure-https.sh /usr/local/sbin/srastemsya-configure-https
   sudo visudo -f /etc/sudoers.d/srastemsya-https
   ```

   Строка для sudoers, где `DEPLOY_USER` нужно заменить именем пользователя:

   ```text
   DEPLOY_USER ALL=(root) NOPASSWD: /usr/local/sbin/srastemsya-configure-https
   ```

6. После первого push workflow настроит отдельный виртуальный хост для
   окружения, запросит сертификат, включит редирект на HTTPS и проверит
   готовность сервисов через публичный домен. Nginx на сервере проксирует
   в контейнеры на localhost. После настройки обоих стендов проверьте
   продление командой `sudo certbot renew --dry-run`. При смене домена
   администратор сначала корректирует существующий виртуальный хост.

Оба стенда принимают mock OTP. Используйте только демонстрационные данные.

[GitHub Actions Environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments) · [Certbot для Nginx](https://certbot.eff.org/instructions?ws=nginx&os=debiantesting)
