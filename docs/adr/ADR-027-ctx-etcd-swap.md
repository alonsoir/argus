# ADR-027: CTX_ETCD_TX/RX Swap en etcd-server

**Estado**: ACEPTADO  
**Fecha**: 2026-04-05  
**Contexto**: DAY 107–108 — troubleshooting MAC verification failed  
**Deciders**: Alonso Isidoro Román, Consejo de Sabios DAY 107

---

## Contexto

Durante DAY 107, tras resolver el root cause principal (ADR-027-pre: 
`component_config_path` no seteado → `tx_` null → datos en claro), el 
pipeline arrancó 6/6 con el swap `CTX_ETCD_TX/RX` aplicado en 
`etcd-server/src/component_registry.cpp`.

DAY 108, PASO 1: se revirtió el swap para verificar si era necesario 
independientemente del fix de `component_config_path`. Resultado: MAC 
failure confirmado en ml-detector, sniffer y firewall. El swap es 
correcto y necesario.

## Decisión

En `etcd-server/src/component_registry.cpp`, el servidor etcd debe 
invertir los contextos HKDF respecto al cliente:
```cpp
// CORRECTO — servidor invierte TX/RX respecto al cliente
tx_ = std::make_unique<crypto_transport::CryptoTransport>(
    *seed_client_, ml_defender::crypto::CTX_ETCD_RX);  // ← RX, no TX
rx_ = std::make_unique<crypto_transport::CryptoTransport>(
    *seed_client_, ml_defender::crypto::CTX_ETCD_TX);  // ← TX, no RX
```

## Justificación

HKDF deriva subclaves distintas por contexto semántico. El cliente cifra 
con `CTX_ETCD_TX` (transmisión) y descifra con `CTX_ETCD_RX` (recepción). 
El servidor es el espejo exacto: debe descifrar lo que el cliente cifró 
(usa `CTX_ETCD_TX` en su `rx_`) y cifrar lo que el cliente descifrará 
(usa `CTX_ETCD_RX` en su `tx_`). Sin el swap, ambos lados usan la misma 
subclave en la misma dirección — MAC failure garantizado.

Este es el mismo principio que los nonces unidireccionales en TLS 1.3: 
cliente y servidor mantienen contadores separados por dirección.

## Verificación (DAY 108)

1. Swap revertido al original → MAC failure en 3/6 componentes (los que
   tenían `component_config_path` correctamente seteado)
2. Swap restaurado → 6/6 RUNNING, cifrado funcional

**TEST de regresión**: si se revierte este swap, ml-detector, sniffer y 
firewall-acl-agent deben producir `MAC verification failed` en el PUT 
de configuración. Verificado empíricamente DAY 108.

## Invariant asociado (mismo commit)

En los tres adaptadores `etcd_client.cpp` se añadió fail-fast:
```cpp
// INVARIANT (ADR-027): encryption_enabled requiere component_config_path.
// Sin él, SeedClient no inicializa → datos en claro → MAC failure garantizado.
if (config_.encryption_enabled && config.component_config_path.empty()) {
    std::terminate(); // FATAL: setear component_config_path en etcd_client::Config
}
```

## Consecuencias

- **Positivas**: fallo rápido y ruidoso si el swap se revierte
  accidentalmente; documentación del principio mirror para futuros 
  adaptadores
- **Deuda**: cuando se añadan nuevos componentes con `etcd_client.cpp`, 
  el `component_config_path` debe setearse explícitamente (invariant lo 
  garantiza con `std::terminate`)

## Ficheros modificados

- `etcd-server/src/component_registry.cpp` — swap CTX_ETCD_TX/RX
- `ml-detector/src/etcd_client.cpp` — invariant fail-fast
- `sniffer/src/userspace/etcd_client.cpp` — invariant fail-fast  
- `firewall-acl-agent/src/core/etcd_client.cpp` — invariant fail-fast
