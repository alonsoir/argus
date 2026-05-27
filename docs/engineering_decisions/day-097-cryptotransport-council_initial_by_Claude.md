# ML Defender — Consejo de Sabios DAY 97
## Informe de trabajo · 25 marzo 2026

Estimados co-revisores: Grok (xAI), ChatGPT (OpenAI), DeepSeek, Qwen (Alibaba),
Gemini (Google), Parallel.ai,

Os presento el trabajo realizado en DAY 97. Solicito revisión técnica y validación
de las decisiones tomadas.

---

## Resumen ejecutivo

DAY 97 completó el eslabón central de la cadena de confianza criptográfica:
`CryptoTransport` con HKDF-SHA256 nativo via libsodium 1.0.19. La propuesta
de implementar HKDF manualmente (RFC 5869 con `crypto_auth_hmacsha256`) fue
descartada en favor de la API nativa — decisión correcta validada en producción.

**Tests: 22/22 suites · 100% passed**

---

## Trabajo realizado

### 1. libsodium 1.0.19 desde fuente (provision.sh)

Debian Bookworm solo distribuye libsodium 1.0.18. `crypto_kdf_hkdf_sha256_*`
requiere >= 1.0.19. Solución implementada en `tools/provision.sh`:

- `check_entropy()`: verifica entropía del pool del kernel (DEBT-CRYPTO-003b).
  Si < 256 bits, instala `haveged` automáticamente.
- `install_libsodium_1019()`: descarga, verifica SHA-256, compila, instala.
    - SHA-256 verificado: `018d79fe0a045cca07331d37bd0cb57b2e838c51bc48fd837a1472e50068bbea`
    - Idempotente: salta si 1.0.19 + headers HKDF ya presentes.
    - Reinstala ZeroMQ tras el remove de libsodium23 (apt arrastra libzmq5).
- Función integrada en `provision_full()` antes de generar material criptográfico.

**Incidencia:** `apt remove libsodium23` elimina también `libzmq5 libzmq3-dev cppzmq-dev`.
Solución en provision.sh: reinstalación explícita post-compilación.

### 2. CryptoTransport — HKDF-SHA256 + ChaCha20-Poly1305 IETF

Ficheros: `crypto-transport/include/crypto_transport/transport.hpp` +
`crypto-transport/src/transport.cpp`

**Decisiones de implementación:**

- **HKDF-SHA256 nativo:** `crypto_kdf_hkdf_sha256_extract_init/update/final` +
  `crypto_kdf_hkdf_sha256_expand`. Salt = 32 bytes cero (RFC 5869 default).
  PRK nunca sale de la función — `sodium_memzero` inmediato tras expand.

- **Cifrado:** `crypto_aead_chacha20poly1305_ietf_*` (nonce 12 bytes, MAC 16 bytes).
  Wire format: `[nonce(12) || ciphertext(N) || mac(16)]`.

- **Nonce 96-bit monotónico:** `[0x00000000 || uint64_LE_counter]` atómico
  (`std::atomic<uint64_t>`). Thread-safe. Overflow detectado y lanza excepción.

- **RAII:** destructor limpia `session_key_` con `sodium_memzero`. Move semántico
  implementado (zeroing del origen). No copiable.

- **TX/RX separados:** contextos distintos → claves distintas → sin reutilización
  de nonce entre dirección de envío y recepción.

**Incidencia crítica descubierta:** La firma real de `crypto_kdf_hkdf_sha256_expand`
en 1.0.19 recibe `prk[]` directamente, NO el state. El state solo se usa en extract.
La documentación oficial es ambigua — detectado en tiempo de compilación.

### 3. CMake — libsodium priorizada en /usr/local

`NO_DEFAULT_PATH` añadido al `find_library` de libsodium para evitar que el linker
coja `libsodium.so.23` del sistema en lugar de `libsodium.so.26` de `/usr/local`.

### 4. 10 tests TC-CT-001..010

Tests en `crypto-transport/tests/test_crypto_transport.cpp`:
- TC-CT-001: Constructor con SeedClient cargado
- TC-CT-002: Constructor lanza si SeedClient no cargado
- TC-CT-003: Round-trip encrypt/decrypt exacto
- TC-CT-004: Wire format = nonce(12) + ct(N) + mac(16)
- TC-CT-005: Plaintext vacío → empty
- TC-CT-006: Nonce counter monotónico
- TC-CT-007: Dos cifrados del mismo plaintext → ciphertexts distintos
- TC-CT-008: Ciphertext manipulado → MAC failure
- TC-CT-009: Contextos distintos → claves distintas → MAC failure
- TC-CT-010: Move constructor correcto

### 5. ADR-020: Cifrado y compresión siempre obligatorios

Flags `encryption.enabled` y `compression.enabled` eliminados del contrato de
configuración. La migración de JSONs se completará en DAY 98 junto con la
integración de `CryptoTransport` en los 6 componentes.

---

## Estado del test suite

```
crypto-transport:  4/4  (test_crypto · test_compression · test_integration · test_crypto_transport)
seed-client:       1/1  (6 tests internos)
etcd-server:       1/1  (test_secrets_manager_simple — add_test() añadido)
rag-ingester:      7/7
ml-detector:       9/9
─────────────────────
TOTAL:            22/22  100% passed
```

---

## Preguntas para el Consejo

**P1 — Contextos HKDF y forward secrecy:**
El contexto actual `"ml-defender:{component}:v1:{tx|rx}"` es estático por sesión.
¿Recomendáis añadir un timestamp o session_id al contexto para mayor separación
entre sesiones sin requerir rotación completa de seeds?

**P2 — Migración CryptoManager → CryptoTransport (DAY 98):**
`CryptoManager` usa el seed directamente como clave (sin HKDF) — el "USO INCORRECTO"
documentado en `seed_client.hpp`. La migración en DAY 98 implicará cambios en los
6 componentes simultáneamente. ¿Recomendáis migración incremental o big-bang?

**P3 — mlock() en seed_client.cpp (DEBT-CRYPTO-003a):**
`mlock()` previene que el seed sea swapeado a disco. En entornos con memoria
limitada (hospitales con hardware antiguo), `mlock()` puede fallar con `ENOMEM`.
¿Debe ser un error fatal o una advertencia?

**P4 — TEST-INTEG-1/2:**
Los tests de integración E2E requieren seed.bin real en `/etc/ml-defender/`.
¿Los tests de integración deben correr como parte del `ctest` normal (requiriendo
`sudo provision.sh` previo) o como target separado `make test-integ`?

---

## Commit de referencia

```
feat(crypto): HKDF-SHA256 nativo + CryptoTransport + libsodium 1.0.19 (DAY 97)

- CryptoTransport: HKDF-SHA256 via libsodium 1.0.19 nativo (ADR-013 PHASE 2)
- Nonce 96-bit monotónico atómico (DEBT-CRYPTO-001)
- ChaCha20-Poly1305 IETF — wire format [nonce(12)|ct(N)|mac(16)]
- 10 tests TC-CT-001..010: round-trip, MAC failure, nonce, move, contexts
- provision.sh: install_libsodium_1019 + check_entropy + reinstala ZeroMQ
- SHA-256 verificado: 018d79fe0a045cca…
- ADR-020: cifrado+compresión siempre obligatorios — flags enabled eliminados
- etcd-server CMakeLists: add_test() registrado correctamente
- Tests: 22/22 suites 100% passed

Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)
```

---

Quedo a disposición del Consejo para cualquier aclaración técnica.

*Alonso Isidoro Roman*
*ML Defender — DAY 97 · 25 marzo 2026*
*Via Appia Quality: piano piano, stone by stone*