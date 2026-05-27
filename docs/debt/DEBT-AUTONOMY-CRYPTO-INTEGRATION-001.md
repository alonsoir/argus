# DEBT-AUTONOMY-CRYPTO-INTEGRATION-001

**Fecha:** DAY 155  
**Prioridad:** P1 post-P2  
**Estado:** ABIERTA

## Descripción

`CryptoAutonomyStateMachine` está definida en `common/` pero no instanciada
en ningún componente de producción. `AutonomyPublisher` y `AutonomySubscriber`
están implementados y testeados (DAY 155) pero sin integración en `main.cpp`.

## Bloqueador

No está decidido qué proceso es "Proceso A" — el daemon que gestiona el crypto
y que debe instanciar `CryptoAutonomyStateMachine` + `AutonomyPublisher`.

Candidatos:
- Un daemon crypto dedicado (nuevo componente)
- El sniffer (si linkea crypto_provider)
- Un proceso de supervisión central

## Trabajo pendiente

1. Decidir qué proceso instancia `CryptoAutonomyStateMachine` (consulta Consejo)
2. Integrar `AutonomyPublisher` en el `main.cpp` de ese proceso
3. Integrar `AutonomySubscriber` en `firewall-acl-agent/src/main.cpp`
4. Integrar polling reconciliador 90s en el health-check loop del firewall

## Implementado (DAY 155)

- `common/autonomy_publisher.h/.cpp` — ZMQ PUB, topic `argus.crypto.autonomy`
- `firewall-acl-agent/include/firewall/autonomy_subscriber.hpp/.cpp` — ZMQ SUB
- Tests de ambas clases en aislamiento

## Transporte

`ipc:///run/argus/autonomy.sock` — procesos separados confirmado
(firewall-acl-agent no linkea common/)
