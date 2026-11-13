# BE-L03 · Пакет для тестировщика

Ревизия кода и документации — `6d456374003f0e72c897699fb1214ed142628769`. Рабочая сборка из `/private/tmp/be-l03`, ветка `be-l03`, база `484d87b`. Идентификатор конфигурации проверенного контейнера swipes — `sha256:4e1b918149788a459c368ce68dbe72cb073bd6aa58723ea64aa6688880e339f9`.

Из каталога `backend`:

```sh
NGINX_PORT=18943 docker compose -p srastemsya_l03 -f compose.yaml -f compose.dev.yaml up --build -d --wait
curl -i http://127.0.0.1:18943/swipes/health
NGINX_PORT=18943 docker compose -p srastemsya_l03 -f compose.yaml -f compose.dev.yaml down
```

- Базовый URL через Nginx — `http://127.0.0.1:18943`.
- Участники — `person1@example.test` … `person10@example.test` с завершёнными профилями. Вход через `POST /v1/auth/challenges` и `POST /v1/auth/challenges/{challengeId}/verify`. Параметры входа и управление dev OTP описаны в README бэкенда.
- Наборы — `dev-lobby-two`, `dev-lobby-short`, `dev-swipe-events`, `dev-swipe-places` и смешанные события на `2090-02-01`. Состав и фильтры перечислены в README бэкенда.
- Dev-время — заголовок `X-Dev-Swipes-Now` в RFC 3339.

[README бэкенда](../../backend/README.md) · [Маршруты swipes](../../docs/services/swipes.md) · [Контракт комнаты v2](../../docs/contracts/lobby-v2.md) · [Discovery v1](../../docs/contracts/discovery-v1.md) · [Мобильный HTTP-контракт](../../docs/contracts/mobile-api.md#be-04--подборка-и-комната)
