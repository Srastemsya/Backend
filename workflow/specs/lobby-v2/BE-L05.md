# BE-L05

Обрабатывается только раздел [BE-L05](../../../docs/specs/lobby-v2/implementation.md#be-l05--следующий-пул-по-весам-категорий) в implementation.md и «Правила для всех пакетов» из того же документа. Итог при исчерпании в этот пакет не входит.

Пакет зависит от BE-L04. Порядок, ветка и база PR описаны в [README комнаты v2](../../../docs/specs/lobby-v2/README.md). Критерии L05-01 … L05-06 берутся из [acceptance.md](../../../docs/specs/lobby-v2/acceptance.md).

Публичное поведение определяется [контрактом комнаты v2](../../../docs/contracts/lobby-v2.md) поверх [Discovery v1](../../../docs/contracts/discovery-v1.md) и [мобильного HTTP-контракта](../../../docs/contracts/mobile-api.md). При расхождении для комнат действует контракт комнаты v2.

Developer дополнительно читает раздел BE-L05 и «Проверки перед отчётом» в [памятке разработчика](../../../docs/specs/lobby-v2/developer-guide.md). PM и Tester памятку не открывают и не пересылают: она описывает устройство кода.
