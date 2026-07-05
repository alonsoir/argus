## ESTADO ACTUAL (DAY 207) — GRADUADO A PRODUCCIÓN

**El código de `bronze_to_gold_converter.cpp` YA NO VIVE AQUÍ.** Se graduó de
prototipo a producción el DAY 207 (decisión de Alonso, consenso del Consejo de
Sabios durante la ratificación de Flujo B — ver
`docs/council/PROPUESTA -- Flujo B, parquet_to_kuzu_loader (DAY 207).md`).

**Ubicación actual del código:** `correlation-engine/tools/bronze_to_gold_converter.cpp`
(movido con `git mv`, historial de commits preservado; integrado en
`correlation-engine/CMakeLists.txt` como target de build oficial).

**Este fichero (`README.md`) se conserva intacto como registro histórico** del
proceso de diseño, el bloqueo real de HMAC encontrado DAY 205, y su
resolución DAY 206 — según decisión explícita de Alonso de no reescribir la
historia del diseño, solo mover el código ya verificado. Todo lo que sigue
debajo de esta línea describe el estado **DAY 205, ya superado**; no refleja
el estado actual del componente.

**Estado real hoy (DAY 207):** compilado vía CMake, verificado 24/24 filas
bit-idénticas contra el mismo segmento bronce real, tanto con el binario
compilado a mano (DAY 206) como con el nuevo target de CMake (DAY 207). Ver
`docs/BACKLOG.md` → "ACCION-3-DAY206 — Destino de bronze_to_gold_converter.cpp"
para el cierre formal de esta decisión.

---

# converter-prototype/ — ESTADO: NO VERIFICADO

`bronze_to_gold_converter.cpp` es un **borrador sin compilar ni ejecutar**, distinto
del `smoke/` (que sí está verificado 12/12, dos veces: sandbox + `defender`).

No confundir el nivel de madurez de ambos ficheros.

## Bloqueo actual (DAY 205)

El converter necesita `ARGUS_BRONZE_HMAC_KEY_HEX` para verificar filas de bronce
reales. Medido DAY 205: esa clave la sirve `SecretsManager::get_hmac_key()`
(`etcd-server/src/secrets_manager.cpp`), que la genera **en memoria pura**
(`store_key()` → `keys_storage_`, sin persistencia a disco — confirmado por
`find / -iname "*hmac*"` sin resultados fuera de headers de librerías del sistema).

Consecuencia: las claves que firmaron los segmentos de bronce ya existentes
(`logs/correlation/argus/2026-07-02-*.csv`) murieron con el proceso `etcd-server`
de aquella sesión. Son **irrecuperables** — no es un bug del converter, es el
comportamiento real (y no documentado hasta hoy) del `SecretsManager` actual.

## Para desbloquear (DAY 206)

1. Levantar `etcd-server` + `ml-detector` (pipeline mínimo, no todo EMECAS++).
2. Generar tráfico que dispare al menos una fila de correlación nueva.
3. Capturar la clave activa — `main.cpp:442` solo loguea la LONGITUD
   (`log->info("✅ [csv] HMAC key retrieved ({} chars)", key.size())`), no el
   valor. Instrumentar temporalmente o interceptar de otra forma.
4. Exportar `ARGUS_BRONZE_HMAC_KEY_HEX` con esa clave y compilar/correr el converter
   contra la fila fresca (no contra `2026-07-02-*.csv`, que ya no es verificable).

## Deuda candidata a registrar (no añadida aún al BACKLOG.md — pendiente de que Alonso decida el ID)

El `SecretsManager` in-memory-only implica que **cualquier reinicio del proceso
`etcd-server` invalida silenciosamente todas las filas de bronce ya firmadas**,
sin relación con el `grace_period_seconds`/`min_rotation_interval_seconds` de
ADR-004 (esa lógica protege rotación *voluntaria*, no muerte de proceso). Ninguna
fila de bronce sobrevive a un `pkill etcd-server` o crash. Candidato:
`DEBT-SECRETS-MANAGER-PERSISTENCE-001` (severidad a discutir — probablemente P1,
toca la inmutabilidad del ledger "Via Appia" si se llega a producción sin resolver).