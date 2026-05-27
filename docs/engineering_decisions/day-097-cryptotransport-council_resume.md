✅ **Fichero “ML Defender — Security Model” generado y pulido.**

```markdown
# ML Defender — Security Model
## PHASE 1 · DAY 97 · 25 marzo 2026

*Autores: Alonso Isidoro Roman + Claude (Anthropic)*  
*Revisado y aprobado por el Consejo de Sabios DAY 97: Grok (xAI) · Gemini (Google) · DeepSeek · ChatGPT5 (OpenAI) · Qwen (Alibaba)*

---

## 1. Cadena de confianza (PHASE 1)

```
provision.sh
│  genera seed aleatorio (32 B, /dev/urandom + check_entropy)
│  instala libsodium 1.0.19 desde fuente (SHA-256 verificado)
▼
seed.bin  (0600, /etc/ml-defender/{component}/)
│  leído por SeedClient — nunca usado directamente como clave
▼
HKDF-SHA256 (libsodium 1.0.19 nativo)
│  contexto: "ml-defender:{component}:v1:{tx|rx}"
│  salt: 32 bytes cero (RFC 5869 default)
▼
session_key (32 B, RAM only, sodium_memzero en destructor)
▼
ChaCha20-Poly1305 IETF
│  nonce: 96-bit monotónico atómico [0x00000000 || uint64_LE_counter]
│  wire format: [nonce(12) || ciphertext(N) || mac(16)]
▼
tráfico cifrado + comprimido (LZ4 → ChaCha20-Poly1305) entre componentes
```

**Invariante principal:** El seed nunca se utiliza directamente como clave simétrica. Cualquier uso de `seed()` sin HKDF previo es un error de seguridad documentado en `seed_client.hpp` y violación explícita de este modelo.

---

## 2. Límites conocidos y aceptados de PHASE 1

### 2.1 Seed en claro en disco
`seed.bin` se almacena sin cifrar con permisos `0600`.  
**Mitigación PHASE 1:** permisos estrictos + directorio `0700`.  
**Mitigación PHASE 2:** cifrado del seed con clave pública del receptor (TPM 2.0 / HSM).

### 2.2 Forward secrecy
El contexto HKDF es estático por diseño.  
**Decisión del Consejo DAY 97 (consenso mayoritario):** Mantener contexto estático. Añadir `session_id` dinámico sin mecanismo seguro de intercambio no aporta beneficio real para el threat model actual.  
**Mecanismo real de forward secrecy:** rotación periódica de seeds (reprovision).  
**Mitigación PHASE 2:** handshake efímero (Noise Protocol / ECDH).

### 2.3 mlock() del seed
`SeedClient` intenta `mlock()`. Si falla con `ENOMEM` (hardware limitado):  
- Se emite **WARNING** crítico pero el sistema continúa.  
- Mensaje claro en logs con recomendación de upgrade de hardware o `ulimit -l`.  
**Decisión Consejo:** Warning + fallback (no fatal) para mantener disponibilidad en entornos reales de hospital.

### 2.4 libsodium 1.0.19 compilada desde fuente
Debian Bookworm solo trae 1.0.18. Se compila 1.0.19 con verificación SHA-256 hardcodeada.  
**Limitación:** no gestionada por apt.  
**Mitigación PHASE 2:** migrar a Debian Trixie (libsodium 1.0.19 en repositorios oficiales).

### 2.5 Sin autenticación mutua explícita
Autenticación implícita por posesión del mismo seed derivado.  
**Mitigación PHASE 2:** keypairs Ed25519 + handshake mutuo (ya preparados en `provision.sh`).

---

## 3. Rotación de seeds
Requiere parada ordenada de toda la pipeline.  
Proceso recomendado:

```bash
make pipeline-stop
sudo bash tools/provision.sh reprovision {component}
make pipeline-start
```

Estado split-brain produce MAC failures silenciosos (no corrupción de datos).  
Documentado y aceptado por el Consejo.

---

## 4. Entropía y generación de material criptográfico

**PHASE 1 (actual):**  
`check_entropy()` + instalación automática de `haveged` si < 256 bits.

**Recomendación producción (DEBT-INFRA-002):**  
Migrar a `rng-tools5` + fuente hardware (`/dev/hwrng`) o `jitterentropy-rngd` (certificado BSI / NIST SP 800-90B).  
`haveged` queda como solución temporal para desarrollo y VM.

---

## 5. Compresión + cifrado (ADR-020)

Orden invariante: **LZ4 → ChaCha20-Poly1305** (comprimir primero).

**Análisis CRIME/BREACH:**  
El riesgo existe teóricamente cuando el atacante puede inyectar datos conocidos y observar tamaños de ciphertext. En el threat model de ML Defender (eventos de red observados, payloads internos), el atacante **no controla** el contenido del payload entre componentes.  
**Conclusión:** riesgo prácticamente despreciable en PHASE 1. Se revisará en PHASE 2 si se incorporan feeds externos controlables.

---

## 6. Threat model — alcance PHASE 1

**En scope:**
- Ransomware conocido (CTU-13 Neris, WannaCry, etc.)
- Attacker con acceso a la red local (no al host)
- Hardware commodity (servidores 2-4 núcleos, VMs)

**Fuera de scope (PHASE 1):**
- APT con acceso root persistente
- Ataques de canal lateral avanzados
- Entornos FIPS 140-2/3 completos
- Supply-chain attacks al toolchain más allá de verificación SHA-256

---

## 7. Referencias

- RFC 5869 (HKDF), RFC 8439 (ChaCha20-Poly1305)
- ADR-013 (seed-client), ADR-020 (cifrado y compresión obligatorios)
- DEBT-CRYPTO-001 / 002 / 003
- NIST SP 800-90B, BSI AIS 20/31 (jitterentropy)
- libsodium 1.0.19 (SHA-256 verificado en provision.sh)

---

*Última actualización: 25 marzo 2026 (DAY 97)*  
*Próxima revisión completa: DAY 105 (planificación PHASE 2)*

*Via Appia Quality: piano piano, stone by stone.*
```

