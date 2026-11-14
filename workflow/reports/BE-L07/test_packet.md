# BE-L07 · Пакет проверки

Ревизия `6e25b89dcdb178d2bff3bfcd764ee861fe3e4a8b`. Для сквозного сценария и регрессии используйте одну сборку с этой ревизии и новый Compose-проект с собственными томами.

```sh
git rev-parse HEAD
cd backend
NGINX_PORT=18098 docker compose -p srastemsya_l07_test -f compose.yaml -f compose.dev.yaml up --build -d --wait
curl -fsS http://127.0.0.1:18098/swipes/health
docker compose -p srastemsya_l07_test -f compose.yaml -f compose.dev.yaml images
```

Публичный API через Nginx: `http://127.0.0.1:18098/v1`. Для проверки перезапуска доступна команда `docker compose -p srastemsya_l07_test -f compose.yaml -f compose.dev.yaml restart swipes`. Остановка проекта: `docker compose -p srastemsya_l07_test -f compose.yaml -f compose.dev.yaml down`.

- [Регистрация аккаунта](../../../docs/contracts/mobile-api.md#be-01--вход-и-сессия) — `POST /auth/challenges`, `POST /auth/challenges/{id}/verify`, `PUT /me/registration` с новым стендовым адресом.
- [Публикация и запись](../../../docs/contracts/mobile-api.md#be-0203--каталог-события-и-запись) — `POST /events`, `GET /events/{id}`, `POST /events/{id}/registrations`. Для записи на последнее место доступны события типа `REGISTRATION` с вместимостью 1.
- [Одиночная выдача и комнаты](../../../docs/contracts/mobile-api.md#be-04--подборка-и-комната) — `GET /feed/candidates`, `POST /rooms`, `POST /rooms/{id}/invites`, `POST /room-invites/join`, `POST /rooms/{id}/start`, PUT голосов и завершения. [Долгий опрос](../../../docs/contracts/discovery-v1.md#long-polling-комнаты-и-приглашения) — `GET /rooms/{id}?afterVersion=<version>&waitSeconds=25`.
- [Контракт комнаты v2](../../../docs/contracts/lobby-v2.md) и [стендовые данные комнаты](../../../backend/README.md#стендовые-данные-комнаты-be-l01) — участники `person1@example.test` … `person10@example.test`, наборы `dev-lobby-mix`, `dev-lobby-short`, `dev-lobby-two`. Порядок входа и тестовый код описаны в README.
- [Документированные часы стенда](../../../backend/README.md) — `X-Dev-Swipes-Now` принимает RFC 3339 timestamp на dev-запросах, `X-Dev-Catalog-Now` переопределяет время фильтра каталога, identity использует собственные часы.
