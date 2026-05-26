# Consejo de Sabios — DAY 165
## Validación Enterprise: diseño de EMECAS++

**Fecha:** 26 de Mayo 2026
**Árbitro:** Alonso Isidoro Román (PI, aRGus NDR)
**Rama activa:** `feature/day161-enterprise-crypto-integration`
**arXiv:** 2604.04952

---

## Contexto — qué hemos construido (FASES 0-4)

El pipeline aRGus tiene dos modos de operación:

| Modo | CryptoProvider | Keypair | Epoch rotation |
|------|---------------|---------|----------------|
| **Community** (OSS) | `SeedFileProvider` | estático, `seed.bin` | no |
| **Enterprise** | `VaultProvider` | efímero, `vendor.key` nunca en disco | sí, coordinado |

**Lo implementado (DAY 161-165):**
- FASE 0: `vendor.key` → Vault dev. Modelo B: cada `vagrant destroy+up` genera un nuevo keypair y lo borra de disco. Solo existe en Vault.
- FASE 1: `CryptoProviderHandle` RCU. Hot-reload atómico de la clave activa sin parar el pipeline.
- FASE 2a/b: `HttpEtcdRegistrar` + `CryptoEpochCoordinator`. Watch real sobre `/argus/crypto/epoch` en etcd.
- FASE 3: Wire header extendido 4B→8B: `[uint32_t size][uint16_t epoch_id][2B reserved]`. El firewall selecciona la clave correcta antes de descifrar.
- FASE 4: `test_e2e_rotation` 5/5, `test-e2e-vault` PASSED con Vault dev real.
- EMECAS++ OSS verde hoy: test-all + test-e2e-synthetic-full + test-e2e-synthetic-firewall.

**EMECAS actual (OSS):**
```
vagrant destroy -f && vagrant up && make bootstrap && make test-all && make test-e2e-synthetic
```
Valida exclusivamente el modo Community. Enterprise queda sin gate de validación.

---

## El problema

El Consejo de Sabios votó 8/8 en DAY 162:
> "Veto a merge a main hasta Fases 0-4 verdes **con EMECAS**."

EMECAS+ OSS está verde. Pero no existe todavía un protocolo formal para validar que el modo enterprise funciona end-to-end en un entorno reproducible desde cero. Antes de mergear necesitamos definir ese protocolo y obtener aprobación del Consejo.

---

## Propuesta de EMECAS Enterprise

**Propuesta base `make emecas-enterprise`:**

```
vagrant destroy -f && vagrant up    # incluye vault-enterprise-bootstrap
make bootstrap                      # igual que OSS
make test-all                       # gate OSS (sin cambios)
make test-enterprise                # NUEVO — ver detalle abajo
make test-e2e-synthetic             # gate OSS e2e
make test-e2e-enterprise            # NUEVO — ver detalle abajo
```

**`make test-enterprise` incluiría:**
- `test_e2e_rotation` (ya existe, 5/5 con FakeEtcdServer — determinista)
- `test_crypto_epoch_coordinator` (ya existe)
- `test_crypto_autonomy` (ya existe)
- `test_crypto_provider_community` (ya existe)
- Verificación: Vault aún contiene `vendor-key`, `vendor-pubkey`, `token` (script bash idempotente)
- Verificación: `epoch_id != 0` en wire header post-arranque enterprise

**`make test-e2e-enterprise` incluiría:**
- Arrancar pipeline en modo enterprise (VaultProvider activo)
- Inyectar 100 eventos vía `synthetic_sniffer_injector`
- Verificar delta: `firewall.events_processed += 100` y `crypto_errors == 0`
- Simular epoch rotation (script que incrementa epoch en etcd)
- Verificar que pipeline sigue procesando post-rotation sin drops
- Verificar que `epoch_id` en wire header refleja el nuevo epoch

**Tiempo estimado total:** ~15-20 minutos (Vault bootstrap + tests + e2e).

---

## Preguntas al Consejo

### Pregunta 1 — Arquitectura del protocolo

¿Debería `emecas-enterprise` ser:

**(A) Superset** — ejecuta OSS + enterprise en una sola invocación (un único `make emecas-enterprise`). Más simple de mantener, tiempo total mayor, un solo punto de fallo.

**(B) Dos targets paralelos** — `make emecas-oss` y `make emecas-enterprise` independientes. Permite correr solo el enterprise cuando el OSS ya está validado. Más flexible para el día a día, ligeramente más complejidad en el Makefile.

