# PROMPT DE CONTINUIDAD — DAY 208 (continúa DAY 205-207)
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
- **EMECAS++** antes de cualquier merge · **PR obligatorio** (main tiene branch protection — push directo rechazado, confirmado DAY 206 y de nuevo DAY 207).
- **Consejo de Sabios** (9 modelos: Claude, ChatGPT, DeepSeek, Gemini, GLM, Grok, Kimi, Mistral, Qwen) ratifica decisiones de arquitectura.
- Python3 heredoc (lectura→memoria→escritura) para editar ficheros en macOS · NUNCA `sed -i` · `vagrant ssh defender -c` para comandos del VM (defender = VM de desarrollo principal, lleva todo el peso; hay más VMs en el mismo Vagrantfile) · commits/push desde el HOST.
- Un día, una batalla. Features pequeñas (días, no semanas), merge frecuente a main vía EMECAS++.
- `.PHONY` en Makefile: lista separada por ESPACIOS, nunca comas (lección DAY 205).
- Al comitear y hacer push a una rama de trabajo, verificar SIEMPRE con `git log --oneline -3 <rama>` y `git log --oneline -3 origin/<rama>` que el commit realmente llegó (lección DAY 206).
- **Lección nueva DAY 207 — crear la rama de trabajo ANTES del primer commit, no después.** Un commit suelto se hizo directo sobre `main` local por trabajar sin rama abierta; el push lo rechazó branch protection (sin daño real: el commit se rescató con `git checkout -b <rama>` y `main` local se realineó con `git reset --hard origin/main`). Regla operativa: en cuanto haya trabajo suelto que comitear en una sesión, `git checkout -b day<N>/<slug>` es el PRIMER comando, no el último.
- **Lección nueva DAY 207 — pkg-config en shells no-interactivos.** `vagrant ssh <vm> -c "..."` no carga `.bashrc` de forma fiable, y el `.bashrc` de `defender` además apunta a `/usr/lib64/pkgconfig` (convención RedHat), mientras los `.pc` reales de Debian/Ubuntu viven en `/usr/lib/x86_64-linux-gnu/pkgconfig`. Cualquier target de Makefile o CMakeLists que dependa de `pkg-config` en shell no-interactivo debe exportar `PKG_CONFIG_PATH` explícitamente (con el doble-escape `\$$` que Make exige para emitir un `$` literal al shell remoto) en vez de asumir que el entorno lo resuelve solo.
- **Lección nueva DAY 207 — no asumir que un target de `test-all` cubre lo que parece cubrir.** Antes de lanzar `emecas+++` (20-30 min, `vagrant destroy` incluido), se verificó a mano la cadena de dependencias del Makefile (`emecas+++`→`emecas++`→`emecas`→`test-all`→`test-components`→`correlation-engine-test`) para confirmar que el gate realmente ejercitaba los cambios de la sesión, y se descubrió que `test-parquet` (otra dependencia de `test-all`) es un pipeline legacy no relacionado (`schema_ml_detector`/`schema_firewall`, mayo), no algo que tocara el trabajo de Eslabón 1.

## Estado al cierre de DAY 207 — Canonicalización unificada, Flujo B ratificado, converter graduado, EMECAS+++ verde, mergeado a main

### Resumen de lo cerrado hoy

1. **Brecha real encontrada y cerrada: canonicalización IEEE754 divergía entre Camino 0 y Flujo A+B.**
   Durante el diseño del test de equivalencia parcial (predicado §3.1, ADR-058),
   se detectó que `parse_and_verify` (consumido tanto por Camino 0 vía
   `segment_processor.cpp` como por el converter de Flujo A) nunca canonicalizaba
   NaN/-0.0 en los 3 scores — solo el converter lo hacía, y solo localmente en su
   propio `.cpp` (duplicado además en el smoke test). Si una fila de bronce trae
   NaN/-0.0, Kuzu (Camino 0) y el Parquet (Flujo A+B) habrían divergido bit a bit
   en el score, con el mismo `flow_uid`.
   **Corrección:** nuevo header `correlation-engine/include/correlation_engine/
   canonical_double.hpp`, aplicado dentro de `parse_and_verify`
   (`correlation-engine/src/correlation_reader.cpp`) tras la verificación HMAC —
   punto único real, porque `parse_and_verify` es el confluente de ambos caminos,
   no "el converter" como decía la fila 16a de ADR-058 v3 (corregida con una
   sección "Corrección post-v3 DAY 207" en el propio ADR).
   **Verificado:** 2 tests nuevos en `test_correlation_reader.cpp`
   (`CanonicalizesNaNScore`, `CanonicalizesNegativeZeroScore`, bit-exacto vía
   `std::bit_cast`) — 8/8 PASSED. Suite completa del correlation-engine — 7/7
   PASSED, sin regresión en Camino 0. El converter retiró su copia local;
   recompilado, 24/24 filas idénticas al resultado previo.
   Deuda registrada y cerrada el mismo día: `DEBT-CIRCUIT-CANONICALIZE-PARITY-001`.

