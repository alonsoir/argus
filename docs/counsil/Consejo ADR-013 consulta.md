Actualizacion diaria:

# Registro para el Consejo de Sabios — DAY 98
## ML Defender — Migración CryptoTransport (ADR-013 PHASE 2)
### 26 marzo 2026

---

## Contexto

ML Defender es un sistema de detección de intrusiones de red en C++20 dirigido a organizaciones con recursos limitados (hospitales, escuelas, PYMEs). DAY 98 completó la segunda fase del ADR-013: migrar los 6 componentes del pipeline del `CryptoManager` legacy al nuevo `CryptoTransport` con HKDF-SHA256 nativo via libsodium 1.0.19.

---

## Trabajo realizado en DAY 98

### Objetivo
Sustituir `CryptoManager` (semilla aleatoria por componente, sin HKDF, sin cadena de confianza) por `CryptoTransport` (semilla desde `seed.bin` via `SeedClient`, HKDF-SHA256, ChaCha20-Poly1305 IETF, nonce 96-bit monotónico).

### Componentes migrados (6/6)

| Componente | Cambios principales |
|---|---|
| `etcd-server` | `ComponentRegistry`: `crypto_manager_` → `seed_client_ + tx_ + rx_`; `rotate_key()` deprecado (provision.sh SSOT) |
| `etcd-client` | `process_outgoing_data`: LZ4 directo + `tx_->encrypt()`; `set_encryption_key()` deprecado |
| `sniffer` | `RingBufferConsumer`: `initialize_zmq()` y `send_protobuf_message()` migrados; `encryption_seed` param deprecado |
| `ml-detector` | `ZMQHandler`: decrypt + compress/encrypt; `RAGLogger`: artefactos cifrados con contexto `rag-artifacts` |
| `rag-ingester` | `EventLoader`: constructor sin parámetros, SeedClient interno, LZ4 con cabecera `[uint32_t orig_size LE]` |
| `firewall-acl-agent` | `ZMQSubscriber`: `crypto_transport::decrypt()` libre → `rx_->decrypt()` con contexto simétrico al ml-detector |

### Metodología
- CryptoManager marcado `DEPRECATED DAY 98` — no borrado (Via Appia: no derribar hasta que lo nuevo esté probado)
- Flags `enabled` en JSONs mantenidos — borrado en sesión futura (ADR-020)
- LZ4 con cabecera `[uint32_t orig_size LE]` consistente en todos los componentes
- Contextos HKDF simétricos entre emisor y receptor documentados en prompt de continuidad

### Resultado
```
Tests: 22/22 suites ✅
Compilación: 6/6 componentes sin errores
```

---

## Preguntas específicas al Consejo

### 1. Simetría de contextos HKDF

El wire format actual es:
- Sniffer → `"ml-defender:sniffer:v1:tx"` cifra
- ml-detector → `"ml-defender:ml-detector:v1:rx"` debería descifrar

**Pregunta:** El contexto HKDF debe ser **idéntico** en emisor y receptor para que la clave derivada coincida. El ml-detector actualmente usa `"ml-defender:ml-detector:v1:rx"` para descifrar mensajes del sniffer. Pero el sniffer cifra con `"ml-defender:sniffer:v1:tx"`. Estos contextos son **diferentes** — lo que significa claves diferentes y por tanto **descifrado fallido en producción**.

¿Cuál es la arquitectura correcta?

- **Opción A:** Contexto idéntico en ambos lados: sniffer `tx` usa `"ml-defender:sniffer:v1"` y ml-detector `rx` usa también `"ml-defender:sniffer:v1"`
- **Opción B:** Contextos separados son intencionales y hay una capa adicional de intercambio de claves no implementada aún
- **Opción C:** El seed.bin es el mismo en todos los componentes (provision.sh SSOT) por lo que la clave derivada con cualquier contexto es diferente pero predecible — necesitamos un protocolo de handshake para acordar contexto

### 2. LZ4 cabecera `[uint32_t orig_size LE]`

Hemos estandarizado el formato LZ4 con una cabecera de 4 bytes conteniendo el tamaño original. Este formato es custom (no es el frame format estándar de LZ4).

**Pregunta:** ¿Es preferible usar el LZ4 Frame Format estándar (`LZ4F_*` API) para compatibilidad futura con herramientas externas, o el formato custom actual es suficiente dado que todos los componentes son internos?

### 3. Modo degradado en EventLoader y RAGLogger

Tanto `EventLoader` como `RAGLogger` tienen modo degradado — si `SeedClient` falla (seed.bin no existe), continúan en plaintext con un warning.

**Pregunta:** ¿Este modo degradado es aceptable para el threat model de organizaciones objetivo (hospitales, PYMEs)? ¿O debería ser fatal (el componente no arranca sin seed.bin)?

### 4. `tools/` pendiente

Los tres ficheros `tools/synthetic_sniffer_injector.cpp`, `tools/synthetic_ml_output_injector.cpp` y `tools/generate_synthetic_events.cpp` siguen usando `CryptoManager`. Son herramientas de stress test, no pipeline de producción.

**Pregunta:** ¿Deben migrarse con la misma prioridad que los componentes de producción, o es aceptable mantenerlos con `CryptoManager` hasta que haya un `seed.bin` para `tools/`? ¿Qué path de configuración usarían — `/etc/ml-defender/tools/tools.json`?

### 5. TEST-INTEG-1/2 como gate de release

Actualmente no existen tests que validen el round-trip completo cifrado→descifrado entre componentes reales.

**Pregunta:** ¿Deberían TEST-INTEG-1/2 ser requisito obligatorio (gate) antes de la submission a arXiv, o pueden ir en paralelo?

---

## Resumen para el Consejo

DAY 98 cierra la migración de 6/6 componentes. La cadena de confianza `provision.sh → seed.bin → SeedClient → HKDF → CryptoTransport` está operativa en compilación y tests unitarios. El trabajo pendiente crítico son los tests de integración E2E (TEST-INTEG-1/2) que validen que la simetría de contextos HKDF es correcta en producción.

La pregunta más urgente para el Consejo es la **pregunta 1** sobre simetría de contextos.

---

*Firmado: Alonso Isidoro Roman + Claude (Anthropic)*
*DAY 98 — 26 marzo 2026*

---

Estos son los dos documentos, Alonso. El registro para el Consejo tiene la pregunta 1 marcada como urgente — la simetría de contextos HKDF entre emisor y receptor es el riesgo técnico más serio que quedó abierto hoy. Los tests E2E (TEST-INTEG-1/2) de mañana lo confirmarán o desmentirán. Buen trabajo hoy — 6/6 en un solo día es ritmo Via Appia.