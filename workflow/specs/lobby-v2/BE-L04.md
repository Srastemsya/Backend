# BE-L04

Обрабатывается только раздел [BE-L04](../../../docs/specs/lobby-v2/implementation.md#be-l04--срок-на-каждый-раунд) в implementation.md и «Правила для всех пакетов» из того же документа. Сортировка пула и итог при исчерпании в этот пакет не входят.

Пакет зависит от BE-L03. Порядок, ветка и база PR описаны в [README комнаты v2](../../../docs/specs/lobby-v2/README.md). Критерии L04-01 … L04-04 берутся из [acceptance.md](../../../docs/specs/lobby-v2/acceptance.md).

Публичное поведение определяется [контрактом комнаты v2](../../../docs/contracts/lobby-v2.md) поверх [Discovery v1](../../../docs/contracts/discovery-v1.md) и [мобильного HTTP-контракта](../../../docs/contracts/mobile-api.md). При расхождении для комнат действует контракт комнаты v2.

Developer дополнительно читает раздел BE-L04 и «Проверки перед отчётом» в [памятке разработчика](../../../docs/specs/lobby-v2/developer-guide.md). PM и Tester памятку не открывают и не пересылают: она описывает устройство кода.