**(C) Targets anidados** — `make emecas` = OSS, `make emecas++` = OSS + enterprise. Naming intuitivo para el proyecto, no introduce cambios breaking en los targets actuales.

¿Cuál es la estructura más robusta y mantenible a largo plazo?

---

### Pregunta 2 — Vault dev como gate suficiente

`vagrant up` provisiona automáticamente un Vault dev con el keypair efímero (Modelo B). Este Vault:
- Es efímero (muere con `vagrant destroy`)
- Corre en modo `dev` (datos en memoria, sin TLS real, sin HA)
- Es suficiente para tests funcionales

¿Es Vault dev suficiente como gate de merge, o el Consejo considera que necesitamos:
- Un segundo Vagrantfile simulando el servidor central (con Vault en modo server/file)?
- Un test explícito de reconexión tras reinicios de Vault?

Aclaración: Vault HA real queda para hardware (RPi5 + N100). La pregunta es sobre el entorno mínimo aceptable para el gate de merge.

---

### Pregunta 3 — Live epoch rotation en EMECAS

`test_e2e_rotation` usa `FakeEtcdServer` (determinista, sin red). EMECAS enterprise podría incluir adicionalmente un test de rotación en vivo con el pipeline completo corriendo.

Opciones:

**(A) Solo FakeEtcdServer** — determinista, rápido, ya existe. La confianza en Vault real viene de `test-e2e-vault` (que ya pasa). Suficiente para gate de merge.

**(B) Live rotation con pipeline activo** — más costoso (~5 min extra), valida la secuencia completa: Vault emite nuevo epoch → `CryptoEpochCoordinator` propaga → `CryptoProviderHandle` hot-reload → wire header actualizado → firewall acepta nuevo epoch sin drops. Elimina el riesgo de bugs de integración que el FakeEtcdServer no detecta.

¿Cuál da la confianza necesaria para el gate de merge sin sobrecargar el protocolo?

---

### Pregunta 4 — Test negativo (epoch_id incorrecto)

EMECAS debería incluir un test de rechazo:
- Firewall recibe mensaje con `epoch_id` que no corresponde a ninguna clave activa
- Resultado esperado: `crypto_errors += 1`, mensaje descartado, pipeline continúa

¿Es este test un requisito del gate de merge o puede diferirse como deuda técnica (DEBT-CRYPTO-NEGATIVE-TEST-001)?

---

### Pregunta 5 — Gate de Jenkins

Jenkins está en desarrollo (feature separada, post-merge). El gate enterprise será manual (`make emecas-enterprise`) hasta que Jenkins esté listo.

¿Acepta el Consejo merge con gate manual, asumiendo que Jenkins se añadirá como BACKLOG-CI-ENTERPRISE-001 con P1 explícito?

O ¿considera el Consejo que Jenkins es un prerequisito del merge?

---

### Pregunta 6 — Naming y documentación

El protocolo OSS actual se documenta como "EMECAS" (Entorno Mínimo Ejecutable y Comparable de Arranque y Seguridad). Para el enterprise, propongo:

**(A) EMECAS-E** — sufijo explícito, documenta dos protocolos separados en README.md y en el arXiv paper.

**(B) EMECAS++** — ya usado informalmente. Redefinir oficialmente como "EMECAS OSS + enterprise".

**(C) TDH-Gate** — Gate unificado bajo la filosofía TDH, sin distinción explícita OSS/enterprise. Un único protocolo que valida ambos modos.

¿Qué naming refleja mejor la filosofía del proyecto para el paper y para la comunidad open-source?

---

## Información técnica de referencia para el Consejo

**Keypair activo hoy (ephémero, generado en este vagrant up):**
`a2abfe43e349e86ddeb4a22496b007919c87bdb0f5dc88c17b57cabf0d61331f`

**Tests enterprise existentes (todos verdes DAY 165):**
- `test_e2e_rotation`: 5/5 (FakeEtcdServer)
- `test_crypto_epoch_coordinator`: verde
- `test_crypto_autonomy`: verde
- `test_crypto_provider_community`: verde
- `test-e2e-vault`: PASSED (Vault dev real)

**Vault dev provisioned:** ✅ (via `vault-enterprise-bootstrap` en Vagrantfile)
**Wire header epoch_id:** ✅ propagado en todo el pipeline
**Jenkins:** ⏳ feature separada, post-merge

**Rama:** `feature/day161-enterprise-crypto-integration`
**Commits clave:** `ccaf6a13` (FASE 3), `c9cf172c` (FASE 4)

---

*El árbitro es Alonso. El Consejo delibera, propone, disensite. La decisión final es de Alonso.*