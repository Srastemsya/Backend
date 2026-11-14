# BE-L04 · Тестовый пакет

- Ревизия: `3b026cf16a17248831c8106549236a27ec254952`.
- Dev-стенд: `http://127.0.0.1:18094`, готовность `/swipes/health`, API `/v1`.
- Запуск из `/tmp/be-l04/backend`: `NGINX_PORT=18094 docker compose -p srastemsya_l04 -f compose.yaml -f compose.dev.yaml up --build -d --wait`.
- Перезапуск swipes из того же каталога: `NGINX_PORT=18094 docker compose -p srastemsya_l04 -f compose.yaml -f compose.dev.yaml restart swipes`.
- [Стендовые участники, данные и заголовок X-Dev-Swipes-Now](../../../backend/README.md).
- [Контракт комнаты v2](../../../docs/contracts/lobby-v2.md) · [Discovery v1](../../../docs/contracts/discovery-v1.md) · [мобильный API](../../../docs/contracts/mobile-api.md).