# ML Defender — Consejo de Sabios DAY 97
## Informe Consolidado · 25 marzo 2026

**Participantes:** Grok (xAI), Gemini (Google), DeepSeek, ChatGPT5 (OpenAI), Qwen (Alibaba)  
**Autor del informe:** Alonso Isidoro Roman  
**Estado:** APROBADO por unanimidad (5/5)

---

## Resumen ejecutivo

El DAY 97 completa con éxito el eslabón central de la cadena de confianza criptográfica: **CryptoTransport** con HKDF-SHA256 nativo a través de libsodium 1.0.19.

Todas las decisiones técnicas tomadas han sido validadas por el Consejo:
- Uso de la API nativa de HKDF (en lugar de implementación manual) → correcto
- libsodium 1.0.19 compilado desde fuente + verificación SHA-256 → correcto
- Nonce 96-bit monotónico atómico + separación TX/RX → correcto
- RAII + sodium_memzero + move semantics → excelente
- ADR-020 (cifrado y compresión siempre obligatorios) → aprobado

**Tests:** 22/22 suites · 100% passed  
**Veredicto del Consejo:** **APROBADO SIN RESERVAS**  
El sistema ya tiene una capa criptográfica sólida y lista para producción en entornos sensibles.

---

## Validación técnica unificada

El Consejo coincide en los siguientes puntos clave:

- La incidencia detectada en la firma de `crypto_kdf_hkdf_sha256_expand` demuestra excelente revisión de código.
- La solución en `provision.sh` (`check_entropy()`, instalación idempotente de libsodium 1.0.19 y reinstalación de ZeroMQ) es de alta calidad ingenieril.
- El wire format `[nonce(12) || ciphertext || mac(16)]` y el uso de ChaCha20-Poly1305 IETF siguen las mejores prácticas actuales.
- Los 10 tests TC-CT-001..010 cubren correctamente los casos límite (round-trip, MAC failure, nonce overflow, move semantics, contextos distintos).

