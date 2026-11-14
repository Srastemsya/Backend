# BE-D02 · Пакет для независимой проверки

- Кандидат `74887588ffc1da7c751569f7273b81660e648d2b`, ветка `be-d02`. Сборка catalog на стенде разработчика `sha256:ce890df6bd30c35cd200181bd885f9509ce4c53bac9aa4a99071a2a7ca38e5bd`.
- [Контракт Discovery v1](../../../docs/contracts/discovery-v1.md#афиша-публикация-и-участие), [DTO мобильного API](../../../docs/contracts/mobile-api.md#be-0203--каталог-события-и-запись), [внутренний интерфейс снимка и Kafka](../../../docs/contracts/catalog-integration.md), [локальный запуск и dev-данные](../../../backend/README.md).
- Из `backend`: `NGINX_PORT=18086 docker compose -p srastemsya-be-d02-tester -f compose.yaml -f compose.dev.yaml up --build -d --wait`. HTTP `http://127.0.0.1:18086/v1`. Готовность `/identity/health`, `/catalog/health`, `/swipes/health`.
- Контакты dev, обложки и заголовок часов приведены в [инструкции стенда](../../../backend/README.md#стендовые-обложки-и-часы-be-d02). Запуск запроса к снимку из swipes и просмотр Kafka приведены в том же разделе. Для этих команд используйте `-p srastemsya-be-d02-tester`.
