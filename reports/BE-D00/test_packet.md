# BE-D00 · публичный стенд

- [Инструкции запуска, fixture-контакты, адреса, сценарий базовой конфигурации](../../backend/README.md)
- [Discovery v1](../../docs/contracts/discovery-v1.md), [мобильный контракт](../../docs/contracts/mobile-api.md)
- Запуск из backend. Изолированное имя проекта и свободный порт задаются командами `NGINX_PORT=18081 docker compose -p srastemsya-d00-test -f compose.yaml -f compose.dev.yaml up --build -d --wait`. Основной URL в этом варианте — http://127.0.0.1:18081. Порт 8080 занят другим проектом.
- Публичные endpoints готовности: /identity/health, /catalog/health, /swipes/health. Доступность Redis и баз для испытания проверяется через CLI Compose с изолированным именем проекта.
- Контакты с заполненным профилем: person1@example.test … person5@example.test. Новая регистрация: new@example.test или +15550100100. Для повторного challenge одного контакта предусмотрено 60 секунд.
- BE-D00 fixtures: GET /v1/home и GET /v1/rooms. Контракт и текущая область указаны в README.
- Build identity: base be714aa, uncommitted BE-D00 tree, capture actual image IDs with Docker Compose `images -q` for the isolated project.

- Round 1 candidate: developer image config ID `3e1ee132027df35f84be173c8c0bcc00412104f66acd7994b8d0b94fab8c42eb`. Rebuild the isolated tester project with the documented command and record its image IDs.
