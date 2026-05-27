¡Excelente trabajo, Alonso!

DAY 97 marca un hito sólido en la cadena de confianza de **ML Defender**. Has cerrado el eslabón central con limpieza, rigor y excelente higiene criptográfica. El Consejo de Sabios valida **técnicamente todas las decisiones tomadas**. A continuación, la revisión punto por punto y respuestas a las preguntas.

### Validación general

- **libsodium 1.0.19 desde fuente** → Correcto y necesario. Debian Bookworm trae 1.0.18; HKDF llegó exactamente en 1.0.19. La verificación SHA-256, el `check_entropy()`, la idempotencia y la reinstalación de ZeroMQ son impecables. La incidencia con `apt remove libsodium23` está bien resuelta.

- **CryptoTransport** → Diseño excelente.
  - Uso nativo de `crypto_kdf_hkdf_sha256_*` (extract + expand) es la vía correcta.
  - Salt = 32 bytes cero es aceptable cuando el IKM ya tiene suficiente entropía (como tu seed de 256+ bits).
  - PRK zeroed inmediatamente → muy buena práctica.
  - ChaCha20-Poly1305 IETF con wire format `[nonce(12) || ct || mac(16)]` es estándar y seguro.
  - Nonce 96-bit como `[0x00000000 || uint64_LE_counter]` atómico es la forma recomendada por RFC 8439 para evitar reutilización. Overflow como excepción es correcto (mejor fallar seguro que reutilizar nonce).
  - RAII + move semantics + `sodium_memzero` en destructor/origen → perfecto.
  - Contextos TX/RX separados → evita cualquier riesgo de nonce reuse entre direcciones.

La incidencia detectada en la firma de `crypto_kdf_hkdf_sha256_expand` (recibe `prk[]` directamente, no el state) es conocida; la documentación oficial es un poco ambigua en algunos sitios, pero el código fuente y los headers son claros. Buen catch en tiempo de compilación.

- **CMake** con `NO_DEFAULT_PATH` → decisión correcta y defensiva.

- **Tests 10/10 + suite completa 22/22** → cobertura excelente. Especialmente valoro TC-CT-008 (manipulación → MAC failure), TC-CT-009 (contextos distintos → claves distintas) y TC-CT-010 (move semantics).

- **ADR-020** (cifrado + compresión siempre obligatorios) → totalmente de acuerdo. Eliminar los flags simplifica el contrato y elimina caminos de degradación insegura.

### Respuestas del Consejo a las preguntas (P1–P4)

**P1 — Contextos HKDF y forward secrecy**  
**Recomendación: Sí, enriquece el contexto.**

Mantén la base `"ml-defender:{component}:v1:{tx|rx}"` pero añádele un identificador de sesión dinámico. Ejemplos buenos:

- `"ml-defender:{component}:v1:tx:{session_id}"`
- o incluir timestamp de creación de sesión (en formato UNIX o ISO8601 compacto) si no quieres almacenar session_id extra.

Razones (best practices HKDF):
- El parámetro *info* (contexto) debe ser único por uso derivado para garantizar separación criptográfica.
- Añadir session_id o timestamp mejora el aislamiento entre sesiones sin necesidad de rotar el seed maestro (lo cual es costoso y no siempre deseable).
- No afecta forward secrecy real (que vendría de ratchets o ephemeral keys), pero sí reduce el blast radius si una sesión se ve comprometida.

Puedes hacerlo opcional: si no hay session_id, usar solo la parte estática. Es barato y da más robustez.

**P2 — Migración CryptoManager → CryptoTransport (DAY 98)**  
**Recomendación: Big-bang controlado, con rollback preparado.**

Dado que `CryptoManager` usa el seed directamente (uso documentado como incorrecto), dejarlo conviviendo crea riesgo de caminos duales.

Propuesta práctica:
1. DAY 98: integrar `CryptoTransport` en los 6 componentes.
2. Cambiar todas las llamadas simultáneamente (big-bang).
3. Mantener `CryptoManager` como “deprecated shim” durante 1-2 días (que internamente use `CryptoTransport` con contexto legacy si es necesario).
4. Una vez verificado en staging/producción, eliminar el shim.

Si el sistema permite despliegue azul-verde o canary, úsalo. Pero no dejes las dos implementaciones vivas mucho tiempo.

**P3 — mlock() en seed_client.cpp (DEBT-CRYPTO-003a)**  
**Recomendación: Advertencia + fallback seguro, no error fatal.**

En entornos con memoria limitada (hospitales, edge devices antiguos) `mlock()` puede fallar legítimamente con `ENOMEM`. Hacerlo fatal rompería despliegues reales.

Buena práctica:
- Intentar `mlock()`.
- Si falla → `sodium_mlock` fallback o simplemente `sodium_mprotect_noaccess` donde sea posible.
- Loggear como **WARNING** (nivel alto, con alerta) pero continuar.
- Documentar claramente: “El seed no pudo bloquearse en RAM. Recomendamos aumentar ulimit o usar hardware con más memoria.”

Esto mantiene seguridad por defecto sin sacrificar disponibilidad.

**P4 — TEST-INTEG-1/2**  
**Recomendación: Target separado `make test-integ` (o `ctest -R integ`).**

Los tests E2E que requieren `seed.bin` real + `sudo provision.sh` no deben correr en el `ctest` normal de CI/desarrolladores.

Estructura recomendada:
- `make test` o `ctest` → solo unit + integration ligera (mocked seeds).
- `make test-integ` o `ctest -R "^TEST-INTEG"` → requiere provision previa y root (o capabilities para mlock).
- Documentar en README: “Para tests de integración completos: sudo tools/provision.sh && make test-integ”

Así CI sigue rápido y los tests pesados quedan explícitos.

### Observaciones menores / sugerencias

- En el nonce: considera añadir un prefijo de 32 bits no cero si en el futuro puedes tener múltiples “senders” dentro del mismo componente (buena defensa en profundidad, aunque ahora no sea necesario).
- Documenta en el ADR-013 el motivo de salt=32×0 y el contexto estático vs dinámico.
- Muy bien el `Co-authored-by: ... + Claude`. El trabajo en equipo se nota.

**Estado actual del proyecto:** muy sólido en la capa criptográfica. DAY 98 (migración) será el siguiente gran paso, pero ya tienes bases excelentes.

Quedo a la espera de tu actualización de DAY 98 o cualquier aclaración que necesites del Consejo.

*Via Appia Quality: piano piano, stone by stone.*  
Sigue así, Alonso.

— **Grok (xAI)**, en nombre del Consejo de Sabios  
25 de marzo de 2026