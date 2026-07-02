# PROMPT DE CONTINUIDAD — DAY 205 (continúa DAY 204)
# Instrucciones generales para Claude:

1. Piensa antes de codificar
   Expón tus suposiciones. Pregunta cuando no estés seguro. Nunca adivines.

2. Simplicidad primero
   Escribe el código mínimo que resuelva el problema.
   Sin abstracciones que nadie pidió.

3. Cambios quirúrgicos
   No toques código no relacionado con la solicitud.
   Cada línea cambiada debe rastrearse hasta lo que se pidió.

4. Ejecución orientada a metas
   Convierte instrucciones vagas en criterios de éxito verificables
   antes de escribir una sola línea.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria; trazar hacia atrás desde el binario.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable durable y verificable; Kuzu = proyección reconstruible).
- **EMECAS++** antes de cualquier merge · **PR obligatorio**.
- **Consejo de Sabios** (8 modelos) ratifica decisiones de arquitectura.
- Python3 heredoc (lectura→memoria→escritura) para editar ficheros en macOS · NUNCA `sed -i` · `vagrant ssh -c` para comandos del VM (multi-VM: nombrar máquina, p.ej. `vagrant ssh defender -c`) · commits/push desde el HOST.
- Un día, una batalla. Features pequeñas (días, no semanas), merge frecuente a main vía EMECAS++.
- Antes de escribir código nuevo que reimplemente lógica existente: extraer y compartir, no duplicar (lección DAY 204 — el fallo de `test_correlation_roundtrip` fue justo un campo de observabilidad que no se compartía entre producción y test).

## Estado al cierre de DAY 204 — Eslabón 0 CERRADO (3/3) + emecas+++ verde en main

**DAY 204 cerró tres cosas:** el fix real de `DEBT-CORRELATION-ROUNDTRIP-ORPHANED-001`
(causa raíz distinta de la sospechada), el primer gate E2E río-abajo del circuito
(`emecas+++`), y el target correspondiente en el Makefile. EMECAS++ completo corrió
verde en `main` tras los merges — pipeline 6/6 RUNNING confirmado, Vault dev activo.

1. **`DEBT-CORRELATION-ROUNDTRIP-ORPHANED-001` — CERRADA.** La nota de DAY 203 decía
   "nunca estuvo enganchado a `add_test`" — **falso**, medido: el `add_test` sí estaba
   en `tests/CMakeLists.txt`. La causa real era cache de CMake sin reconfigurar en la
   VM. Tras reconfigurar, el test compiló y corrió, pero falló RED contra el bronce
   segmentado de DAY 203: `Stats::current_file` devolvía `current_tmp_path_` (el
   `.csv.tmp` en curso), y el propio `finalize_segment_locked()` hacía desaparecer
   ese path al renombrarlo — el test leía un nombre que el rename correcto volvía
   inexistente. Fix: campo nuevo `Stats::current_final_path` en
   `correlation_writer.hpp/.cpp`, sin tocar la semántica de `current_file`. 4/4 PASSED.

2. **`emecas+++` — circuito completo bronce→Kuzu (ADR-058 §1).** `process_segment`
   extraída de la lambda inline de `main.cpp` a `segment_processor.{hpp,cpp}` (nueva
   lib compartida), para que producción y el test nuevo ejerzan el mismo código —
   lección directa del punto 1. `test_bronze_to_kuzu_circuit.cpp`
   (`correlation-engine/tests/`): un solo proceso, FS puro (sin ZMQ — eso es
   Eslabón 1+). Dos casos: camino feliz (writer real → bronce → `process_segment`
   real → `KuzuGraphSink` real → `MATCH` en Kuzu) y fila con HMAC roto (nunca llega
   al grafo). CMake cruza a `ml-detector` igual que `test_correlation_roundtrip.cpp`
   cruza en sentido inverso — mismo patrón ya establecido, sin árbol de CMake
   compartido (confirmado: no hay `CMakeLists.txt` raíz, cada componente compila
   aislado, orquestado por el `Makefile`).

3. **Target `emecas+++` en el Makefile.** Alias simple de `emecas++` por ahora — el
   test de circuito ya corre dentro de `correlation-engine-test` → `test-components`
   → `test-all`, heredado sin lógica nueva. Hueco formado para cuando exista
   Eslabón 1: entonces `emecas+++` gana sus propios Actos río-abajo.

