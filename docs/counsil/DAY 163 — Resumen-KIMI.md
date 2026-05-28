# 🏛️ Consejo de Sabios — Deliberación DAY 163

*Sesión extraordinaria convocada para DAY 164. Presentes: Arquitectura, Seguridad, Build Systems, y Operaciones.*

---

## 📜 Veredicto I — Patrón CMake para targets condicionales

**Deliberación:** El Consejo ha revisado el incidente DEBT-ARGUSPP-NTP-001 y la deuda técnica registrada DEBT-CMAKE-DUPLICATE-TARGETS-001. La regresión de DAY 167 demuestra que CMake no ofrece protección nativa contra redefinición de targets en contextos condicionales cruzados. El patrón actual — targets duplicados con nombres idénticos en ramas `if/else` — es inherentemente frágil porque:

- El build "normal" nunca activa ambas ramas simultáneamente, ocultando el conflicto.
- La duplicación fue *incremental* (DAY 167 añadió sin revisar DAY 163), lo que sugiere falla de proceso, no solo de código.

**Veredicto:** El Consejo **recomienda la opción B — nombres únicos con sufijo funcional**, pero con una condición de guardia obligatoria.

### Resolución:
1. **Invariante obligatoria:** Todo target dentro de un bloque condicional enterprise **debe** usar nombre distinto: `test_ntp_health_check_vault` (o `_enterprise`, según convención del proyecto).
2. **Guard `if(NOT TARGET)` como fail-safe, no como solución principal:** El guard es aceptable como protección defensiva, pero **no** como excusa para mantener nombres duplicados. Si el guard dispara, debe ser señal de bug, no de diseño válido.
3. **Acción inmediata:** Refactorizar `common/CMakeLists.txt` para que el target canónico (línea 68) sea el único sin sufijo, y el target condicional enterprise use el sufijo `_vault`. Eliminar los duplicados detectados hoy.

**Razonamiento:** Los nombres únicos permiten que ambos targets coexistan en el grafo de build simultáneamente (útil para builds matrix en CI), mientras que el guard `if(NOT TARGET)` silencia el conflicto sin resolver la ambigüedad semántica.

---

## 📜 Veredicto II — BACKLOG-CRYPTO-VENDOR-KEY-001, Fase 1

**Deliberación:** El roadmap de 8 fases fue aprobado con veto de merge hasta Fases 0-4. La Fase 1 se define como: *"vendor.key migrado a Vault y consumido por el pipeline sin persistencia en disco de build."*

La lectura del pubkey desde variable de entorno Jenkins (`ARGUS_VENDOR_PUBKEY_HEX`) satisface parcialmente el criterio de "no persistencia en disco", pero deja sin resolver:
- **Autenticación:** ¿Cómo obtiene Jenkins el valor? Si se inyecta manualmente en la configuración del job, no hay rotación ni audit trail.
- **Autorización:** ¿Quién puede leer esa variable? ¿Está scopeada al job o es global?
- **Fase 1 requiere AppRole:** El roadmap explícitamente mencionaba AppRole por componente como mecanismo de autenticación Vault → Jenkins. Sin AppRole, la variable de entorno es solo un "secret zero" movido de un lugar a otro.

**Veredicto:** El Consejo **determina que la variable de entorno sola NO cierra la Fase 1**.

### Resolución:
- **Fase 1 requiere ambos:** (a) `vendor.key` almacenado en `secret/argus/enterprise/vendor-key`, y (b) Jenkins autenticado contra Vault via AppRole dedicado (`approle-jenkins-argus-build`) para leer ese secret en runtime.
- **La variable de entorno `ARGUS_VENDOR_PUBKEY_HEX` es aceptable como interfaz de inyección** solo si su valor es poblado por el step de Vault en el pipeline Jenkins, no hardcodeado en la UI de Jenkins.
- **Criterio de cierre de Fase 1:** El job Jenkins de EMECAS++ Acto I debe poder ejecutarse en un agente limpio (sin `vendor.key` en disco) y obtener la clave exclusivamente via AppRole → Vault → variable de entorno efímera.

