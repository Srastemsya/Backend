# Срастёмся · локальный бэкенд для фронтенда

Установите Docker Desktop или Docker Engine с Compose v2. Распакуйте архив, откройте терминал в распакованной папке и запустите:

```sh
cd backend
docker compose -f compose.yaml -f compose.dev.yaml up --build -d --wait
```

Первый запуск скачает образы и зависимости. GitHub и отдельный файл .env для запуска не нужны. Если порт 8080 занят, добавьте перед командой `NGINX_PORT=18090` и используйте этот порт во всех адресах ниже.

| Клиент | Базовый URL API |
|---|---|
| Этот компьютер, iOS Simulator | `http://127.0.0.1:8080` |
| Android Emulator | `http://10.0.2.2:8080` |
| Android по USB с `adb reverse tcp:8080 tcp:8080` | `http://127.0.0.1:8080` |

Локальный API использует HTTP. Для debug-сборки разрешите cleartext к этому адресу, если платформа его блокирует.

## Вход и карточки

1. Войдите как `person1@example.test` или `person2@example.test`. Dev-код — `0427`. Оба профиля уже заполнены. Для теста регистрации используйте новый email.
2. Для входа через HTTP вызовите `POST /v1/auth/challenges` с JSON `{"channel":"EMAIL","destination":"person1@example.test"}`, затем `POST /v1/auth/challenges/{challengeId}/verify` с JSON `{"code":"0427"}`. Для каждого POST передайте свой `Idempotency-Key`. В дальнейших запросах передавайте `Authorization: Bearer <accessToken>`.
3. Откройте `GET /v1/home`, `GET /v1/events` или `GET /v1/feed/candidates?kind=EVENT`. Чистый стенд автоматически заполняется событиями Владивостока, местами и активностями. Есть бесплатные события и мастер-класс с записью. Для пагинации и комнат используйте категорию `dev-swipe-events` с 22 карточками.
4. Отображайте `cover.url` в карточке. Для локальных фото это путь от корня API, например `/dev-media/gallery.jpg`. Соберите URL относительно настроенного origin API. Фото лежат в архиве и отдаются Nginx без авторизации. Это синтетические фотографии для моков, несколько карточек могут использовать одну обложку.

Проверка готовности:

```sh
curl -fsS http://127.0.0.1:8080/identity/health
curl -fsS http://127.0.0.1:8080/catalog/health
curl -fsS http://127.0.0.1:8080/swipes/health
```

Остановка с сохранением базы и сессий:

```sh
docker compose -f compose.yaml -f compose.dev.yaml down
```

[Контракт Discovery v1](docs/contracts/discovery-v1.md) · [Общий мобильный контракт](docs/contracts/mobile-api.md) · [Дополнительная документация бэкенда](backend/README.md)

[Справочник по сервисам и маршрутам](docs/services/README.md).
