# Backend contracts with code

Update the relevant contract in the same change as a new or modified backend interface.

| Change | Documentation |
|---|---|
| Mobile HTTP route, DTO, or authentication | [Mobile HTTP contract](../../../docs/contracts/mobile-api.md) and OpenAPI definition if present |
| New service, Kafka topic, or event shape | Document service ownership and the event contract alongside the implementation |
| Cross-cutting architecture | Update the relevant architecture documentation |

Define contracts before implementation. Document paths, request and response shapes, ownership, and scope. Keep descriptive documentation aligned with implementation and exclude secrets and full environment values. Preserve normative acceptance requirements and escalate contract changes outside scope to PM.
