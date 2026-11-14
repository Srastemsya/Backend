# Identity

Владеет профилями, OTP, ключом подписи access JWT и сессиями. Использует собственную PostgreSQL и Redis для проверки состояния сессий. В Compose доступен как `identity:8000`.

| Метод и путь | Запрос | Успешный ответ |
|---|---|---|
| `POST /v1/auth/challenges` | `{channel: "SMS" \| "EMAIL", destination}` | `201 {challengeId, expiresAt, resendAvailableAt}` |
| `POST /v1/auth/challenges/{id}/verify` | `{code: string}` | `200 Session` |
| `POST /v1/auth/refresh` | `{refreshToken}` | `200 Session` с новой парой токенов |
| `GET /v1/me` | Bearer JWT | `200 Profile` |
| `PUT /v1/me/registration` | Bearer JWT и `{displayName, birthDate}` | `200 Profile` |
| `DELETE /v1/auth/session` | Bearer JWT | `204`, сессия отозвана |
| `GET /internal/identity/participants?id=…&id=…` | В сети Compose, Bearer JWT завершённого профиля и 1–20 ID | `200 {items: [{id, displayName, avatar}]}` |

POST требует `Idempotency-Key`. OTP действует 5 минут. Неверный код возвращает `422 OTP_INVALID`, истёкший challenge — `410 OTP_EXPIRED`, лимит — `429 RATE_LIMITED`. В dev используется тестовый код из инструкции запуска. Для обновления и выхода учитывайте правила ротации и отзыва.

[Вход, регистрация и сессии](../contracts/discovery-v1.md#вход-и-регистрация) · [DTO и общие ошибки](../contracts/mobile-api.md) · [Служебные маршруты](README.md#служебные-маршруты)
