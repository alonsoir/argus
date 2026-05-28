Claro. Vamos por partes.

---

## DAY 163 — Resumen

**Estado:** EMECAS++ ✅ verde — rama lista para merge a main.

**Lo que hicimos hoy:**

1. **EMECAS++ bloqueado** — `test_ntp_health_check` triplicado en `common/CMakeLists.txt` impedía compilar con `-DARGUS_VAULT_ENABLED=ON` en el Acto I del gate enterprise.

2. **Root cause** — Regresión de DAY 167 (DEBT-ARGUSPP-NTP-001): el target fue añadido tres veces de forma incremental sin detectar duplicados porque el build normal (sin la flag vault) nunca activaba el bloque condicional que los exponía simultáneamente.

3. **Fix** — `sed -i '291,302d;387,398d' common/CMakeLists.txt` — eliminadas las dos definiciones duplicadas, conservada la canónica en línea 68.

4. **Commit** — `fix(common): remove duplicate test_ntp_health_check targets (DEBT-ARGUSPP-NTP-001 DAY 167 regression)`

5. **EMECAS++ verde** — 3 Actos completos en 1h 3m 26s.

**Deuda técnica registrada:**
- `DEBT-CMAKE-DUPLICATE-TARGETS-001` — Ausencia de guard contra targets duplicados en CMakeLists condicionales. Propuesta: añadir `if(NOT TARGET test_ntp_health_check)` como patrón estándar para todos los targets dentro de bloques condicionales.

---

## DAY 164 — Plan

**Prioridad principal: BACKLOG-CRYPTO-VENDOR-KEY-001**
- Mover `vendor.key` a Vault (ruta `secret/argus/enterprise/vendor-key`)
- Leer la clave pública desde variable de entorno Jenkins (`ARGUS_VENDOR_PUBKEY_HEX`)
- AppRole por componente (Jenkins + Vault producción-ready)

**Secundario:**
- DEBT-CONFIG-JINJA2-PIPELINE-001 — generación de contratos JSON desde templates Jinja2
- DEBT-PACKAGE-DEB-001 — builds de paquetes Debian (deferred desde DAY 161)

---

## Preguntas para el Consejo de Sabios

**1. Patrón CMake para targets condicionales**
El bug de hoy revela un patrón peligroso: targets definidos dentro de bloques `if(ARGUS_VAULT_ENABLED)` que duplican targets ya existentes fuera. ¿Recomendáis el guard `if(NOT TARGET <nombre>)` como invariante obligatorio, o preferís refactorizar los CMakeLists para que los targets enterprise sean siempre únicos con nombre distinto (p.ej. `test_ntp_health_check_vault`)?

**2. BACKLOG-CRYPTO-VENDOR-KEY-001 — scope DAY 164**
El Consejo aprobó el roadmap de 8 fases con veto de merge hasta Fases 0-4. ¿La lectura del pubkey desde variable de entorno Jenkins cubre completamente la Fase 1 (vendor.key en Vault), o requiere también el AppRole por componente en la misma jornada para considerarla cerrada?

**3. EMECAS++ Acto I — cobertura enterprise**
El Acto I compila con `ARGUS_VAULT_ENABLED=ON` pero todavía usa `SeedFileProvider` en el bootstrap de la VM (Modelo B efímero). ¿Debería EMECAS++ Acto I exigir que el test E2E vault use `VaultProvider` real, o es suficiente que compile y los tests unitarios pasen hasta que BACKLOG-CRYPTO-VENDOR-KEY-001 esté cerrado?

---

¿Añadimos algo, o lo volcamos al DAILY.md?