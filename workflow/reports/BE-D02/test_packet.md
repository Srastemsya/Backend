# BE-D02 · Пакет для независимой проверки

- Кандидат `d3d76991309ebb180278605d46d8e11c6f4e7380`, ветка `be-d02`. Сборка catalog на стенде разработчика `sha256:b4e59c4fc70c825223d8343725dc09deb8dfa1638513e91a8f84c08819a20239`.
- [Контракт Discovery v1](../../../docs/contracts/discovery-v1.md#афиша-публикация-и-участие), [DTO мобильного API](../../../docs/contracts/mobile-api.md#be-0203--каталог-события-и-запись), [внутренний интерфейс снимка и Kafka](../../../docs/contracts/catalog-integration.md), [локальный запуск и dev-данные](../../../backend/README.md).
- Из `backend`: `NGINX_PORT=18086 docker compose -p srastemsya-be-d02-tester -f compose.yaml -f compose.dev.yaml up --build -d --wait`. HTTP `http://127.0.0.1:18086/v1`. Готовность `/identity/health`, `/catalog/health`, `/swipes/health`.
- Контакты dev, обложки и заголовок часов приведены в [инструкции стенда](../../../backend/README.md#стендовые-обложки-и-часы-be-d02). Запуск запроса к снимку из swipes и просмотр Kafka приведены в том же разделе. Для этих команд используйте `-p srastemsya-be-d02-tester`.