2. **Diseño de Flujo B (`parquet_to_kuzu_loader`) ratificado por el Consejo (9/9).**
   Propuesta en `docs/council/PROPUESTA -- Flujo B, parquet_to_kuzu_loader (DAY 207).md`,
   con resolución final anexada al mismo fichero. Decisiones:
   - **(a)** Lector-puro-reusa-sink — unánime. No amplía `IGraphSink`/`KuzuGraphSink`.
   - **(b)** Chunking — **desviación deliberada de la mayoría del Consejo**
     (que proponía assert-y-diferir): Alonso decidió **bucle multi-chunk completo
     desde el primer commit**, con `WARNING` (no excepción/fail-fast) si
     `num_chunks() > 1` — procesa todo correctamente siempre, solo avisa cuando
     el supuesto de "ficheros pequeños" deja de cumplirse, sin cortar ejecución.
   - **(c)** `ingested_at`/`seq_in_window` — unánime, sin tratamiento especial,
     ya excluidos del predicado §3.1 por ADR-058 v3.
   - **(d)** Ubicación — resuelta hoy mismo por la decisión de la acción 3
     (ver punto 3 abajo): `correlation-engine/tools/`, junto al converter.
   Hallazgos del Consejo incorporados al diseño (pendientes de codificar):
   manejo de error explícito si el Parquet gold no existe (GLM); nota de punto
   único de verdad, el loader no conoce Cypher/Kuzu (ChatGPT).
   **`parquet_to_kuzu_loader.cpp` NO existe todavía como código** — solo el
   diseño ratificado. Es la acción 1 de DAY 208.

3. **Acción 3 (pendiente desde DAY 206) resuelta: converter GRADUADO a producción.**
   `bronze_to_gold_converter.cpp` movido con `git mv` de
   `docs/design/eslabon-1-flujo-a-avro-parquet/converter-prototype/` a
   `correlation-engine/tools/bronze_to_gold_converter.cpp` (historial preservado).
   Integrado en `correlation-engine/CMakeLists.txt` como target de build oficial
   (nuevo bloque `pkg_check_modules` para avro-c/arrow/parquet, con el fallback
   defensivo de `PKG_CONFIG_PATH` de la lección de arriba). Sin `add_test` —
   herramienta/medición ejecutada a mano, mismo patrón que `kuzu_concurrency_smoke`.
   Verificado: compilado vía `cmake --build . --target bronze_to_gold_converter`,
   24/24 filas bit-idénticas al binario compilado a mano antes de la integración.
   El `README.md` de la carpeta de diseño original se conserva íntegro (decisión
   explícita de Alonso: no reescribir el historial), con un banner nuevo al
   principio señalando el estado actual y la nueva ubicación del código.
   Cierre formal registrado en BACKLOG.md como "ACCION-3-DAY206... — RESUELTO".

4. **Deudas nuevas registradas — ambas con fundamento real, no especulativo:**
   - `DEBT-KUZU-CONTINUITY-001` (P2) — KuzuDB fue **archivado el 10 de octubre de
     2025** (mismo día del release final `0.11.3`, la versión pineada del
     proyecto); causa revelada en filing EU DMA de febrero 2026: **Apple adquirió
     Kùzu Inc. el 9 de octubre de 2025**. Verificado por Claude vía búsqueda web
     independiente, no aceptado solo por la palabra de un modelo del Consejo
     (Kimi lo señaló primero). **Decisión de Alonso: NO depreciar hoy.** El
     objetivo actual es demostrar la hipótesis de que los datasets generados por
     el pipeline vía grafo son de calidad suficiente para inferir datasets
     comportamentales académicos — no entregar una demo. Evaluación de migración
     diferida a: (i) hipótesis demostrada → estudio post-FEDER con fondos ya
     asegurados, o (ii) impedimento técnico real en Kuzu 0.11.3 que bloquee la
     demostración. No antes.
   - `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` (P1, bloqueante para Flujo B
     *completo*, no para la v1) — el Parquet gold de producción real puede
     combinar aRGus + Suricata + Zeek + Wazuh con activación configurable por
     señal (necesario para el método científico: aislar el efecto de cada
     señal). **La ratificación del Consejo de hoy sobre Flujo B cubre solo el
     esquema mono-fuente `correlation_v1`** — el caso multi-sensor no estaba en
     el documento enviado, así que no fue evaluado por nadie. Requiere su propia
     sesión de diseño + su propia ronda de Consejo antes de que Flujo B se
     considere completo para producción real. La v1 se construye contra el
     esquema mono-fuente ya ratificado.

5. **EMECAS+++ verde — reconstrucción completa desde `vagrant destroy -f && vagrant up`.**
   Confirma que el `CMakeLists.txt` actualizado (converter graduado) y la
   canonicalización sobreviven un provisioning limpio, no solo la VM con
   dependencias puestas a mano. `correlation-engine-test` (dentro de
   `test-components`, dentro de `test-all`) ejercitó los tests nuevos de
   canonicalización sin fallos.

6. **Mergeado a `main`** — rama `day207/canonicalize-parity-single-source`
   (4 commits: PKG_CONFIG_PATH defensivo, canonicalización, resolución Flujo B,
   converter graduado), vía PR, EMECAS+++ verde como evidencia adjunta.