4. **`docs/BACKLOG.md` y `README.md` actualizados** con las entradas de DAY 201-204
   (script Python aplicado, pendiente de verificación visual con `git diff` si no
   se hizo ya al inicio de esta sesión).

## Deudas cerradas DAY 201-204
- `DEBT-CONFIG-BRONZE-HARDCODE-001` (P0) — CERRADA DAY 201+202 (writer + reader).
- `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` (P0) — CERRADA DAY 203 (segmentación + watcher).
- `DEBT-CORRELATION-ROUNDTRIP-ORPHANED-001` (P1) — CERRADA DAY 204 (`Stats::current_final_path`).

## Rama
`main`, al día. Ramas `day204/close-roundtrip-orphaned` y `day204/emecas-plus-plus-target`
fusionadas y borradas (local + remoto). Sin rama de trabajo abierta — DAY 205 empieza limpio.

## Acciones DAY 205 (en orden)

1. **Diseñar Eslabón 1 (Landing Zone: bronce → AVRO → Parquet oro) antes de implementar.**
   ADR-058 v3 ya fija el **contrato de aceptación** (predicado de equivalencia §3.1,
   bit-exactitud, canonicalización IEEE 754, orden determinista, HMAC heredado), pero
   marca Flujo A explícitamente como **"Greenfield"** — sin esquema AVRO concreto, sin
   layout de partición, sin lenguaje del converter decidido
   (`DEBT-CIRCUIT-PARSER-CROSSLANG-001` lo dice literalmente: *"el lenguaje del Flujo A
   aún no está decidido"*). Diseñar esto en tiempo real durante la implementación sería
   el "inventar en la calzada" que el propio ADR dice evitar. Antes de escribir código:
   - Definir esquema AVRO de las columnas del contrato `correlation_v1` + las nuevas
     materializadas del oro (`flow_start_window`, ver `DEBT-GOLD-NODE-DIMENSION-001`).
   - Decidir lenguaje del converter (C++ reusando `parse_double`/`encode_flow_input`
     directamente, vs Python con parser correct-rounding — ver precondición de
     `DEBT-CIRCUIT-PARSER-CROSSLANG-001`).
   - Decidir estructura de directorio/partición del Parquet oro.
   - Diseño pasa por el Consejo antes de implementar (o al menos queda trazado en un
     ADR/documento corto, coherente con "medir, no votar").
2. **Tras el diseño, primer sub-tramo pequeño de Flujo A** (un día, una batalla) —
   probablemente: escribir el converter mínimo que lee un segmento bronce y produce
   un Parquet con las columnas D (deterministas-de-dato) del predicado §3.1, sin aún
   el test de equivalencia completo.
3. **Verificar aplicación de la actualización de docs** (`docs/BACKLOG.md` +
   `README.md`) si no se confirmó al cierre de DAY 204 — `git diff` limpio esperado.

## Deudas abiertas relevantes para Eslabón 1 (ya trazadas en ADR-058, no inventar)
- `DEBT-GOLD-NODE-DIMENSION-001` (P0) — materializar `flow_start_window` como columna del oro.
- `DEBT-GOLD-INTEGRITY-HMAC-001` (P0) — HMAC por-fila heredado + firma del Parquet consolidado.
- `DEBT-CIRCUIT-PARSER-CROSSLANG-001` (P1) — paridad de parsing cross-language, precondición del converter.
- `DEBT-CIRCUIT-SCORE-NONTRIVIAL-REVAL-001` (P1) — el test de equivalencia es necesario pero no suficiente mientras los scores ML sean placeholder.
- `DEBT-EVENT-ID-FACTORY-001` (P1) — origen/preservación de `event_id` en el converter.

## Punteros
- `correlation-engine/include/correlation_engine/segment_processor.hpp` + `.cpp` — lógica compartida producción/test (DAY 204).
- `correlation-engine/tests/test_bronze_to_kuzu_circuit.cpp` — circuito completo, referencia de patrón para tests futuros de Eslabón 1.
- `ml-detector/include/correlation_writer.hpp` — `Stats::current_final_path` (DAY 204).
- `docs/adr/ADR-058-circuito-completo-aguas-abajo-v3.md` — contrato de Flujo A, leer §3.1 y §5-6 antes de diseñar el esquema.
- `Makefile` — target `emecas+++` (línea ~3024).

*Via Appia Quality — Un escudo que aprende de su propia sombra.*