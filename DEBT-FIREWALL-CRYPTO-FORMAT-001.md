# DEBT-FIREWALL-CRYPTO-FORMAT-001

**Prioridad:** P1  
**Estado:** ABIERTA  
**Detectado formalmente:** DAY 158  
**Origen real:** DAY 98 (migración CryptoManager → CryptoTransport, ADR-013)

## Síntoma
Firewall: events_processed=0, events_dropped=N (100% drop rate).
`Decrypt/decompress failed | error=Invalid hex character at position 0: stoi`

## Causa raíz
`zmq_subscriber.cpp` usa la ruta antigua:
  `hex_to_bytes(config_.crypto_token)` donde `crypto_token` viene vacío de etcd
  porque `get_encryption_key()` está DEPRECATED desde DAY 98.

El firewall TIENE el seed correcto en disco:
  `/etc/ml-defender/firewall-acl-agent/seed.bin` (idéntico al de ml-detector)
  pero nunca lo usa para descifrar.

ml-detector cifra con CryptoTransport + seed.bin → correcto.
firewall intenta descifrar con token vacío de etcd → 100% drop.

## Fix DAY 159
Migrar `firewall-acl-agent/src/api/zmq_subscriber.cpp` para usar
CryptoTransport con seed.bin compartido, igual que ml-detector.
Mismo patrón que ADR-013 PHASE 2 DAY 98-99.

Modo community: seed.bin en /etc/ml-defender/ (SeedFileProvider)
Modo enterprise: family_B/seed desde Vault (post-FEDER)

## Impacto
El firewall no bloquea ninguna IP en producción.
La cadena sniffer→ml-detector→firewall está rota desde DAY 98.

## Prerequisito para
- BACKLOG-BENCHMARK-CAPACITY-001 (benchmarks reales)
- DEBT-ALERTING-LIBCRYPTO-PROVIDER-001
- Cualquier validación E2E del pipeline completo
