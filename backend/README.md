# Бэкенд Discovery v1

В каталоге backend запустите Docker Compose.

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build -d --wait
```

Nginx публикует HTTP на 127.0.0.1:8080. На Android Emulator используйте http://10.0.2.2:8080, в iOS Simulator используйте http://127.0.0.1:8080. PostgreSQL, Redis и Kafka доступны в сети Compose. Каждый сервис использует отдельный PostgreSQL. Повторный запуск сохраняет записи и применяет миграции и dev-данные без дублей. Остановка с сохранением данных выполняется командой `docker compose -f compose.yaml -f compose.dev.yaml down`.

В dev используйте существующие `person1@example.test` … `person5@example.test`, а для новой регистрации `new@example.test` и `+15550100100`. Код по умолчанию — `0427`. Укажите `DEV_OTP`, чтобы заменить его четырьмя цифрами. Между отправками кода на один контакт выдержите 60 секунд.

Проверки готовности через Nginx доступны по `/identity/health`, `/catalog/health` и `/swipes/health`. Профиль завершённого пользователя открывает пустые ответы `GET /v1/home` и `GET /v1/rooms` для проверки доступа в BE-D00. Бизнес-данные каталога и комнат входят в следующие пакеты.

Для локальной конфигурации возьмите `.env.example`. Базовый Compose запускается с выключенным mock OTP. Запуск identity вне dev с `MOCK_OTP=true` завершается ошибкой. Сервисы проверяют JWT отдельным публичным ключом, доступ к подписи есть только у identity. Admin UI каждого сервиса доступен на `/<service>/admin` с отдельным Bearer JWT (HS256, аудитория `srastemsya-admin`, срок `exp`, ключ `ADMIN_JWT_KEY`).

Запускайте `scripts/heal-compose-runtime.sh` каждые 30–60 секунд системным таймером из того же проекта Compose. Для dev установите `SR_ALWAYS_DEV=1` в окружении таймера. Скрипт пересоздаёт приложение с ограничением частоты и сохраняет тома.

[Мобильный HTTP-контракт](../docs/contracts/mobile-api.md) · [Контракт Discovery v1](../docs/contracts/discovery-v1.md).

Если порт 8080 занят, задайте `NGINX_PORT` перед командой запуска. Для проверки отказа mock OTP используйте отдельное имя проекта и базовую конфигурацию, например `APP_ENV=production MOCK_OTP=true docker compose -p srastemsya-mock-check -f compose.yaml up -d --build --wait identity`.
