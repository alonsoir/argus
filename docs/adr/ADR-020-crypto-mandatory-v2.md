# ADR-020: Cifrado y Compresión Siempre Obligatorios

**Status:** ACCEPTED
**Fecha:** 2026-03-25
**Autores:** Alonso Isidoro Roman + Claude (Anthropic)
**DAY:** 97
**Consejo DAY 96:** Grok · DeepSeek · Gemini · ChatGPT5 (unanimidad 4/4)

---

## Contexto

Los JSONs de los 6 componentes del pipeline contenían flags opcionales:

```json
"encryption": { "enabled": true, ... }
"compression": { "enabled": true, ... }
```

Esto permitía desactivar cifrado o compresión en tiempo de ejecución. Para un
sistema EDR diseñado para hospitales y organizaciones con recursos limitados de
seguridad, este vector de ataque es inaceptable: un atacante que modifique el
fichero JSON (misconfiguration, supply-chain attack) puede silenciar el cifrado
sin tocar el código.

Con la llegada de CryptoTransport (ADR-013 PHASE 2, DAY 97), el cifrado ya no
es configurable — está hardwired en la cadena de confianza:

    provision.sh → seed.bin → SeedClient → CryptoTransport(HKDF) → ChaCha20-Poly1305

No existe ruta de código que omita este camino.

---

## Decisión

**Eliminar los flags `enabled` de todos los JSONs de configuración.**

Cifrado y compresión son **siempre obligatorios** en el pipeline de ML Defender.
No existe modo "sin cifrado" ni "sin compresión" en producción.

Orden de operaciones invariante: **LZ4 → ChaCha20-Poly1305 IETF**
(comprimir antes de cifrar maximiza la ratio de compresión y la entropía).

---

## Especificación técnica

### Cifrado
- Algoritmo: **ChaCha20-Poly1305 IETF** (`crypto_aead_chacha20poly1305_ietf_*`)
- Derivación de clave: **HKDF-SHA256** via libsodium 1.0.19 nativo
- Nonce: **96-bit monotónico** — `[0x00000000 || uint64_LE_counter]`
- Wire format: `[nonce(12) || ciphertext(N) || mac(16)]`
- Clase: `crypto_transport::CryptoTransport`

### Compresión
- Algoritmo: **LZ4** con header de tamaño original (4 bytes big-endian)
- Wire format: `[original_size(4) || compressed_data(N)]`

### Contextos HKDF obligatorios por componente

```
"ml-defender:{component}:{version}:{tx|rx}"

Ejemplos:
  "ml-defender:sniffer:v1:tx"
  "ml-defender:sniffer:v1:rx"
  "ml-defender:ml-detector:v1:tx"
  "ml-defender:firewall-acl-agent:v1:tx"
  "ml-defender:rag-ingester:v1:tx"
  "ml-defender:rag-security:v1:tx"
  "ml-defender:etcd-server:v1:tx"
```

TX y RX **siempre** usan instancias separadas con contextos distintos.

---

## Consecuencias

### Positivas
- Superficie de ataque reducida: ningún flag de configuración puede desactivar
  la cadena de confianza criptográfica.
- Código más simple: no hay ramas `if (encryption.enabled)` en los componentes.
- Comportamiento determinista: todo el tráfico del pipeline está cifrado
  y comprimido sin excepción.
- `CryptoManager` (clase legacy) queda deprecada — `CryptoTransport` la sustituye.

### Negativas / Mitigaciones
- **Debug**: sin flag `enabled`, el debugging de comunicaciones requiere
  un entorno de test con CryptoTransport mock o logs TRACE.
  Mitigación: los tests TC-CT-001..010 cubren el round-trip completo.
- **Rollback**: si libsodium 1.0.19 no está disponible, el pipeline no arranca.
  Mitigación: `provision.sh` garantiza libsodium 1.0.19 instalada y verificada
  (SHA-256: 018d79fe0a045cca07331d37bd0cb57b2e838c51bc48fd837a1472e50068bbea)
  antes del deploy, con reinstalación de dependencias ZeroMQ incluida.

---

## Ficheros afectados

### JSONs de configuración (pendiente DAY 98)
| Componente | JSON |
|---|---|
| sniffer | `sniffer/config/sniffer.json` |
| ml-detector | `ml-detector/config/ml_detector_config.json` |
| firewall-acl-agent | `firewall-acl-agent/config/firewall.json` |
| rag-ingester | `rag-ingester/config/rag-ingester.json` |
| rag-security | `rag/config/rag-config.json` |
| etcd-server | `etcd-server/config/etcd-server.json` |

### Código nuevo (DAY 97)
| Fichero | Descripción |
|---|---|
| `crypto-transport/include/crypto_transport/transport.hpp` | Interfaz CryptoTransport |
| `crypto-transport/src/transport.cpp` | Implementación HKDF + nonce + AEAD |
| `crypto-transport/tests/test_crypto_transport.cpp` | 10 tests TC-CT-001..010 |
| `tools/provision.sh` | install_libsodium_1019() + check_entropy() |

### Código deprecado (migración pendiente DAY 98)
| Fichero | Estado |
|---|---|
| `crypto-transport/include/crypto_transport/crypto_manager.hpp` | DEPRECADO — sustituido por CryptoTransport |

---

## Alternativas consideradas

**Flag `enabled` en compilación (#ifdef):** Un build de debug sin cifrado que
llega a producción (error operacional común) expondría todo el tráfico. Rechazado.

**Flag solo para tests:** El entorno de test usa VMs idénticas a producción con
seed.bin generado por provision.sh. Los tests deben ejercitar el path
criptográfico completo para ser válidos. Rechazado.

---

## Referencias

- ADR-013: seed-client y cadena de confianza
- ADR-019: OS hardening y secure deployment
- DEBT-CRYPTO-001: nonce monotónico 96-bit
- DEBT-CRYPTO-002: HKDF en crypto-transport
- DEBT-CRYPTO-003b: entropy check en provision.sh
- Consejo DAY 96: docs/engineering_decisions/day-096-seed-client-council.md
- Tests: TC-CT-001..010 en crypto-transport/tests/test_crypto_transport.cpp