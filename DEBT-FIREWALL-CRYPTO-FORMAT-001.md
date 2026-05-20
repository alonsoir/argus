# DEBT-FIREWALL-CRYPTO-FORMAT-001

**Prioridad:** P1
**Estado:** ABIERTA
**Detectado formalmente:** DAY 158
**Origen real:** DAY 98 (migración CryptoManager → CryptoTransport, ADR-013)

## Síntoma
Firewall: events_processed=0, events_dropped=N (100% drop rate).
`Decrypt/decompress failed | error=Invalid hex character at position 0: stoi`

## Causa
`get_encryption_key()` deprecated desde DAY 98. El firewall usa la ruta
antigua (token hex de etcd vía `hex_to_bytes(config_.crypto_token)`).
ml-detector publica con CryptoTransport + seed compartido.
El firewall nunca recibió la migración a CryptoTransport.

## Fix necesario
Migrar `zmq_subscriber.cpp` para usar CryptoTransport con seed compartido,
igual que ml-detector. Mismo patrón que ADR-013 PHASE 2 DAY 98-99.

## Impacto
El firewall no bloquea ninguna IP en producción.
La cadena sniffer→ml-detector→firewall está rota desde DAY 98.
