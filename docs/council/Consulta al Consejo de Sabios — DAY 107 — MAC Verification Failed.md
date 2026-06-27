---

## Consulta al Consejo de Sabios — DAY 107 — MAC Verification Failed

**Proyecto**: aRGus NDR (ML Defender) — C++20, libsodium 1.0.19, ChaCha20-Poly1305 IETF

### Síntoma exacto

El componente `ml-detector` envía un PUT cifrado a `/v1/config/ml-detector` en el `etcd-server`. El servidor responde siempre con:

```json
{"details":"CryptoTransport::decrypt: MAC verification failed (wrong key, corrupted data, or nonce mismatch)","error":"Internal error","status":"error"}
```

El endpoint `/register` (sin cifrado) funciona correctamente — `ml-detector` se registra con éxito. Solo el PUT cifrado falla.

---

### Arquitectura cripto relevante

**`CryptoTransport`**: wrapper sobre HKDF-SHA256 + ChaCha20-Poly1305 IETF.
- Constructor: `CryptoTransport(SeedClient&, context_string)` → deriva `session_key` vía HKDF
- `encrypt(plaintext)` → `[nonce_96bit | ciphertext | MAC_16]`
- `decrypt(ciphertext)` → plaintext o lanza si MAC falla
- Nonce: contador monotónico 64-bit en bytes 4-11 del nonce de 96 bits

**`SeedClient`**: lee `seed.bin` (32 bytes) del path en el JSON del componente.

**Contextos** (`contexts.hpp`):
```cpp
CTX_ETCD_TX = "ml-defender:etcd:v1:tx"
CTX_ETCD_RX = "ml-defender:etcd:v1:rx"
```

**etcd-client** (ml-detector usa):
```cpp
tx_ = CryptoTransport(seed_client, CTX_ETCD_TX);  // cifra PUT
rx_ = CryptoTransport(seed_client, CTX_ETCD_RX);  // descifra respuestas
```

**etcd-server** (tras el fix de hoy):
```cpp
tx_ = CryptoTransport(seed_client, CTX_ETCD_RX);  // cifra respuestas
rx_ = CryptoTransport(seed_client, CTX_ETCD_TX);  // descifra PUT ← este es el que falla
```

---

### Todo lo verificado y descartado

| Check | Resultado |
|---|---|
| Seeds idénticos etcd-server y ml-detector | ✅ `ff87bf05852f3f2a...` ambos |
| Una sola libsodium en memoria | ✅ solo `.so.26` tras fix symlink `.so.23→.so.26` |
| Contextos HKDF simétricos server/client | ✅ TX↔TX, RX↔RX |
| `test_integ_contexts` 4/4 | ✅ incluyendo INTEG3 asimétrico |
| `test_crypto_transport` 10/10 | ✅ |
| Binario etcd-server recompilado limpio (rm -rf build-debug) | ✅ `component_registry.cpp` compilado desde cero |
| Binario correcto en `/proc/PID/exe` | ✅ `/vagrant/etcd-server/build-debug/etcd-server` |
| `libcrypto_transport.so.1.0.0` fecha abr 4 | ✅ 52032 bytes |
| Symlinks `.so` actualizados a abr 4 | ✅ |
| `ldconfig` ejecutado | ✅ |
| component_json_path etcd-server lee seed de `/etc/ml-defender/etcd-server/seed.bin` | ✅ symlink → `/vagrant/etcd-server/config/etcd-server.json` |
| component_json_path ml-detector lee seed de `/etc/ml-defender/ml-detector/seed.bin` | ✅ |
| `chmod 755` directorios, `640` seeds | ✅ |

---

### Lo que NO hemos verificado

1. Si `encryption_enabled_` está realmente `true` en el servidor cuando llega el PUT (podría estar en `false` y el path llegar sin cifrar al `decrypt_data`, que lo devolvería tal cual — pero entonces no habría MAC error)
2. Si el cliente `ml-detector` está realmente usando `CTX_ETCD_TX` y no otro contexto (¿qué `component_config_path` recibe?)
3. Si la compresión LZ4 está activa en el cliente y el servidor no la está decomprimiendo antes de descifrar (orden incorrecto)
4. Si hay otro `libetcd_client.so` con lógica distinta siendo cargado por ml-detector vs el que usa el sniffer (que sí arranca)

---

### Pregunta al Consejo

Dados seeds idénticos, contextos simétricos, una sola libsodium, y binarios frescos — **¿qué otras causas pueden producir MAC verification failed en ChaCha20-Poly1305 IETF?**

Específicamente pedimos hipótesis que no sean seeds distintos, contextos asimétricos, o doble libsodium — ya que esas tres están descartadas.