## Rama

Todo el trabajo de DAY 207 ya vive en `main`. `day207/canonicalize-parity-single-source`
puede borrarse (ya mergeada). No hay rama de trabajo abierta pendiente al cierre
de DAY 207 — **recordar la lección de arriba: crear la rama ANTES del primer
commit de DAY 208, no después.**

## Acciones DAY 208 (en orden)

1. **Escribir `parquet_to_kuzu_loader.cpp`** siguiendo el diseño ratificado
   (sección "Estado al cierre" punto 2, y el documento completo en
   `docs/council/PROPUESTA -- Flujo B, parquet_to_kuzu_loader (DAY 207).md`):
   - Lector puro, reusa `KuzuGraphSink`/`IGraphSink` sin ampliarlos.
   - Bucle multi-chunk completo desde el primer commit + `WARNING` (no excepción)
     si `num_chunks() > 1`.
   - Manejo de error explícito si el Parquet gold no existe
     (`"gold Parquet not found: <path>"`, no crash genérico de Arrow).
   - Mapeo cols 0-17 → `CorrelationRecord`; `flow_uid` (col 21) leído directo,
     sin recomputar; cols 18-20 (`hmac_row`, `flow_start_window`,
     `seq_in_window`) explícitamente no usadas como fuente (documentar por qué
     en el propio código, no dejarlo implícito otra vez).
   - Ubicación: `correlation-engine/tools/parquet_to_kuzu_loader.cpp`, junto al
     converter ya graduado. Integrar en `correlation-engine/CMakeLists.txt`
     (mismo patrón que se usó hoy para el converter).
   - Alcance: esquema mono-fuente `correlation_v1` únicamente — el caso
     multi-sensor es `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001`, sesión aparte.
2. **Escribir el test de integración de Flujo B**, mismo patrón que
   `test_bronze_to_kuzu_circuit.cpp`: escribir Parquet con el converter real →
   leer con el loader real → `MATCH` en Kuzu confirma nodos/aristas. Kuzu de
   test aislado y desechable, nunca compartido con nada de producción (Camino 0
   nunca fue candidato a producción — solo valida tecnología para Camino 1,
   que llegará por ZMQ, no por FS).
3. **Con Flujo B funcionando, ejecutar por fin el test de equivalencia completo
   Camino-0 ≡ Flujo-A+B** (predicado §3.1, ADR-058) — el criterio de cierre real
   del medallón, no la versión parcial de DAY 207. Comparar las dos proyecciones
   Kuzu (una por camino) sobre el mismo segmento bronce sintético.
4. **Pendiente sin resolver, traído de sesiones anteriores, evaluar margen:**
   - `DEBT-SECRETS-MANAGER-PERSISTENCE-001` (P1, 2-3 sesiones) — persistencia de
     claves HMAC en Vault. No forma parte estricta de Eslabón 1/2, pero motivada
     directamente por ellos.
   - `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` — si hay margen y ganas de
     abrir el diseño (requiere su propia ronda de Consejo, no improvisar).

## Punteros

- `correlation-engine/tools/bronze_to_gold_converter.cpp` — graduado DAY 207,
  código de producción, compilado vía CMake. `parquet_to_kuzu_loader.cpp` va
  al lado, mismo directorio, cuando se escriba.
- `correlation-engine/include/correlation_engine/canonical_double.hpp` — punto
  único de canonicalización IEEE754, consumido por `correlation_reader.cpp`.
- `correlation-engine/CMakeLists.txt` — nuevo bloque `pkg_check_modules` para
  avro-c/arrow/parquet (con fallback `PKG_CONFIG_PATH`) y target
  `bronze_to_gold_converter`, justo antes del bloque `emecas+++`
  (`test_bronze_to_kuzu_circuit`). Añadir el target del loader en el mismo sitio.
- `docs/council/PROPUESTA -- Flujo B, parquet_to_kuzu_loader (DAY 207).md` —
  diseño completo + las 9 respuestas del Consejo + resolución final de Alonso.
  Fuente de verdad para escribir el código de Flujo B.
- `docs/adr/ADR-058-circuito-completo-aguas-abajo-v3.md` — sección "Corrección
  post-v3 (DAY 207)" al final, documenta la reubicación del punto único de
  canonicalización.
- `docs/BACKLOG.md` — 4 entradas nuevas DAY 207: `DEBT-CIRCUIT-CANONICALIZE-
  PARITY-001` (cerrada), `DEBT-KUZU-CONTINUITY-001` (abierta, diferida),
  `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` (abierta, bloqueante para Flujo B
  completo), y el cierre de "ACCION-3-DAY206... — RESUELTO".
- `docs/design/eslabon-1-flujo-a-avro-parquet/converter-prototype/README.md` —
  conservado como historial, con banner de estado actual al principio.
- `.gitignore` — scripts scratch de sesión (Python heredoc usados para editar
  documentación) se añaden aquí, no se comitean al repo.

*Via Appia Quality — Un escudo que aprende de su propia sombra.*