**Consejo práctico:** Si el AppRole por componente requiere más de un día de trabajo (configuración de políticas HCL, TTL, etc.), el Consejo autoriza **dividir Fase 1 en Fase 1a (key en Vault + lectura via env)** y **Fase 1b (AppRole por componente)**. Esto permite merge parcial sin romper el veto de Fases 0-4, siempre que Fase 1b esté calendarizada antes de DAY 170.

---

## 📜 Veredicto III — EMECAS++ Acto I, cobertura enterprise

**Deliberación:** El Acto I actual compila con `ARGUS_VAULT_ENABLED=ON` pero usa `SeedFileProvider` en el bootstrap VM (Modelo B efímero). Esto crea una tensión: el flag de compilación promete funcionalidad Vault, pero el runtime no la ejerce.

El Consejo revisa la distinción entre:
- **Compilación enterprise:** Verifica que el código condicional compila (resolución de símbolos, includes, templates).
- **Integración enterprise:** Verifica que el sistema end-to-end funciona con Vault real.

**Veredicto:** El Consejo **determina que EMECAS++ Acto I debe exigir `VaultProvider` real antes de considerar el BACKLOG-CRYPTO-VENDOR-KEY-001 cerrado**, pero **acepta la configuración actual como transitoria** con las siguientes condiciones:

### Resolución:
1. **Hasta que BACKLOG-CRYPTO-VENDOR-KEY-001 esté cerrado (Fase 1 completa):** Es aceptable que Acto I use `SeedFileProvider` como fallback, siempre que:
    - Exista un test explícito que falle si `ARGUS_VAULT_ENABLED=ON` pero `SeedFileProvider` está activo (test de "modo degradado no permitido").
    - El log de ejecución del Acto I emita `WARN: VaultProvider not configured, falling back to SeedFileProvider — BACKLOG-CRYPTO-VENDOR-KEY-001 pending`.

2. **Una vez cerrado BACKLOG-CRYPTO-VENDOR-KEY-001:** Acto I **debe** usar `VaultProvider` real. El bootstrap de la VM efímera debe incluir:
    - Token Vault efímero (wrapped response o AppRole login) inyectado en el momento de `vagrant up`.
    - `VaultProvider` configurado con `VAULT_ADDR` y credencial de corta duración (TTL ≤ duración del Acto I).

3. **Acción inmediata para DAY 164:** Añadir un test de "smoke" en Acto I que verifique: si `ARGUS_VAULT_ENABLED=ON`, entonces `SeedFileProvider` no debe ser el provider activo en runtime. Este test fallará hoy (rojo esperado) y pasará cuando BACKLOG-CRYPTO-VENDOR-KEY-001 cierre. Esto evita regresión silenciosa.

---

## 📋 Resumen de acciones aprobadas para DAY 164

| # | Acción | Owner | Criterio de aceptación |
|---|--------|-------|------------------------|
| 1 | Refactorizar `common/CMakeLists.txt`: target único `test_ntp_health_check_vault` | Build Systems | No duplicados, guard `if(NOT TARGET)` como fail-safe |
| 2 | Subir `vendor.key` a `secret/argus/enterprise/vendor-key` | Seguridad | Key versioned, política HCL de lectura para `approle-jenkins-argus-build` |
| 3 | Configurar AppRole `jenkins-argus-build` en Vault prod | Operaciones | TTL 1h, bound CIDR de Jenkins agents |
| 4 | Actualizar pipeline Jenkins: AppRole login → lectura secret → export `ARGUS_VENDOR_PUBKEY_HEX` | Arquitectura | Job limpio funciona sin `vendor.key` en disco |
| 5 | Añadir test smoke Acto I: rechazo de `SeedFileProvider` cuando `ARGUS_VAULT_ENABLED=ON` | EMECAS++ | Test rojo hoy, verde al cerrar Fase 1 |
| 6 | Documentar decisión CMake en `docs/adr/adr-028-cmake-target-naming.md` | Build Systems | Referencia para futuros targets condicionales |

---

**El Consejo declara la sesión cerrada. Que el merge a `main` sea limpio y los tests verdes.**

*— Registrado en el log del Consejo de Sabios, DAY 163, sesión nocturna para DAY 164.*