## Respuestas del Consejo — Claude (Anthropic)

---

**Pregunta 1: Patrón CMake para targets condicionales**

Recomiendo `if(NOT TARGET <nombre>)` como invariante obligatorio, pero con matiz: no es suficiente por sí solo porque enmascara el bug en lugar de prevenirlo. El patrón correcto es dos cosas juntas:

Primero, la regla estructural: **ningún target de test debe definirse dentro de un bloque `if(ARGUS_VAULT_ENABLED)` si ya existe fuera**. Los bloques condicionales deben añadir *comportamiento* a targets existentes (compile definitions, link libraries), no *crear* targets nuevos que dupliquen los de fuera.

Segundo, el guard `if(NOT TARGET ...)` como red de seguridad para los casos donde la separación no sea posible.

Nombres distintos como `test_ntp_health_check_vault` los rechazo: añaden complejidad sin valor semántico real. El test es el mismo, no necesita un nombre distinto.

**Voto: invariante obligatorio `if(NOT TARGET)` + regla estructural documentada en CONTRIBUTING.md.**

---

**Pregunta 2: Scope de BACKLOG-CRYPTO-VENDOR-KEY-001**

La Fase 1 requiere **ambas cosas en la misma jornada**, no son separables:

Leer el pubkey desde variable de entorno Jenkins sin AppRole por componente es una Fase 1 a medias. Si Jenkins tiene acceso a `ARGUS_VENDOR_PUBKEY_HEX` pero todos los componentes comparten el mismo token Vault, el perímetro de compromiso es el sistema entero. El AppRole por componente es lo que convierte "vendor.key en Vault" de gesto cosmético en control real.

El orden concreto que propongo para DAY 164:

1. AppRole `argus-etcd-server`, `argus-ml-detector`, etc. con política read-only sobre su propio path.
2. `vendor.key` en `secret/argus/enterprise/vendor-key` accesible solo desde el AppRole correspondiente.
3. Jenkins lee `ARGUS_VENDOR_PUBKEY_HEX` desde Vault en tiempo de pipeline, no desde disco.
4. Test E2E que verifica que un AppRole de un componente **no puede leer** el secret de otro.

Sin el punto 4, la Fase 1 no está cerrada según ADR-049.

**Voto: AppRole + vendor.key + test de aislamiento = Fase 1 cerrada. Sin los tres, no.**

---

**Pregunta 3: EMECAS++ Acto I — cobertura enterprise**

Es suficiente que compile y los tests unitarios pasen **hasta que BACKLOG-CRYPTO-VENDOR-KEY-001 esté cerrado**, con una condición: el Acto I debe fallar explícitamente si se detecta que `VaultProvider` está activado (`ARGUS_VAULT_ENABLED=ON`) pero el token Vault no está disponible en el entorno. Es decir, el gate debe ser honesto sobre lo que está probando.

Lo que no acepto es que el Acto I pase silenciosamente usando `SeedFileProvider` cuando la flag dice `VaultProvider`. Eso es un gate que miente.

La solución pragmática para DAY 163-164: añadir un test de smoke en el Acto I que detecte si Vault dev está corriendo y, si lo está, exija que `VaultProvider::create()` no lance. Si Vault no está corriendo, el test hace skip documentado, no fail silencioso.

En cuanto BACKLOG-CRYPTO-VENDOR-KEY-001 esté cerrado (DAY 164 si el plan anterior se cumple), el Acto I debe promover ese smoke test a test obligatorio sin skip posible.

**Voto: suficiente hoy, con smoke test honesto. Obligatorio tras DAY 164.**

---

¿Volcamos esto al DAILY.md junto con el resumen, o prefieres que redacte el documento completo listo para commit?