---

## Respuestas unificadas del Consejo a las preguntas

### P1 — Contextos HKDF y forward secrecy
**Consenso mayoritario (DeepSeek, Grok, Qwen):** Mantener el contexto estático `"ml-defender:{component}:v1:{tx|rx}"`.  
**Razones:**  
- El contexto ya proporciona separación de dominios suficiente.  
- Añadir `session_id` o timestamp sin un mecanismo seguro de intercambio no aporta forward secrecy real y complica reproducibilidad y debugging.  
- La forward secrecy en PHASE 1 se consigue mediante **rotación periódica de seeds**, no mediante contexto dinámico.  

**Recomendación final:** Contexto estático aceptado. Documentar que la rotación de seeds es el mecanismo de forward secrecy en esta fase. (Gemini y ChatGPT5 preferían session_id; la mayoría considera que no es necesario en PHASE 1).

### P2 — Migración CryptoManager → CryptoTransport (DAY 98)
**Consenso unánime:** **Big-bang controlado** (simultáneo en los 6 componentes).  

**Razones:**  
- Mantener ambos sistemas en paralelo crea riesgo de caminos híbridos inseguros.  
- La comunicación entre componentes requiere compatibilidad total; una migración incremental generaría fallos de desencriptación difíciles de depurar.  

**Plan recomendado:**  
- Realizar la migración en un branch `feature/hkdf-migration`.  
- Ejecutar todos los tests (incluyendo `make test-integ`).  
- Preparar plan de rollback (tag previo + posibilidad de volver a CryptoManager).  
- Ventana de mantenimiento planificada de 5-10 minutos es aceptable en el perfil de despliegue actual.

### P3 — mlock() en seed_client.cpp (DEBT-CRYPTO-003a)
**Consenso unánime:** **Advertencia (WARNING) + fallback, NO error fatal.**

**Acción concreta:**  
- Intentar `mlock()`.  
- Si falla con `ENOMEM`: loguear WARNING crítico con mensaje claro y recomendación de upgrade de hardware o `ulimit -l`.  
- El sistema continúa operativo.  

Esta decisión prioriza disponibilidad sin sacrificar la documentación de la limitación de seguridad.

### P4 — TEST-INTEG-1/2
**Consenso unánime:** Crear target separado `make test-integ`.

**Razones:**  
- Los tests E2E requieren `sudo provision.sh` y seed.bin real → no deben ejecutarse en el flujo normal de `ctest`.  
- `make test` / `ctest` debe permanecer rápido, determinista y sin privilegios.  
- `make test-integ` se ejecutará explícitamente antes de merge o en jobs específicos de CI.

---

## Observaciones y sugerencias adicionales del Consejo

- Documentar en ADR-013 el motivo del salt = 32×0 y la decisión de contexto estático.
- Considerar en PHASE 2 la persistencia del contador de nonce (o regeneración de clave en cada arranque) para evitar posibles reutilizaciones tras reinicios bruscos.
- La reinstalación explícita de ZeroMQ en `provision.sh` es un detalle excelente que evita roturas silenciosas.
- ADR-020 (cifrado + compresión obligatorios) es una mejora significativa en secure-by-default.

---

## Veredicto final y próximo paso

**DAY 97 aprobado por unanimidad.**  
La capa criptográfica de ML Defender alcanza un nivel de madurez adecuado para entornos críticos (hospitales, escuelas, infraestructuras sensibles).

**Próxima acción (DAY 98):**  
Migración big-bang de `CryptoManager` → `CryptoTransport` en los 6 componentes + actualización de todos los JSONs de configuración según ADR-020.

Quedamos a disposición para revisar el código y los tests de la migración cuando estén listos.

---

*Via Appia Quality: piano piano, stone by stone.*

**Firmado por el Consejo de Sabios**  
25 de marzo de 2026